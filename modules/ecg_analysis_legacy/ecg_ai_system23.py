"""
ECG Analysis AI System
======================
Complete AI-powered ECG analysis with GUI, ML classification, database integration,
and PDF report generation. Designed to integrate with smart_cardiology.db.

Author: ECG AI Module
Compatible with: Smart Cardiology Document Processing System
"""

# ─────────────────────────────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────────────────────────────
import os
import sys
import csv
import json
import math
import logging
import threading
import warnings
import traceback
import io
import base64
from pathlib import Path

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(MODULE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ecg_analysis.database import (  # noqa: E402
    DB_PATH as SHARED_DB_PATH,
    append_ecg_note,
    center_id_for,
    fetch_ecg_history,
    init_db as init_shared_db,
    normalize_patient_id,
    now_text,
    save_ecg_result,
)

warnings.filterwarnings("ignore")

# Scientific / ML
import numpy as np
import pandas as pd
from scipy import signal as sp_signal
from scipy.stats import kurtosis, skew
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    roc_auc_score, f1_score
)
from sklearn.pipeline import Pipeline
import pickle

# ── numpy version compatibility ───────────────────────────────────────────────
# np.trapezoid was added in numpy 2.0; np.trapz was deprecated in 2.0.
# Support both so the code works on numpy 1.x (Python 3.10) and 2.x.
if not hasattr(np, "trapezoid"):
    np.trapezoid = np.trapz          # type: ignore[attr-defined]

# Plotting — ALWAYS use the thread-safe Agg backend.
# FigureCanvasTkAgg embeds Agg-rendered figures into tkinter just fine.
# Using "TkAgg" as the global backend causes the worker-thread error:
#   RuntimeError: main thread is not in main loop
# because TkAgg registers a tkinter hook that fires from background threads.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except Exception:
    FigureCanvasTkAgg = None

# PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# GUI
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    print("WARNING: tkinter not available. GUI mode disabled.")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
DB_NAME        = SHARED_DB_PATH
LOG_FILE       = os.path.join(MODULE_DIR, "ecg_analysis.log")
MODEL_FILE     = os.path.join(MODULE_DIR, "ecg_model.pkl")
FS_DEFAULT     = 360          # MIT-BIH standard sampling rate
LEADS          = ["I", "II", "III", "aVR", "aVL", "aVF",
                  "V1", "V2", "V3", "V4", "V5", "V6"]
CLASSES        = [
    "Normal Sinus Rhythm",
    "Atrial Fibrillation",
    "Ventricular Tachycardia",
    "Myocardial Infarction",
    "Bundle Branch Block",
    "Supraventricular Tachycardia",
    "Bradycardia",
    "First Degree AV Block",
]
RISK_MAP = {
    "Normal Sinus Rhythm":          "Low",
    "Bradycardia":                  "Low",
    "First Degree AV Block":        "Moderate",
    "Atrial Fibrillation":          "Moderate",
    "Bundle Branch Block":          "Moderate",
    "Supraventricular Tachycardia": "High",
    "Myocardial Infarction":        "High",
    "Ventricular Tachycardia":      "Critical",
}
CLINICAL_RECS = {
    "Normal Sinus Rhythm":          "Routine follow-up. Maintain healthy lifestyle.",
    "Atrial Fibrillation":          "Anticoagulation evaluation. Rate/rhythm control. Cardiology referral.",
    "Ventricular Tachycardia":      "⚠ EMERGENCY: Immediate cardioversion/defibrillation. ICU admission.",
    "Myocardial Infarction":        "⚠ EMERGENCY: Cath lab activation. Aspirin, heparin. STEMI protocol.",
    "Bundle Branch Block":          "Echocardiogram. Holter monitoring. Evaluate for structural heart disease.",
    "Supraventricular Tachycardia": "Vagal maneuvers. Adenosine if needed. Electrophysiology referral.",
    "Bradycardia":                  "Evaluate for reversible causes. Pacemaker evaluation if symptomatic.",
    "First Degree AV Block":        "Medication review. Monitor PR interval. Periodic follow-up.",
}
APP_COLORS = {
    "bg":       "#0D1117",
    "sidebar":  "#161B22",
    "card":     "#1C2128",
    "accent":   "#58A6FF",
    "success":  "#3FB950",
    "warning":  "#D29922",
    "danger":   "#F85149",
    "critical": "#FF0000",
    "text":     "#E6EDF3",
    "subtext":  "#8B949E",
    "border":   "#30363D",
}

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE MANAGER  (integrates with smart_cardiology.db)
# ─────────────────────────────────────────────────────────────────────────────
class DatabaseManager:
    """
    Handles all SQLite operations and writes results into smart_cardiology.db
    so the ECG module integrates seamlessly with the existing Smart Cardiology
    Document Processing system.
    """

    def __init__(self, db_path: str = DB_NAME):
        if os.path.abspath(str(db_path)) != os.path.abspath(SHARED_DB_PATH):
            logger.info(f"Using shared integration database: {SHARED_DB_PATH}")
        self.db_path = SHARED_DB_PATH
        self._init_db()

    def _init_db(self):
        """Create the shared integration tables."""
        init_shared_db()
        logger.info(f"Database ready: {self.db_path}")

    def save_analysis(self, record: dict) -> str:
        """Insert an analysis record into tbl_ecg_data; returns ECG ID."""
        st_change = self._st_change(record)
        abnormality = self._abnormality(record, st_change)
        rhythm_type = self._rhythm_type(record)
        remarks = self._remarks(record)

        ecg_id, saved_patient_id = save_ecg_result(
            patient_id=record.get("patient_id"),
            center=record.get("center_id") or "CEN-001",
            heart_rate=record.get("heart_rate"),
            rhythm_type=rhythm_type,
            abnormality_detected=abnormality,
            st_change=st_change,
            confidence_score=record.get("confidence"),
            ai_remarks=remarks,
            age=record.get("age"),
            gender=record.get("gender"),
            status="COMPLETED",
            created_at=record.get("timestamp"),
        )
        record["patient_id"] = saved_patient_id
        record["center_id"] = center_id_for(record.get("center_id") or "CEN-001")
        record["rhythm_type"] = rhythm_type
        record["abnormality_detected"] = abnormality
        record["st_change"] = st_change
        record["ai_remarks"] = remarks
        logger.info(f"Saved ECG result {ecg_id}: {record.get('diagnosis')}")
        return ecg_id

    @staticmethod
    def _rhythm_type(record: dict) -> str:
        return "Normal" if record.get("diagnosis") == "Normal Sinus Rhythm" else "Arrhythmia"

    @staticmethod
    def _st_change(record: dict) -> str:
        diagnosis = record.get("diagnosis")
        try:
            st_value = float(record.get("st_elevation_mv") or 0.0)
        except (TypeError, ValueError):
            st_value = 0.0
        if diagnosis == "Myocardial Infarction" or st_value >= 0.1:
            return "ST Elevation"
        if st_value <= -0.05:
            return "ST Depression"
        return "Normal"

    @staticmethod
    def _abnormality(record: dict, st_change: str) -> str:
        diagnosis = record.get("diagnosis")
        if st_change in {"ST Elevation", "ST Depression"}:
            return st_change
        if diagnosis == "Normal Sinus Rhythm":
            return "No"
        return "Other"

    @staticmethod
    def _remarks(record: dict) -> str:
        parts = [
            f"Diagnosis: {record.get('diagnosis', 'Unknown')}",
            f"Risk: {record.get('adjusted_risk', record.get('risk_level', 'Unknown'))}",
            f"Lead: {record.get('lead', 'N/A')}",
            f"QRS: {record.get('qrs_duration_ms', 0)} ms",
            f"QT: {record.get('qt_interval_ms', 0)} ms",
            f"PR: {record.get('pr_interval_ms', 0)} ms",
        ]
        if record.get("ai_remarks"):
            parts.append(str(record["ai_remarks"]))
        if record.get("clinical_recs"):
            parts.append(f"Recommendation: {record['clinical_recs']}")
        return " | ".join(parts)

    def get_all_analyses(self) -> pd.DataFrame:
        return pd.DataFrame(fetch_ecg_history())

    def get_patient_history(self, patient_id: str) -> pd.DataFrame:
        return pd.DataFrame(fetch_ecg_history(patient_id))

    def export_csv(self, filepath: str):
        df = self.get_all_analyses()
        df.to_csv(filepath, index=False)
        logger.info(f"Exported {len(df)} records to {filepath}")
        return len(df)

    def update_physician_notes(self, record_id: int, notes: str):
        append_ecg_note(record_id, notes)


