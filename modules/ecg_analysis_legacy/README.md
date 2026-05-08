# ECG AI Analysis System
## Smart Cardiology Integration Module

---

## Overview

A complete, production-ready ECG analysis pipeline that integrates directly with the
**Smart Cardiology Document Processing** system by writing all results into `smart_cardiology.db`.

### Features
- Real ECG signal preprocessing (baseline correction, bandpass/notch filtering)
- Pan-Tompkins inspired R-peak detection
- Full HRV analysis (SDNN, RMSSD, pNN50, LF/HF ratio)
- Clinical interval measurement (QRS, QT, PR, ST elevation)
- Multi-class arrhythmia classification (8 conditions)
- Age/gender-specific risk adjustment
- Emergency alert system (VT, STEMI, extreme HR)
- PDF clinical report generation
- CSV data export
- SQLite integration with `smart_cardiology.db`
- Tkinter GUI with real-time waveform display
- Batch processing support
- Audit logging for HIPAA compliance

---

## Installation

```bash
pip install numpy scipy scikit-learn matplotlib pandas reportlab Pillow
# For real TF/Keras CNN-LSTM (optional upgrade):
pip install tensorflow
```

---

## Integration with Smart Cardiology

The module writes directly to the shared project `smart_cardiology.db` through
`shared/database.py`.
Run from the same directory as your existing project:

```bash
cd /path/to/Smart-Cardiology-Document-Processing
python ecg_ai_system23.py --source "synthetic:Atrial Fibrillation" --patient P-0001 --center CEN-001
```

Table written in `smart_cardiology.db`:
- `tbl_ecg_data` - Module 2 ECG analysis results

---

## Usage

### GUI Mode (requires tkinter)
```bash
python ecg_ai_system23.py
python ecg_ai_system23.py --gui
```

### CLI Mode
```bash
# Analyse a CSV file
python ecg_ai_system23.py --source path/to/ecg.csv --patient P-0042 --center CEN-001 --age 65 --gender Female

# Demo with synthetic ECG
python ecg_ai_system23.py --source "synthetic:Atrial Fibrillation" --patient P-0001 --center CEN-001 --age 72 --gender Male

# Generate PDF report
python ecg_ai_system23.py --source ecg.csv --patient P-0001 --center CEN-001 --pdf report.pdf

# Export all DB records to CSV
python ecg_ai_system23.py --source "synthetic:Normal Sinus Rhythm" --export-csv all_analyses.csv

# Force model retraining
python ecg_ai_system23.py --train --source "synthetic:Normal Sinus Rhythm"

# Custom DB path
python ecg_ai_system23.py --source ecg.csv
```

### Python API
```python
from ecg_ai_system23 import ECGAnalysisEngine

engine = ECGAnalysisEngine()

# Analyse a file
record = engine.analyze(
    source="path/to/ecg.csv",
    patient_id="P-0001",
    center="CEN-001",
    age=65,
    gender="Female",
    lead_idx=1,  # Lead II (0-indexed)
)

print(record["diagnosis"])      # e.g. "Atrial Fibrillation"
print(record["confidence"])     # 0.0 – 1.0
print(record["heart_rate"])     # beats per minute
print(record["adjusted_risk"])  # Low / Moderate / High / Critical
print(record["ecg_id"])         # ECG ID in tbl_ecg_data, e.g. ECG-0001

# Export PDF
engine.export_pdf(record, "report.pdf")

# Export all records to CSV
engine.db.export_csv("all_records.csv")
```

---

## Supported ECG Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| CSV | .csv | Auto-detect lead columns |
| MATLAB | .mat | Keys: val, signal, ecg, data |
| EDF | .edf | Basic EDF reader included |
| Text | .dat, .txt | Space/tab delimited |

For MIT-BIH `.dat`+`.hea` files, install `wfdb`:
```bash
pip install wfdb
```
Then convert: `python -c "import wfdb; rec = wfdb.rdrecord('100'); rec.to_csv('100.csv')"`

---

## Database Schema

### `tbl_ecg_data`
| Column | Type | Description |
|--------|------|-------------|
| ecg_id | TEXT PK | `ECG-0001` style ECG result ID |
| patient_id | TEXT | `P-0001` style patient identifier |
| center_id | TEXT | `CEN-001` through `CEN-006` |
| heart_rate | INTEGER | bpm |
| rhythm_type | TEXT | `Normal` or `Arrhythmia` |
| abnormality_detected | TEXT | `No`, `ST Depression`, `ST Elevation`, `LV Hypertrophy`, or `Other` |
| st_change | TEXT | `Normal`, `ST Elevation`, or `ST Depression` |
| confidence_score | REAL | 0 to 1 model confidence |
| ai_remarks | TEXT | AI-generated notes |
| status | TEXT | `COMPLETED` for finished analyses |
| created_at | TEXT | `YYYY-MM-DD HH:MM:SS` |

---

## Classified Conditions

| Condition | Base Risk | Emergency |
|-----------|-----------|-----------|
| Normal Sinus Rhythm | Low | No |
| Bradycardia | Low | No |
| First Degree AV Block | Moderate | No |
| Atrial Fibrillation | Moderate | No |
| Bundle Branch Block | Moderate | No |
| Supraventricular Tachycardia | High | No |
| Myocardial Infarction | High | YES |
| Ventricular Tachycardia | Critical | YES |

---

## Upgrading to TensorFlow CNN-LSTM

Replace `ECGClassifier.train()` and `ECGClassifier.predict()` with:

```python
import tensorflow as tf

def build_cnn_lstm(n_features, n_classes):
    inp = tf.keras.Input(shape=(n_features, 1))
    x = tf.keras.layers.Conv1D(64, 3, activation="relu")(inp)
    x = tf.keras.layers.MaxPooling1D(2)(x)
    x = tf.keras.layers.Conv1D(128, 3, activation="relu")(x)
    x = tf.keras.layers.LSTM(64, return_sequences=False)(x)
    x = tf.keras.layers.Dense(64, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    out = tf.keras.layers.Dense(n_classes, activation="softmax")(x)
    return tf.keras.Model(inp, out)
```

---

## HIPAA Compliance Notes

- No PHI is transmitted externally; all processing is local
- Results stay local in `smart_cardiology.db`
- Physician notes can be appended to `ai_remarks`
- Export functions produce de-identifiable CSV

---

## MIT-BIH Dataset Integration

```python
# Download MIT-BIH from PhysioNet (free, public domain)
# https://physionet.org/content/mitdb/1.0.0/

import wfdb
record = wfdb.rdrecord("mitdb/100")
# Save as CSV for this system
import pandas as pd
df = pd.DataFrame(record.p_signal, columns=record.sig_name)
df.to_csv("mitdb_100.csv", index=False)

# Then analyse:
from ecg_ai_system23 import ECGAnalysisEngine
engine = ECGAnalysisEngine()
result = engine.analyze("mitdb_100.csv", patient_id="P-0100", center="CEN-001")
```