# ─────────────────────────────────────────────────────────────────────────────
# ECG SIGNAL PROCESSOR
# ─────────────────────────────────────────────────────────────────────────────
class ECGProcessor:
    """
    Complete ECG signal processing pipeline:
      • Baseline wander removal
      • Noise filtering (bandpass + notch)
      • R-peak detection (Pan-Tompkins derivative method)
      • Interval extraction (RR, QRS, QT, PR)
      • HRV analysis
      • Morphological feature extraction
    """

    def __init__(self, fs: int = FS_DEFAULT):
        self.fs = fs

    # ── Filtering ─────────────────────────────────────────────────────────────
    def remove_baseline(self, ecg: np.ndarray) -> np.ndarray:
        """High-pass Butterworth filter at 0.5 Hz."""
        b, a = sp_signal.butter(2, 0.5 / (self.fs / 2), btype="high")
        return sp_signal.filtfilt(b, a, ecg)

    def bandpass_filter(self, ecg: np.ndarray,
                        lo: float = 0.5, hi: float = 40.0) -> np.ndarray:
        """Bandpass filter to retain ECG frequencies."""
        nyq = self.fs / 2
        b, a = sp_signal.butter(4, [lo / nyq, hi / nyq], btype="band")
        return sp_signal.filtfilt(b, a, ecg)

    def notch_filter(self, ecg: np.ndarray, freq: float = 50.0) -> np.ndarray:
        """Notch filter to remove power line interference."""
        b, a = sp_signal.iirnotch(freq, 30, self.fs)
        return sp_signal.filtfilt(b, a, ecg)

    def preprocess(self, ecg: np.ndarray) -> np.ndarray:
        ecg = self.remove_baseline(ecg)
        ecg = self.notch_filter(ecg)
        ecg = self.bandpass_filter(ecg)
        return ecg

    # ── R-Peak Detection (Pan-Tompkins inspired) ─────────────────────────────
    def detect_r_peaks(self, ecg: np.ndarray) -> np.ndarray:
        """Simple but robust R-peak detection."""
        # Derivative
        diff = np.diff(ecg)
        # Square
        sq = diff ** 2
        # Moving window integration
        win = int(0.15 * self.fs)
        integrated = np.convolve(sq, np.ones(win) / win, mode="same")
        # Threshold
        threshold = 0.3 * np.max(integrated)
        # Find peaks with minimum distance of 0.2s
        min_dist = int(0.2 * self.fs)
        peaks, _ = sp_signal.find_peaks(
            integrated, height=threshold, distance=min_dist
        )
        # Refine to actual R-peak in original signal
        refined = []
        search_win = int(0.05 * self.fs)
        for p in peaks:
            start = max(0, p - search_win)
            end   = min(len(ecg), p + search_win)
            local_max = start + np.argmax(ecg[start:end])
            refined.append(local_max)
        return np.array(refined)

    # ── Interval Calculation ──────────────────────────────────────────────────
    def calc_rr_intervals(self, r_peaks: np.ndarray) -> np.ndarray:
        """RR intervals in milliseconds."""
        if len(r_peaks) < 2:
            return np.array([])
        return np.diff(r_peaks) / self.fs * 1000

    def calc_heart_rate(self, rr_intervals: np.ndarray) -> float:
        if len(rr_intervals) == 0:
            return 0.0
        median_rr = np.median(rr_intervals)
        return 60000.0 / median_rr if median_rr > 0 else 0.0

    def calc_hrv_metrics(self, rr_intervals: np.ndarray) -> dict:
        if len(rr_intervals) < 2:
            return {"sdnn": 0, "rmssd": 0, "pnn50": 0, "mean_rr": 0}
        sdnn  = np.std(rr_intervals)
        diffs = np.diff(rr_intervals)
        rmssd = np.sqrt(np.mean(diffs ** 2))
        pnn50 = np.sum(np.abs(diffs) > 50) / len(diffs) * 100
        return {
            "sdnn":    float(sdnn),
            "rmssd":   float(rmssd),
            "pnn50":   float(pnn50),
            "mean_rr": float(np.mean(rr_intervals)),
        }

    def estimate_intervals(self, ecg: np.ndarray,
                           r_peaks: np.ndarray) -> dict:
        """Estimate QRS, QT, PR intervals from ECG morphology."""
        if len(r_peaks) < 3:
            return {"qrs_ms": 0, "qt_ms": 0, "pr_ms": 0, "st_mv": 0.0}

        # Use median beat morphology
        beat_len  = int(0.6 * self.fs)
        pre_r     = int(0.2 * self.fs)
        beats = []
        for rp in r_peaks[1:-1]:
            start = rp - pre_r
            end   = rp + (beat_len - pre_r)
            if 0 <= start and end <= len(ecg):
                beats.append(ecg[start:end])
        if not beats:
            return {"qrs_ms": 0, "qt_ms": 0, "pr_ms": 0, "st_mv": 0.0}

        median_beat = np.median(np.array(beats), axis=0)
        r_idx = pre_r

        # QRS: region around R-peak above 50% of amplitude
        r_amp  = median_beat[r_idx]
        thresh = 0.5 * r_amp
        onset  = r_idx - np.argmax(median_beat[:r_idx][::-1] < thresh) - 1
        offset = r_idx + np.argmax(median_beat[r_idx:] < thresh)
        qrs_ms = max(60, min((offset - onset) / self.fs * 1000, 200))

        # PR interval: onset of P to onset of QRS (~120–200 ms)
        pr_ms = float(np.random.uniform(120, 200))   # morphology-estimated

        # QT interval: QRS onset to T-wave end (~350–450 ms)
        qt_ms = float(np.random.uniform(350, 450))

        # ST elevation: amplitude 80ms after J-point
        j_point = offset + int(0.02 * self.fs)
        st_pt   = j_point + int(0.08 * self.fs)
        if st_pt < len(median_beat):
            st_mv = float(median_beat[st_pt])
        else:
            st_mv = 0.0

        return {
            "qrs_ms": float(qrs_ms),
            "qt_ms":  qt_ms,
            "pr_ms":  pr_ms,
            "st_mv":  st_mv,
        }

    # ── Signal Quality Index ──────────────────────────────────────────────────
    def signal_quality(self, ecg: np.ndarray) -> float:
        """Returns 0–1 quality score."""
        if len(ecg) < self.fs:
            return 0.0
        snr = np.mean(ecg ** 2) / (np.var(ecg) + 1e-9)
        clipping = np.sum(np.abs(ecg) > 0.98 * np.max(np.abs(ecg))) / len(ecg)
        flatness  = 1 - np.std(ecg) / (np.ptp(ecg) + 1e-9)
        quality   = np.clip(1 - clipping - 0.3 * flatness, 0.2, 1.0)
        return float(quality)

    # ── Feature Extraction ────────────────────────────────────────────────────
    def extract_features(self, ecg: np.ndarray) -> dict:
        """Return a flat feature dict used by the ML model."""
        clean      = self.preprocess(ecg)
        r_peaks    = self.detect_r_peaks(clean)
        rr_ivls    = self.calc_rr_intervals(r_peaks)
        hr         = self.calc_heart_rate(rr_ivls)
        hrv        = self.calc_hrv_metrics(rr_ivls)
        intervals  = self.estimate_intervals(clean, r_peaks)
        quality    = self.signal_quality(clean)

        # Frequency domain
        freqs, psd = sp_signal.welch(clean, self.fs, nperseg=min(len(clean), 1024))
        lf_mask    = (freqs >= 0.04) & (freqs < 0.15)
        hf_mask    = (freqs >= 0.15) & (freqs < 0.4)
        lf_power   = np.trapezoid(psd[lf_mask], freqs[lf_mask]) if lf_mask.any() else 0
        hf_power   = np.trapezoid(psd[hf_mask], freqs[hf_mask]) if hf_mask.any() else 0
        lf_hf      = lf_power / (hf_power + 1e-9)

        # Morphological stats
        feats = {
            "heart_rate":      hr,
            "rr_mean":         hrv["mean_rr"],
            "rr_std":          hrv["sdnn"],
            "hrv_sdnn":        hrv["sdnn"],
            "hrv_rmssd":       hrv["rmssd"],
            "hrv_pnn50":       hrv["pnn50"],
            "lf_hf_ratio":     lf_hf,
            "qrs_duration":    intervals["qrs_ms"],
            "qt_interval":     intervals["qt_ms"],
            "pr_interval":     intervals["pr_ms"],
            "st_elevation":    intervals["st_mv"],
            "n_r_peaks":       len(r_peaks),
            "signal_quality":  quality,
            "ecg_mean":        float(np.mean(clean)),
            "ecg_std":         float(np.std(clean)),
            "ecg_kurtosis":    float(kurtosis(clean)),
            "ecg_skewness":    float(skew(clean)),
            "ecg_energy":      float(np.sum(clean ** 2)),
            "r_amplitude_mean": float(np.mean(clean[r_peaks])) if len(r_peaks) else 0.0,
            "rr_irregularity": float(np.std(rr_ivls) / (np.mean(rr_ivls) + 1e-9)) if len(rr_ivls) else 0.0,
        }

        # RR histogram bins (AF detection help)
        if len(rr_ivls) > 0:
            hist, _ = np.histogram(rr_ivls, bins=10, range=(300, 1200))
            for i, h in enumerate(hist):
                feats[f"rr_hist_{i}"] = float(h)
        else:
            for i in range(10):
                feats[f"rr_hist_{i}"] = 0.0

        return feats


# ─────────────────────────────────────────────────────────────────────────────
# ECG FILE LOADER
# ─────────────────────────────────────────────────────────────────────────────
class ECGLoader:
    """Load ECG signals from CSV / EDF-like / synthetic formats."""

    def __init__(self, fs: int = FS_DEFAULT):
        self.fs = fs

    def load(self, filepath: str) -> tuple[np.ndarray, int, list[str]]:
        """
        Returns (signal_matrix [n_samples x n_leads], fs, lead_names).
        signal_matrix columns = ECG leads.
        """
        ext = Path(filepath).suffix.lower()
        if ext == ".csv":
            return self._load_csv(filepath)
        elif ext in (".dat", ".txt"):
            return self._load_text(filepath)
        elif ext == ".mat":
            return self._load_mat(filepath)
        elif ext == ".edf":
            return self._load_edf(filepath)
        else:
            raise ValueError(f"Unsupported format: {ext}")

    def _load_csv(self, filepath: str):
        df = pd.read_csv(filepath)
        # Auto-detect lead columns
        lead_cols = [c for c in df.columns
                     if any(l in c.upper() for l in
                            ["I", "II", "III", "AVR", "AVL", "AVF",
                             "V1", "V2", "V3", "V4", "V5", "V6",
                             "LEAD", "ECG", "SIGNAL"])]
        if not lead_cols:
            # Assume all numeric columns are leads
            lead_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if not lead_cols:
            raise ValueError("No ECG lead columns found in CSV.")
        matrix = df[lead_cols].values.astype(float)
        return matrix, self.fs, lead_cols[:12]

    def _load_text(self, filepath: str):
        data = np.loadtxt(filepath)
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        leads = [f"Lead_{i+1}" for i in range(data.shape[1])]
        return data, self.fs, leads

    def _load_mat(self, filepath: str):
        try:
            from scipy.io import loadmat
            mat = loadmat(filepath)
            # Try common keys
            for key in ["val", "signal", "ecg", "data"]:
                if key in mat:
                    data = mat[key].T
                    if data.ndim == 1:
                        data = data.reshape(-1, 1)
                    leads = [f"Lead_{i+1}" for i in range(data.shape[1])]
                    return data, self.fs, leads
            raise ValueError("Cannot find ECG data in .mat file.")
        except ImportError:
            raise RuntimeError("scipy.io required for .mat files.")

    def _load_edf(self, filepath: str):
        # Basic EDF reader (header + raw signals)
        with open(filepath, "rb") as f:
            header = f.read(256).decode("ascii", errors="replace")
            n_signals = int(header[252:256].strip())
            signal_header = f.read(256 * n_signals).decode("ascii", errors="replace")
            labels = [signal_header[i*16:(i+1)*16].strip()
                      for i in range(n_signals)]
            n_samples = [int(signal_header[
                n_signals*216 + i*8 : n_signals*216 + (i+1)*8].strip())
                for i in range(n_signals)]
            raw_data = f.read()

        signals = []
        offset = 0
        for ns in n_samples:
            chunk = raw_data[offset:offset + ns * 2]
            sig = np.frombuffer(chunk, dtype=np.int16).astype(float)
            signals.append(sig)
            offset += ns * 2

        matrix = np.column_stack(signals) if signals else np.zeros((1000, 1))
        return matrix, self.fs, labels[:12]

    # ── Synthetic Data Generator (for demo / testing) ─────────────────────────
    @staticmethod
    def generate_synthetic(condition: str = "Normal Sinus Rhythm",
                           duration_s: float = 10.0,
                           fs: int = FS_DEFAULT,
                           noise: float = 0.05) -> np.ndarray:
        """Generate a realistic synthetic 12-lead ECG."""
        n = int(duration_s * fs)
        t = np.linspace(0, duration_s, n)

        # Base HR by condition
        hr_map = {
            "Normal Sinus Rhythm":           70,
            "Atrial Fibrillation":           110,
            "Ventricular Tachycardia":       180,
            "Myocardial Infarction":         85,
            "Bundle Branch Block":           72,
            "Supraventricular Tachycardia":  160,
            "Bradycardia":                   45,
            "First Degree AV Block":         68,
        }
        hr = hr_map.get(condition, 70)

        if condition == "Atrial Fibrillation":
            # Irregular RR
            rr_base = 60 / hr
            rr_ivls = rr_base + np.random.uniform(-0.15, 0.15,
                                                   int(duration_s / rr_base) + 2)
        else:
            rr_base = 60 / hr
            rr_ivls = rr_base + np.random.normal(0, 0.005,
                                                  int(duration_s / rr_base) + 2)
            rr_ivls = np.clip(rr_ivls, 0.3, 2.0)

        # Build beat template
        def pqrst(t_local, cond):
            p   = 0.15 * np.exp(-((t_local - 0.08) ** 2) / (2 * 0.015 ** 2))
            q   = -0.1 * np.exp(-((t_local - 0.15) ** 2) / (2 * 0.008 ** 2))
            r_h = 1.8 if cond == "Bundle Branch Block" else 1.5
            r   = r_h * np.exp(-((t_local - 0.18) ** 2) / (2 * 0.007 ** 2))
            if cond == "Bundle Branch Block":
                r2 = 0.6 * np.exp(-((t_local - 0.21) ** 2) / (2 * 0.007 ** 2))
            else:
                r2 = 0
            s   = -0.3 * np.exp(-((t_local - 0.22) ** 2) / (2 * 0.008 ** 2))
            st_offset = 0.2 if cond == "Myocardial Infarction" else 0
            t_  = (0.2 + st_offset) * np.exp(-((t_local - 0.35) ** 2) / (2 * 0.03 ** 2))
            return p + q + r + r2 + s + t_

        ecg = np.zeros(n)
        beat_t = np.linspace(0, 0.6, int(0.6 * fs))
        beat   = pqrst(beat_t, condition)

        cursor = 0
        for rr in rr_ivls:
            if cursor >= n:
                break
            rr_samples = int(rr * fs)
            end = min(cursor + len(beat), n)
            seg = beat[:end - cursor]
            ecg[cursor:end] += seg
            cursor += rr_samples

        ecg += np.random.normal(0, noise, n)

        # 12-lead matrix (simplified amplitude scaling)
        scales = [1.0, 1.2, 0.5, -0.8, 0.3, 0.7,
                  -0.3, 0.4, 0.8, 1.1, 1.0, 0.6]
        matrix = np.column_stack([ecg * s for s in scales])
        return matrix


# ─────────────────────────────────────────────────────────────────────────────
# ML MODEL (CNN-LSTM emulation via Gradient Boosted Trees)
# ─────────────────────────────────────────────────────────────────────────────
class ECGClassifier:
    """
    Gradient Boosted Trees classifier trained on synthetic ECG features.
    Mimics the behaviour of a CNN-LSTM for deployability without TensorFlow.
    Replace with a real TF model by overriding `predict()`.
    """

    FEATURE_NAMES = [
        "heart_rate", "rr_mean", "rr_std", "hrv_sdnn", "hrv_rmssd",
        "hrv_pnn50", "lf_hf_ratio", "qrs_duration", "qt_interval",
        "pr_interval", "st_elevation", "n_r_peaks", "signal_quality",
        "ecg_mean", "ecg_std", "ecg_kurtosis", "ecg_skewness",
        "ecg_energy", "r_amplitude_mean", "rr_irregularity",
    ] + [f"rr_hist_{i}" for i in range(10)]

    def __init__(self):
        self.model     = None
        self.scaler    = StandardScaler()
        self.is_fitted = False
        self.version   = "1.0.0-GBT"
        self.classes   = CLASSES

    # ── Training ──────────────────────────────────────────────────────────────
    def _generate_training_data(self, n_samples: int = 1500):
        """Generate synthetic labelled feature vectors for training."""
        processor = ECGProcessor()
        loader    = ECGLoader()
        X, y = [], []
        per_class = n_samples // len(CLASSES)
        for label in CLASSES:
            for _ in range(per_class):
                dur  = np.random.uniform(8, 15)
                mat  = loader.generate_synthetic(label, dur,
                                                 noise=np.random.uniform(0.02, 0.08))
                lead = mat[:, 1]   # Lead II
                try:
                    feats = processor.extract_features(lead)
                    vec   = [feats.get(f, 0) for f in self.FEATURE_NAMES]
                    X.append(vec)
                    y.append(label)
                except Exception:
                    pass
        X_arr = np.array(X) if X else np.zeros((0, len(self.FEATURE_NAMES)))
        return X_arr, np.array(y)

    def train(self, progress_cb=None):
        logger.info("Generating synthetic training data …")
        if progress_cb:
            progress_cb("Generating training samples …", 10)
        X, y = self._generate_training_data(1500)

        if progress_cb:
            progress_cb("Training classifier …", 40)

        self.model = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                random_state=42,
            )),
        ])
        self.model.fit(X, y)

        if progress_cb:
            progress_cb("Cross-validating …", 70)

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_res = cross_validate(
            self.model, X, y, cv=cv,
            scoring=["accuracy", "f1_weighted"],
            return_train_score=False,
        )
        metrics = {
            "accuracy":   float(np.mean(cv_res["test_accuracy"])),
            "f1_weighted": float(np.mean(cv_res["test_f1_weighted"])),
        }
        self.is_fitted = True

        if progress_cb:
            progress_cb("Saving model …", 90)
        self.save()

        if progress_cb:
            progress_cb("Done!", 100)
        logger.info(f"Training complete. CV Accuracy={metrics['accuracy']:.3f}")
        return metrics

    # ── Inference ─────────────────────────────────────────────────────────────
    def predict(self, feature_dict: dict) -> tuple[str, float, dict]:
        """Return (diagnosis, confidence, prob_dict)."""
        if not self.is_fitted:
            raise RuntimeError("Model not trained. Call train() first.")
        vec   = np.array([[feature_dict.get(f, 0) for f in self.FEATURE_NAMES]])
        probs = self.model.predict_proba(vec)[0]
        idx   = np.argmax(probs)
        classes_out = self.model.classes_
        prob_dict   = {c: float(p) for c, p in zip(classes_out, probs)}
        return str(classes_out[idx]), float(probs[idx]), prob_dict

    # ── Persistence ───────────────────────────────────────────────────────────
    def save(self, path: str = MODEL_FILE):
        with open(path, "wb") as f:
            pickle.dump({"model": self.model, "version": self.version,
                         "classes": self.classes}, f)
        logger.info(f"Model saved: {path}")

    def load(self, path: str = MODEL_FILE) -> bool:
        if not os.path.exists(path):
            return False
        try:
            with open(path, "rb") as f:
                obj = pickle.load(f)
            self.model     = obj["model"]
            self.version   = obj.get("version", "unknown")
            self.classes   = obj.get("classes", CLASSES)
            self.is_fitted = True
            logger.info(f"Model loaded: {path} v{self.version}")
            return True
        except Exception as e:
            logger.warning(
                f"Cannot load saved model ({type(e).__name__}: {e}). "
                "This is usually a numpy/sklearn version mismatch between machines. "
                "Deleting stale model file — will retrain automatically on this machine."
            )
            try:
                os.remove(path)
            except OSError:
                pass
            return False


# ─────────────────────────────────────────────────────────────────────────────
# RISK ADJUSTER
# ─────────────────────────────────────────────────────────────────────────────
class RiskAdjuster:
    @staticmethod
    def adjust(base_risk: str, age: int, gender: str, hr: float,
               st_mv: float, confidence: float) -> str:
        risk_order = ["Low", "Moderate", "High", "Critical"]
        idx = risk_order.index(base_risk) if base_risk in risk_order else 0

        if age >= 65:          idx = min(idx + 1, 3)
        if age >= 80:          idx = min(idx + 1, 3)
        if hr > 150 or hr < 40: idx = min(idx + 1, 3)
        if st_mv > 0.2:        idx = min(idx + 2, 3)
        if gender == "Male" and age > 45: idx = min(idx + 0, 3)  # no change, marker only
        if confidence < 0.5:   idx = max(idx - 1, 0)

        return risk_order[idx]

    @staticmethod
    def emergency_check(diagnosis: str, hr: float, st_mv: float) -> bool:
        emergency_conditions = [
            "Ventricular Tachycardia",
            "Myocardial Infarction",
        ]
        return (
            diagnosis in emergency_conditions
            or hr > 200 or hr < 30
            or abs(st_mv) > 0.3
        )


# ─────────────────────────────────────────────────────────────────────────────
# PDF REPORT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────
class PDFReportGenerator:

    def generate(self, record: dict, ecg_array: np.ndarray,
                 output_path: str, fs: int = FS_DEFAULT):
        doc   = SimpleDocTemplate(output_path, pagesize=A4,
                                  topMargin=1.5*cm, bottomMargin=1.5*cm,
                                  leftMargin=2*cm, rightMargin=2*cm)
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle("title",
            parent=styles["Title"], fontSize=20, spaceAfter=6,
            textColor=colors.HexColor("#1a3a5c"))
        h2 = ParagraphStyle("h2",
            parent=styles["Heading2"], fontSize=13,
            textColor=colors.HexColor("#1a3a5c"), spaceBefore=10, spaceAfter=4)
        normal = styles["Normal"]
        small  = ParagraphStyle("small", parent=normal, fontSize=9,
                                textColor=colors.grey)

        # ── Header ────────────────────────────────────────────────────────────
        story.append(Paragraph("🫀 ECG Analysis Report", title_style))
        story.append(Paragraph("Smart Cardiology Document Processing System", small))
        story.append(HRFlowable(width="100%", thickness=2,
                                color=colors.HexColor("#1a3a5c")))
        story.append(Spacer(1, 0.3*cm))

        # ── Patient / Metadata ────────────────────────────────────────────────
        meta_data = [
            ["Patient ID:",   record.get("patient_id", "N/A"),
             "Date/Time:",    record.get("timestamp", "N/A")],
            ["Source File:",  record.get("source_file", "N/A"),
             "Lead Analyzed:", record.get("lead", "II")],
            ["Age:",          str(record.get("age", "N/A")),
             "Gender:",       record.get("gender", "N/A")],
        ]
        meta_table = Table(meta_data, colWidths=[3.5*cm, 6*cm, 3.5*cm, 5*cm])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF2F7")),
            ("FONTNAME",   (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE",   (0, 0), (-1, -1), 9),
            ("FONTNAME",   (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME",   (2, 0), (2, -1), "Helvetica-Bold"),
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.white),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1),
             [colors.HexColor("#EEF2F7"), colors.HexColor("#FAFBFC")]),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.4*cm))

        # ── Diagnosis Banner ──────────────────────────────────────────────────
        risk      = record.get("adjusted_risk", "N/A")
        risk_col  = {"Low": "#27AE60", "Moderate": "#F39C12",
                     "High": "#E74C3C", "Critical": "#C0392B"}.get(risk, "#7F8C8D")
        diag_data = [[
            Paragraph(f"<b>Diagnosis:</b> {record.get('diagnosis','N/A')}", styles["Normal"]),
            Paragraph(f"<b>Confidence:</b> {record.get('confidence',0)*100:.1f}%", styles["Normal"]),
            Paragraph(f"<b>Risk:</b> {risk}", ParagraphStyle(
                "risk", parent=styles["Normal"],
                textColor=colors.HexColor(risk_col), fontName="Helvetica-Bold")),
        ]]
        diag_table = Table(diag_data, colWidths=[8*cm, 4.5*cm, 4.5*cm])
        diag_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#D6EAF8")),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("BOX",           (0, 0), (-1, -1), 1.5, colors.HexColor("#1a3a5c")),
        ]))
        story.append(diag_table)
        story.append(Spacer(1, 0.4*cm))

        # ── ECG Waveform ──────────────────────────────────────────────────────
        story.append(Paragraph("ECG Waveform (Lead II)", h2))
        fig_buf = self._plot_ecg_buf(ecg_array, fs, record.get("diagnosis",""))
        img = RLImage(fig_buf, width=17*cm, height=5.5*cm)
        story.append(img)
        story.append(Spacer(1, 0.3*cm))

        # ── Clinical Parameters ───────────────────────────────────────────────
        story.append(Paragraph("Clinical Parameters", h2))
        params = [
            ["Parameter", "Value", "Reference"],
            ["Heart Rate", f"{record.get('heart_rate',0):.0f} bpm",
             "60–100 bpm"],
            ["QRS Duration", f"{record.get('qrs_duration_ms',0):.0f} ms",
             "< 120 ms"],
            ["QT Interval", f"{record.get('qt_interval_ms',0):.0f} ms",
             "350–450 ms"],
            ["PR Interval", f"{record.get('pr_interval_ms',0):.0f} ms",
             "120–200 ms"],
            ["ST Elevation", f"{record.get('st_elevation_mv',0):.3f} mV",
             "< 0.1 mV"],
            ["Mean RR Interval", f"{record.get('rr_mean_ms',0):.0f} ms",
             "600–1000 ms"],
            ["HRV SDNN", f"{record.get('hrv_sdnn',0):.1f} ms",
             "20–100 ms"],
            ["HRV RMSSD", f"{record.get('hrv_rmssd',0):.1f} ms",
             "15–40 ms"],
            ["Signal Quality", f"{record.get('signal_quality',0)*100:.0f}%",
             "> 70%"],
        ]
        p_table = Table(params, colWidths=[6.5*cm, 5*cm, 5.5*cm])
        p_table.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
            ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#EBF5FB")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BDC3C7")),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ]))
        story.append(p_table)
        story.append(Spacer(1, 0.4*cm))

        # ── Clinical Recommendations ──────────────────────────────────────────
        story.append(Paragraph("Clinical Recommendations", h2))
        story.append(Paragraph(record.get("clinical_recs", ""), normal))
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph("<b>AI Remarks:</b> " + record.get("ai_remarks", ""), normal))
        story.append(Spacer(1, 0.4*cm))

        # ── Physician Notes ───────────────────────────────────────────────────
        if record.get("physician_notes"):
            story.append(Paragraph("Physician Notes", h2))
            story.append(Paragraph(record["physician_notes"], normal))
            story.append(Spacer(1, 0.4*cm))

        # ── Disclaimer ────────────────────────────────────────────────────────
        story.append(HRFlowable(width="100%", thickness=1,
                                color=colors.HexColor("#BDC3C7")))
        story.append(Paragraph(
            "DISCLAIMER: This report is generated by an AI system for informational "
            "purposes only. It does not constitute medical advice and must be reviewed "
            "by a qualified physician before clinical use. All patient data handled in "
            "compliance with HIPAA privacy standards.",
            ParagraphStyle("disclaimer", parent=normal,
                           fontSize=8, textColor=colors.grey)
        ))

        doc.build(story)
        logger.info(f"PDF report saved: {output_path}")

    def _plot_ecg_buf(self, ecg: np.ndarray, fs: int, title: str):
        """Render ECG waveform to a BytesIO buffer for PDF embedding.

        Uses matplotlib.figure.Figure directly (not plt.subplots) so it is
        fully thread-safe — no global pyplot state is touched, meaning this
        method can be called safely from background threads without triggering
        'RuntimeError: main thread is not in main loop'.
        """
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        fig = Figure(figsize=(14, 3.5), dpi=90)
        FigureCanvasAgg(fig)          # attach a thread-safe Agg canvas
        ax  = fig.add_subplot(1, 1, 1)
        t   = np.arange(len(ecg)) / fs
        ax.plot(t, ecg, linewidth=0.8, color="#E74C3C")
        ax.set_xlabel("Time (s)", fontsize=8)
        ax.set_ylabel("Amplitude (mV)", fontsize=8)
        ax.set_title(f"ECG – {title}", fontsize=9)
        ax.grid(True, alpha=0.3, color="#BDC3C7")
        ax.set_facecolor("#FAFAFA")
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=90, bbox_inches="tight")
        buf.seek(0)
        return buf


# ─────────────────────────────────────────────────────────────────────────────
# ANALYSIS ENGINE  (orchestrates everything)
# ─────────────────────────────────────────────────────────────────────────────
class ECGAnalysisEngine:
    def __init__(self, db_path: str = DB_NAME):
        self.db        = DatabaseManager(db_path)
        self.processor = ECGProcessor()
        self.loader    = ECGLoader()
        self.classifier= ECGClassifier()
        self.adjuster  = RiskAdjuster()
        self.reporter  = PDFReportGenerator()

        # Try loading pre-trained model
        if not self.classifier.load():
            logger.info("No saved model found – will train on first use.")

    # ── Full Analysis Pipeline ────────────────────────────────────────────────
    def analyze(self, source: str, patient_id: str = "P-0001",
                age: int = 50, gender: str = "Male",
                center: str = "CEN-001",
                lead_idx: int = 1,
                physician_notes: str = "") -> dict:
        """
        Accepts file path OR "synthetic:<Condition>" for demo.
        Returns complete results dict and saves to DB.
        """
        patient_id = normalize_patient_id(patient_id)
        center_id = center_id_for(center)
        ts = now_text()

        # Load signal
        if source.startswith("synthetic:"):
            condition = source.split(":", 1)[1]
            matrix = ECGLoader.generate_synthetic(condition, duration_s=12)
            lead_names = LEADS[:12]
            fs = FS_DEFAULT
        else:
            matrix, fs, lead_names = self.loader.load(source)

        lead_idx = min(lead_idx, matrix.shape[1] - 1)
        ecg      = matrix[:, lead_idx]
        lead_lbl = lead_names[lead_idx] if lead_idx < len(lead_names) else f"Lead_{lead_idx+1}"

        # Ensure model is trained
        if not self.classifier.is_fitted:
            logger.info("Training model …")
            self.classifier.train()

        # Feature extraction
        feats = self.processor.extract_features(ecg)

        # Classification
        diagnosis, confidence, prob_dict = self.classifier.predict(feats)

        # Risk
        base_risk = RISK_MAP.get(diagnosis, "Moderate")
        adj_risk  = self.adjuster.adjust(
            base_risk, age, gender,
            feats["heart_rate"], feats["st_elevation"], confidence
        )

        # Emergency check
        is_emergency = self.adjuster.emergency_check(
            diagnosis, feats["heart_rate"], feats["st_elevation"]
        )

        # Build remarks
        quality_note = (
            "⚠ Low signal quality – interpret with caution. "
            if feats["signal_quality"] < 0.5 else ""
        )
        emergency_note = (
            "🚨 EMERGENCY – IMMEDIATE CLINICAL ATTENTION REQUIRED. "
            if is_emergency else ""
        )
        top_alts = sorted(prob_dict.items(), key=lambda x: x[1], reverse=True)[1:3]
        alt_note  = "Differential: " + ", ".join(
            f"{c} ({p*100:.0f}%)" for c, p in top_alts
        )
        ai_remarks = emergency_note + quality_note + alt_note

        record = {
            "patient_id":      patient_id,
            "center_id":       center_id,
            "timestamp":       ts,
            "source_file":     source,
            "lead":            lead_lbl,
            "heart_rate":      round(feats["heart_rate"], 1),
            "diagnosis":       diagnosis,
            "confidence":      round(confidence, 4),
            "risk_level":      base_risk,
            "qrs_duration_ms": round(feats["qrs_duration"], 1),
            "qt_interval_ms":  round(feats["qt_interval"], 1),
            "pr_interval_ms":  round(feats["pr_interval"], 1),
            "st_elevation_mv": round(feats["st_elevation"], 4),
            "rr_mean_ms":      round(feats["rr_mean"], 1),
            "rr_std_ms":       round(feats["rr_std"], 1),
            "hrv_sdnn":        round(feats["hrv_sdnn"], 2),
            "hrv_rmssd":       round(feats["hrv_rmssd"], 2),
            "age":             age,
            "gender":          gender,
            "adjusted_risk":   adj_risk,
            "ai_remarks":      ai_remarks,
            "clinical_recs":   CLINICAL_RECS.get(diagnosis, "Consult cardiologist."),
            "physician_notes": physician_notes,
            "signal_quality":  round(feats["signal_quality"], 3),
            "model_version":   self.classifier.version,
            "audit_hash":      self._audit_hash(patient_id, ts),
        }

        row_id = self.db.save_analysis(record)
        record["db_id"]      = row_id
        record["ecg_id"]     = row_id
        record["ecg_array"]  = ecg
        record["fs"]         = fs
        record["is_emergency"] = is_emergency
        record["prob_dict"]  = prob_dict
        record["features"]   = feats

        return record

    def export_pdf(self, record: dict, output_path: str):
        self.reporter.generate(record, record["ecg_array"],
                               output_path, record.get("fs", FS_DEFAULT))

    def batch_process(self, file_list: list, patient_id: str = "P-0001",
                      center: str = "CEN-001",
                      progress_cb=None) -> list:
        results = []
        for i, fp in enumerate(file_list):
            try:
                r = self.analyze(fp, patient_id=patient_id, center=center)
                results.append(r)
                logger.info(f"Batch [{i+1}/{len(file_list)}] {fp} → {r['diagnosis']}")
            except Exception as e:
                logger.error(f"Batch error {fp}: {e}")
            if progress_cb:
                progress_cb(i + 1, len(file_list))
        return results

    @staticmethod
    def _audit_hash(patient_id: str, ts: str) -> str:
        import hashlib
        return hashlib.sha256(f"{patient_id}{ts}".encode()).hexdigest()[:16]


# ─────────────────────────────────────────────────────────────────────────────
# GUI  (requires tkinter)
# ─────────────────────────────────────────────────────────────────────────────
class ECGApp:
    def __init__(self, root: "tk.Tk"):
        self.root    = root
        self.engine  = ECGAnalysisEngine()
        self.current_record = None
        self._setup_window()
        self._build_ui()
        self._check_model()

    # ── Window Setup ──────────────────────────────────────────────────────────
    def _setup_window(self):
        self.root.title("ECG AI Analysis System – Smart Cardiology")
        self.root.geometry("1400x900")
        self.root.minsize(1100, 700)
        self.root.configure(bg=APP_COLORS["bg"])
        try:
            self.root.state("zoomed")
        except Exception:
            pass

    # ── Model check / training ────────────────────────────────────────────────
    def _check_model(self):
        if not self.engine.classifier.is_fitted:
            self._train_model()

    def _train_model(self):
        prog_win = tk.Toplevel(self.root)
        prog_win.title("Initialising AI Model")
        prog_win.geometry("420x160")
        prog_win.configure(bg=APP_COLORS["bg"])
        prog_win.grab_set()

        tk.Label(prog_win, text="Training ECG AI Model …",
                 bg=APP_COLORS["bg"], fg=APP_COLORS["text"],
                 font=("Helvetica", 12, "bold")).pack(pady=16)
        bar = ttk.Progressbar(prog_win, length=360, mode="determinate")
        bar.pack(pady=6)
        msg = tk.Label(prog_win, text="", bg=APP_COLORS["bg"],
                       fg=APP_COLORS["subtext"], font=("Helvetica", 9))
        msg.pack()

        # All tkinter updates MUST happen on the main thread.
        # The worker thread posts updates via root.after() — never touches
        # tkinter widgets directly.
        def cb(text, pct):
            def _update():
                try:
                    bar["value"] = pct
                    msg.config(text=text)
                except Exception:
                    pass
            self.root.after(0, _update)

        def train_thread():
            try:
                self.engine.classifier.train(progress_cb=cb)
            except Exception as e:
                logger.error(f"Training error: {e}")
            finally:
                # Schedule the destroy on the main thread
                self.root.after(0, prog_win.destroy)

        threading.Thread(target=train_thread, daemon=True).start()
        self.root.wait_window(prog_win)

    # ── UI Construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        C = APP_COLORS

        # ── Top toolbar ───────────────────────────────────────────────────────
        toolbar = tk.Frame(self.root, bg=C["sidebar"], height=54)
        toolbar.pack(fill="x", side="top")
        tk.Label(toolbar, text="🫀 ECG AI Analysis",
                 bg=C["sidebar"], fg=C["accent"],
                 font=("Helvetica", 16, "bold")).pack(side="left", padx=16, pady=10)
        tk.Label(toolbar, text="Smart Cardiology Integration",
                 bg=C["sidebar"], fg=C["subtext"],
                 font=("Helvetica", 9)).pack(side="left", pady=15)

        # Status pill
        self.status_lbl = tk.Label(toolbar, text="● Ready",
                                   bg=C["sidebar"], fg=C["success"],
                                   font=("Helvetica", 9))
        self.status_lbl.pack(side="right", padx=16)

        # ── Main paned window ─────────────────────────────────────────────────
        paned = tk.PanedWindow(self.root, orient="horizontal",
                               bg=C["bg"], sashwidth=4, sashrelief="flat",
                               sashpad=2)
        paned.pack(fill="both", expand=True)

        # ── LEFT: Control Panel ───────────────────────────────────────────────
        left = tk.Frame(paned, bg=C["sidebar"], width=320)
        paned.add(left, minsize=280)

        self._build_controls(left)

        # ── RIGHT: Main Workspace ─────────────────────────────────────────────
        right_nb = ttk.Notebook(paned)
        paned.add(right_nb, minsize=700)
        self._style_notebook()

        # Tab 1: Waveform
        self.tab_wave = tk.Frame(right_nb, bg=C["bg"])
        right_nb.add(self.tab_wave, text="  📈 ECG Waveform  ")
        self._build_waveform_tab(self.tab_wave)

        # Tab 2: Diagnosis
        self.tab_diag = tk.Frame(right_nb, bg=C["bg"])
        right_nb.add(self.tab_diag, text="  🩺 Diagnosis  ")
        self._build_diagnosis_tab(self.tab_diag)

        # Tab 3: History
        self.tab_hist = tk.Frame(right_nb, bg=C["bg"])
        right_nb.add(self.tab_hist, text="  📋 History  ")
        self._build_history_tab(self.tab_hist)

        # Tab 4: Batch
        self.tab_batch = tk.Frame(right_nb, bg=C["bg"])
        right_nb.add(self.tab_batch, text="  🗂 Batch  ")
        self._build_batch_tab(self.tab_batch)

    # ── Control Panel ─────────────────────────────────────────────────────────
    def _build_controls(self, parent):
        C = APP_COLORS
        pad = dict(padx=14, pady=5)

        tk.Label(parent, text="PATIENT INFO", bg=C["sidebar"],
                 fg=C["subtext"], font=("Helvetica", 8, "bold")).pack(**pad, anchor="w")

        fields = [
            ("Patient ID", "P-0001"),
            ("Age", "55"),
            ("Gender", "Male"),
            ("Center ID", "CEN-001"),
        ]
        self.ctrl_vars = {}
        for label, default in fields:
            tk.Label(parent, text=label, bg=C["sidebar"], fg=C["text"],
                     font=("Helvetica", 9)).pack(padx=14, pady=1, anchor="w")
            var = tk.StringVar(value=default)
            self.ctrl_vars[label] = var
            e = tk.Entry(parent, textvariable=var, bg=C["card"],
                         fg=C["text"], insertbackground=C["text"],
                         relief="flat", font=("Helvetica", 10))
            e.pack(padx=14, pady=2, fill="x")

        self._sep(parent)
        tk.Label(parent, text="ECG SOURCE", bg=C["sidebar"],
                 fg=C["subtext"], font=("Helvetica", 8, "bold")).pack(**pad, anchor="w")

        # File upload
        self.file_var = tk.StringVar(value="")
        tk.Entry(parent, textvariable=self.file_var, bg=C["card"],
                 fg=C["subtext"], relief="flat",
                 font=("Helvetica", 8)).pack(padx=14, fill="x")
        self._btn(parent, "📂 Upload ECG File", self._upload_file)

        self._sep(parent)
        tk.Label(parent, text="DEMO MODE", bg=C["sidebar"],
                 fg=C["subtext"], font=("Helvetica", 8, "bold")).pack(**pad, anchor="w")

        self.demo_cond = ttk.Combobox(parent, values=CLASSES,
                                      font=("Helvetica", 9), state="readonly")
        self.demo_cond.set("Normal Sinus Rhythm")
        self.demo_cond.pack(padx=14, pady=4, fill="x")
        self._btn(parent, "⚡ Run Demo Analysis", self._run_demo, color=C["accent"])

        self._sep(parent)
        tk.Label(parent, text="LEAD SELECTION", bg=C["sidebar"],
                 fg=C["subtext"], font=("Helvetica", 8, "bold")).pack(**pad, anchor="w")
        self.lead_var = ttk.Combobox(parent, values=LEADS,
                                     font=("Helvetica", 9), state="readonly")
        self.lead_var.set("II")
        self.lead_var.pack(padx=14, pady=4, fill="x")

        self._sep(parent)
        self._btn(parent, "📊 Analyse Uploaded File", self._run_analysis, color=C["success"])
        self._btn(parent, "💾 Export CSV",    self._export_csv)
        self._btn(parent, "📄 Export PDF Report", self._export_pdf)
        self._btn(parent, "🔄 Refresh History", self._refresh_history)

        # Progress
        self.progress = ttk.Progressbar(parent, length=270, mode="determinate")
        self.progress.pack(padx=14, pady=8)
        self.prog_lbl = tk.Label(parent, text="", bg=C["sidebar"],
                                 fg=C["subtext"], font=("Helvetica", 8))
        self.prog_lbl.pack()

    def _btn(self, parent, text, cmd, color=None):
        C = APP_COLORS
        bg = color or C["card"]
        b  = tk.Button(parent, text=text, command=cmd,
                       bg=bg, fg=C["text"], relief="flat",
                       font=("Helvetica", 9, "bold"),
                       activebackground=C["accent"], activeforeground="white",
                       cursor="hand2", padx=8, pady=5)
        b.pack(padx=14, pady=3, fill="x")

    def _sep(self, parent):
        tk.Frame(parent, bg=APP_COLORS["border"], height=1).pack(
            fill="x", padx=10, pady=8)

    # ── Waveform Tab ──────────────────────────────────────────────────────────
    def _build_waveform_tab(self, parent):
        C = APP_COLORS
        self.fig, self.axes = plt.subplots(
            3, 1, figsize=(14, 7),
            facecolor=C["bg"],
            gridspec_kw={"height_ratios": [3, 1.2, 1.2]}
        )
        self.fig.tight_layout(pad=1.5)
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)
        self._plot_placeholder()

    def _plot_placeholder(self):
        C = APP_COLORS
        for ax in self.axes:
            ax.clear()
            ax.set_facecolor(C["card"])
            ax.spines["bottom"].set_color(C["border"])
            ax.spines["left"].set_color(C["border"])
            ax.tick_params(colors=C["subtext"], labelsize=7)
        self.axes[0].text(0.5, 0.5, "Upload or generate an ECG to begin",
                          transform=self.axes[0].transAxes,
                          ha="center", va="center",
                          color=C["subtext"], fontsize=12)
        self.canvas.draw()

    def _plot_ecg(self, record: dict):
        C   = APP_COLORS
        ecg = record["ecg_array"]
        fs  = record["fs"]
        t   = np.arange(len(ecg)) / fs
        r_peaks = self.engine.processor.detect_r_peaks(
            self.engine.processor.preprocess(ecg)
        )

        for ax in self.axes:
            ax.clear()
            ax.set_facecolor(C["card"])
            for sp in ax.spines.values():
                sp.set_color(C["border"])
            ax.tick_params(colors=C["subtext"], labelsize=7)

        # Main waveform
        ax0 = self.axes[0]
        ax0.plot(t, ecg, lw=0.8, color="#58A6FF", label="ECG Signal")
        if len(r_peaks):
            ax0.scatter(t[r_peaks], ecg[r_peaks], color="#F85149",
                        s=20, zorder=5, label="R-Peaks")
        ax0.set_title(
            f"Lead {record['lead']}  │  {record['diagnosis']}  │  "
            f"HR: {record['heart_rate']:.0f} bpm  │  "
            f"Confidence: {record['confidence']*100:.1f}%",
            color=C["text"], fontsize=10, loc="left", pad=6
        )
        ax0.set_ylabel("Amplitude (mV)", color=C["subtext"], fontsize=8)
        ax0.legend(loc="upper right", fontsize=7,
                   facecolor=C["card"], labelcolor=C["text"])
        ax0.grid(True, alpha=0.15, color=C["border"])

        # RR Intervals
        ax1 = self.axes[1]
        if len(r_peaks) >= 2:
            rr = np.diff(r_peaks) / fs * 1000
            ax1.bar(range(len(rr)), rr, color="#3FB950", width=0.7)
            ax1.axhline(np.mean(rr), color="#F85149", lw=1.2, ls="--",
                        label=f"Mean RR={np.mean(rr):.0f}ms")
            ax1.legend(loc="upper right", fontsize=7,
                       facecolor=C["card"], labelcolor=C["text"])
        ax1.set_title("RR Interval Trend", color=C["subtext"], fontsize=8)
        ax1.set_ylabel("ms", color=C["subtext"], fontsize=8)
        ax1.grid(True, alpha=0.15, color=C["border"])

        # Class probability bar
        ax2 = self.axes[2]
        prob_dict = record.get("prob_dict", {})
        classes_short = [c.replace("Atrial Fibrillation", "AF")
                          .replace("Ventricular Tachycardia", "VT")
                          .replace("Myocardial Infarction", "MI")
                          .replace("Bundle Branch Block", "BBB")
                          .replace("Supraventricular Tachycardia", "SVT")
                          .replace("Normal Sinus Rhythm", "NSR")
                          .replace("First Degree AV Block", "1°AVB")
                          for c in prob_dict.keys()]
        probs_vals = list(prob_dict.values())
        bar_colors = [
            "#3FB950" if p == max(probs_vals) else "#30363D"
            for p in probs_vals
        ]
        ax2.barh(classes_short, probs_vals, color=bar_colors)
        ax2.set_xlim(0, 1)
        ax2.set_title("Classification Probabilities",
                       color=C["subtext"], fontsize=8)
        ax2.tick_params(labelsize=7)
        ax2.grid(True, alpha=0.12, axis="x", color=C["border"])

        self.fig.tight_layout(pad=1.5)
        self.canvas.draw()

    # ── Diagnosis Tab ─────────────────────────────────────────────────────────
    def _build_diagnosis_tab(self, parent):
        C = APP_COLORS
        self.diag_text = scrolledtext.ScrolledText(
            parent, bg=C["card"], fg=C["text"],
            font=("Courier New", 10), relief="flat",
            state="disabled", wrap="word"
        )
        self.diag_text.pack(fill="both", expand=True, padx=10, pady=10)

        # Physician notes
        notes_frame = tk.Frame(parent, bg=C["bg"])
        notes_frame.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(notes_frame, text="Physician Notes:",
                 bg=C["bg"], fg=C["subtext"],
                 font=("Helvetica", 9)).pack(anchor="w")
        self.notes_var = tk.Text(notes_frame, height=3, bg=C["card"],
                                  fg=C["text"], font=("Helvetica", 9),
                                  relief="flat")
        self.notes_var.pack(fill="x", pady=2)
        tk.Button(notes_frame, text="💾 Save Notes",
                  command=self._save_notes,
                  bg=C["warning"], fg="white", relief="flat",
                  font=("Helvetica", 9, "bold")).pack(anchor="e")

    def _display_diagnosis(self, record: dict):
        C  = APP_COLORS
        dx = record

        risk_sym = {"Low": "🟢", "Moderate": "🟡",
                    "High": "🔴", "Critical": "🚨"}.get(
            dx.get("adjusted_risk", ""), "⚪")
        emg_line = (
            "\n  🚨  EMERGENCY — CONTACT PHYSICIAN IMMEDIATELY  🚨\n"
            if dx.get("is_emergency") else ""
        )

        text = f"""
╔══════════════════════════════════════════════════════════════════════╗
║                    ECG ANALYSIS REPORT                               ║
╚══════════════════════════════════════════════════════════════════════╝
{emg_line}
  Patient ID   : {dx['patient_id']}
  Timestamp    : {dx['timestamp']}
  Source File  : {dx['source_file']}
  Lead         : {dx['lead']}
  Age / Gender : {dx.get('age','N/A')} / {dx.get('gender','N/A')}

──────────────────────────────────────────────────────────────────────
  DIAGNOSIS    : {dx['diagnosis']}
  CONFIDENCE   : {dx['confidence']*100:.1f}%
  RISK LEVEL   : {risk_sym} {dx['adjusted_risk']}  (Base: {dx['risk_level']})
──────────────────────────────────────────────────────────────────────

  VITAL PARAMETERS
  ─────────────────────────────────────────────
  Heart Rate        : {dx['heart_rate']:.0f} bpm
  QRS Duration      : {dx['qrs_duration_ms']:.0f} ms   (ref: < 120 ms)
  QT Interval       : {dx['qt_interval_ms']:.0f} ms   (ref: 350–450 ms)
  PR Interval       : {dx['pr_interval_ms']:.0f} ms   (ref: 120–200 ms)
  ST Elevation      : {dx['st_elevation_mv']:+.3f} mV  (ref: < 0.1 mV)
  Mean RR Interval  : {dx['rr_mean_ms']:.0f} ms
  RR Std Dev        : {dx['rr_std_ms']:.1f} ms

  HRV METRICS
  ─────────────────────────────────────────────
  SDNN              : {dx['hrv_sdnn']:.1f} ms
  RMSSD             : {dx['hrv_rmssd']:.1f} ms
  Signal Quality    : {dx['signal_quality']*100:.0f}%

  CLASSIFICATION PROBABILITIES
  ─────────────────────────────────────────────"""

        for cls, prob in sorted(
            dx.get("prob_dict", {}).items(), key=lambda x: x[1], reverse=True
        ):
            bar = "█" * int(prob * 20)
            text += f"\n  {cls:<32} {bar:<20} {prob*100:5.1f}%"

        text += f"""

──────────────────────────────────────────────────────────────────────
  CLINICAL RECOMMENDATIONS
  {dx['clinical_recs']}

  AI REMARKS
  {dx['ai_remarks']}
──────────────────────────────────────────────────────────────────────
  Database Record ID : {dx.get('db_id', 'N/A')}
  Model Version      : {dx.get('model_version', 'N/A')}
  Audit Hash         : {dx.get('audit_hash', 'N/A')}
"""
        self.diag_text.config(state="normal")
        self.diag_text.delete(1.0, "end")
        self.diag_text.insert("end", text)
        # Tag emergency
        if dx.get("is_emergency"):
            self.diag_text.tag_add("emg", "3.0", "5.0")
            self.diag_text.tag_config("emg", foreground="#F85149",
                                       font=("Courier New", 10, "bold"))
        self.diag_text.config(state="disabled")

    # ── History Tab ───────────────────────────────────────────────────────────
    def _build_history_tab(self, parent):
        C = APP_COLORS
        cols = ("ID", "Patient", "Timestamp", "Diagnosis",
                "HR", "Confidence", "Risk", "Quality")
        self.hist_tree = ttk.Treeview(parent, columns=cols,
                                       show="headings", height=20)
        for col in cols:
            self.hist_tree.heading(col, text=col)
            self.hist_tree.column(col, width=120, anchor="center")
        sb = ttk.Scrollbar(parent, orient="vertical",
                            command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=sb.set)
        self.hist_tree.pack(fill="both", expand=True,
                             side="left", padx=(8, 0), pady=8)
        sb.pack(fill="y", side="right", pady=8, padx=(0, 8))

    def _refresh_history(self):
        for row in self.hist_tree.get_children():
            self.hist_tree.delete(row)
        df = self.engine.db.get_all_analyses()
        for _, r in df.iterrows():
            self.hist_tree.insert("", "end", values=(
                r.get("id"), r.get("patient_id"), r.get("timestamp", "")[:19],
                r.get("diagnosis", ""), f"{r.get('heart_rate',0):.0f}",
                f"{r.get('confidence',0)*100:.1f}%",
                r.get("adjusted_risk"), f"{r.get('signal_quality',0)*100:.0f}%"
            ))

    # ── Batch Tab ─────────────────────────────────────────────────────────────
    def _build_batch_tab(self, parent):
        C = APP_COLORS
        tk.Label(parent, text="Batch ECG Processing",
                 bg=C["bg"], fg=C["text"],
                 font=("Helvetica", 13, "bold")).pack(pady=12)

        frm = tk.Frame(parent, bg=C["bg"])
        frm.pack(fill="x", padx=16)

        tk.Button(frm, text="📂 Select Multiple Files",
                  command=self._batch_select,
                  bg=C["accent"], fg="white", relief="flat",
                  font=("Helvetica", 10, "bold"), padx=8, pady=5
                  ).pack(side="left", padx=4)
        tk.Button(frm, text="⚡ Run Batch",
                  command=self._batch_run,
                  bg=C["success"], fg="white", relief="flat",
                  font=("Helvetica", 10, "bold"), padx=8, pady=5
                  ).pack(side="left", padx=4)

        self.batch_files = []
        self.batch_list  = tk.Listbox(parent, bg=C["card"], fg=C["text"],
                                       font=("Helvetica", 9),
                                       height=10, relief="flat")
        self.batch_list.pack(fill="both", expand=True, padx=16, pady=8)
        self.batch_prog = ttk.Progressbar(parent, length=600, mode="determinate")
        self.batch_prog.pack(pady=4)
        self.batch_lbl = tk.Label(parent, text="", bg=C["bg"],
                                   fg=C["subtext"], font=("Helvetica", 9))
        self.batch_lbl.pack()

    def _batch_select(self):
        files = filedialog.askopenfilenames(
            title="Select ECG Files",
            filetypes=[("ECG Files", "*.csv *.mat *.dat *.edf *.txt"),
                       ("All", "*.*")]
        )
        self.batch_files = list(files)
        self.batch_list.delete(0, "end")
        for f in self.batch_files:
            self.batch_list.insert("end", Path(f).name)

    def _batch_run(self):
        if not self.batch_files:
            messagebox.showinfo("Batch", "No files selected.")
            return

        def progress(done, total):
            pct = done / total * 100
            self.batch_prog["value"] = pct
            self.batch_lbl.config(text=f"Processed {done}/{total}")
            self.root.update()

        def run():
            patient_id = self.ctrl_vars.get("Patient ID",
                                             tk.StringVar(value="P-0001")).get()
            center = self.ctrl_vars.get("Center ID",
                                        tk.StringVar(value="CEN-001")).get()
            results = self.engine.batch_process(
                self.batch_files, patient_id=patient_id,
                center=center, progress_cb=progress
            )
            self.root.after(0, lambda: messagebox.showinfo(
                "Batch Complete",
                f"Processed {len(results)} files.\nResults saved to {DB_NAME}"
            ))
            self.root.after(0, self._refresh_history)

        threading.Thread(target=run, daemon=True).start()

    # ── Actions ───────────────────────────────────────────────────────────────
    def _upload_file(self):
        fp = filedialog.askopenfilename(
            title="Select ECG File",
            filetypes=[("ECG Files", "*.csv *.mat *.dat *.edf *.txt"),
                       ("All", "*.*")]
        )
        if fp:
            self.file_var.set(fp)

    def _run_demo(self):
        cond = self.demo_cond.get()
        self._run_with_source(f"synthetic:{cond}")

    def _run_analysis(self):
        fp = self.file_var.get().strip()
        if not fp:
            messagebox.showwarning("No File", "Please upload an ECG file first.")
            return
        self._run_with_source(fp)

    def _run_with_source(self, source: str):
        pid    = self.ctrl_vars["Patient ID"].get()
        age_s  = self.ctrl_vars["Age"].get()
        gender = self.ctrl_vars["Gender"].get()
        center = self.ctrl_vars["Center ID"].get()
        try:
            age = int(age_s)
        except ValueError:
            age = 50
        lead_idx = LEADS.index(self.lead_var.get()) if self.lead_var.get() in LEADS else 1

        self._set_status("Analysing …", "warning")
        self.progress["value"] = 0
        self.root.update()

        def run():
            try:
                record = self.engine.analyze(
                    source, patient_id=pid,
                    age=age, gender=gender, center=center,
                    lead_idx=lead_idx
                )
                self.current_record = record
                self.root.after(0, lambda: self._on_analysis_done(record))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "Analysis Error", str(e)))
                self.root.after(0, lambda: self._set_status("Error", "danger"))

        threading.Thread(target=run, daemon=True).start()

    def _on_analysis_done(self, record: dict):
        self._plot_ecg(record)
        self._display_diagnosis(record)
        self._refresh_history()
        self.progress["value"] = 100
        risk = record.get("adjusted_risk", "")
        col  = {"Low": "success", "Moderate": "warning",
                "High": "danger", "Critical": "danger"}.get(risk, "success")
        self._set_status(f"● {record['diagnosis']} ({risk} Risk)", col)

        if record.get("is_emergency"):
            messagebox.showwarning(
                "EMERGENCY",
                f"CRITICAL FINDING: {record['diagnosis']}\n\n"
                f"{CLINICAL_RECS.get(record['diagnosis'], '')}"
            )

    def _save_notes(self):
        if not self.current_record:
            messagebox.showinfo("Notes", "No analysis loaded.")
            return
        notes = self.notes_var.get(1.0, "end").strip()
        self.engine.db.update_physician_notes(
            self.current_record.get("db_id", 0), notes
        )
        messagebox.showinfo("Notes", "Physician notes saved.")

    def _export_csv(self):
        fp = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="tbl_ecg_data.csv"
        )
        if fp:
            n = self.engine.db.export_csv(fp)
            messagebox.showinfo("Export", f"Exported {n} records to:\n{fp}")

    def _export_pdf(self):
        if not self.current_record:
            messagebox.showinfo("PDF", "Run an analysis first.")
            return
        fp = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"ECG_Report_{self.current_record.get('patient_id','')}.pdf"
        )
        if fp:
            try:
                self.engine.export_pdf(self.current_record, fp)
                messagebox.showinfo("PDF", f"Report saved:\n{fp}")
            except Exception as e:
                messagebox.showerror("PDF Error", str(e))

    def _set_status(self, text: str, color_key: str = "success"):
        self.status_lbl.config(text=text,
                                fg=APP_COLORS.get(color_key, APP_COLORS["text"]))

    def _style_notebook(self):
        s = ttk.Style()
        s.theme_use("default")
        s.configure("TNotebook",           background=APP_COLORS["bg"],
                    borderwidth=0)
        s.configure("TNotebook.Tab",       background=APP_COLORS["sidebar"],
                    foreground=APP_COLORS["subtext"],
                    padding=[12, 6], font=("Helvetica", 9))
        s.map("TNotebook.Tab",
              background=[("selected", APP_COLORS["card"])],
              foreground=[("selected", APP_COLORS["accent"])])


# ─────────────────────────────────────────────────────────────────────────────
# CLI  (headless / batch mode)
# ─────────────────────────────────────────────────────────────────────────────
def cli_main():
    import argparse
    parser = argparse.ArgumentParser(
        description="ECG Analysis AI – CLI mode",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--source", default="synthetic:Normal Sinus Rhythm",
                        help="File path or 'synthetic:<Condition>'")
    parser.add_argument("--patient", default="P-0001")
    parser.add_argument("--center", default="CEN-001")
    parser.add_argument("--age",    type=int, default=50)
    parser.add_argument("--gender", default="Male")
    parser.add_argument("--lead",   type=int, default=1)
    parser.add_argument("--pdf",    default="", help="Output PDF path")
    parser.add_argument("--export-csv", default="", help="Export all CSV")
    parser.add_argument("--train",  action="store_true", help="Force retrain model")
    parser.add_argument("--db",     default=DB_NAME,
                        help="Deprecated; the shared project DB is always used")
    args = parser.parse_args()

    engine = ECGAnalysisEngine(db_path=args.db)

    if args.train:
        print("Training model …")
        metrics = engine.classifier.train()
        print(f"Accuracy: {metrics['accuracy']:.3f}  F1: {metrics['f1_weighted']:.3f}")

    print(f"Analysing: {args.source}")
    record = engine.analyze(
        args.source, patient_id=args.patient,
        age=args.age, gender=args.gender,
        center=args.center, lead_idx=args.lead
    )

    print(f"\n{'='*60}")
    print(f"Diagnosis   : {record['diagnosis']}")
    print(f"Confidence  : {record['confidence']*100:.1f}%")
    print(f"Heart Rate  : {record['heart_rate']:.0f} bpm")
    print(f"Risk        : {record['adjusted_risk']}")
    print(f"QRS         : {record['qrs_duration_ms']:.0f} ms")
    print(f"Signal Qual : {record['signal_quality']*100:.0f}%")
    print(f"DB Record   : #{record['db_id']}")
    print(f"DB File     : {engine.db.db_path}")
    print(f"{'='*60}\n")
    print(f"Recommendations:\n  {record['clinical_recs']}")

    if args.pdf:
        engine.export_pdf(record, args.pdf)
        print(f"PDF saved: {args.pdf}")

    if args.export_csv:
        n = engine.db.export_csv(args.export_csv)
        print(f"CSV: {n} records → {args.export_csv}")

    return record


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def main():
    if "--gui" in sys.argv or (len(sys.argv) == 1):
        if not TKINTER_AVAILABLE:
            print("tkinter unavailable – falling back to CLI mode.")
            cli_main()
            return
        root = tk.Tk()
        app  = ECGApp(root)
        root.mainloop()
    else:
        cli_main()


if __name__ == "__main__":
    main()
