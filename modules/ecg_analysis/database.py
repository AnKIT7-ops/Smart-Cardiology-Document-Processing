import os
import re
import sqlite3
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.database import (  # noqa: E402,F401
    CENTER_ID_TO_NAME,
    CENTER_NAME_TO_ID,
    DB_PATH,
    DEFAULT_CENTERS,
    center_id_for,
    center_name_for,
    get_connection,
    init_db,
    next_patient_id,
    now_text,
    normalize_risk_level,
    upsert_patient,
)


PATIENT_ID_RE = re.compile(r"^P-(\d+)$", re.IGNORECASE)
RHYTHM_VALUES = {"Normal", "Arrhythmia"}
ABNORMALITY_VALUES = {"No", "ST Depression", "ST Elevation", "LV Hypertrophy", "Other"}
ST_CHANGE_VALUES = {"Normal", "ST Elevation", "ST Depression"}
STATUS_VALUES = {"PENDING", "PROCESSING", "COMPLETED", "FAILED"}


def normalize_patient_id(patient_id):
    """Return a shared patient ID in P-XXXX format."""
    text = str(patient_id or "").strip()
    match = PATIENT_ID_RE.match(text)
    if match:
        return f"P-{int(match.group(1)):04d}"
    return next_patient_id()


def next_ecg_id():
    """Return the next ECG ID in ECG-XXXX format."""
    init_db()
    with get_connection() as conn:
        max_ecg = conn.execute(
            """
            SELECT COALESCE(MAX(CAST(SUBSTR(ecg_id, 5) AS INTEGER)), 0)
            FROM tbl_ecg_data
            WHERE ecg_id LIKE 'ECG-%'
            """
        ).fetchone()[0]
    return f"ECG-{int(max_ecg) + 1:04d}"


def _allowed(value, allowed, default):
    text = str(value or "").strip()
    return text if text in allowed else default


def _heart_rate_value(value):
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _confidence_value(value):
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, score))


def save_ecg_result(
    patient_id,
    center,
    heart_rate,
    rhythm_type,
    abnormality_detected,
    st_change,
    confidence_score,
    ai_remarks,
    ecg_id=None,
    patient_name=None,
    age=None,
    gender=None,
    status="COMPLETED",
    created_at=None,
):
    """
    Save one Module 2 result into tbl_ecg_data using the integration-guide schema.
    """
    init_db()
    patient_id = normalize_patient_id(patient_id)
    center_id = center_id_for(center)
    ecg_id = str(ecg_id or "").strip() or next_ecg_id()
    status = _allowed(status, STATUS_VALUES, "COMPLETED")
    created_at = created_at or now_text()

    upsert_patient(
        patient_id=patient_id,
        patient_name=patient_name,
        age=age,
        gender=gender,
        center=center_id,
        source_module="MODULE_2",
    )

    values = (
        ecg_id,
        patient_id,
        center_id,
        _heart_rate_value(heart_rate),
        _allowed(rhythm_type, RHYTHM_VALUES, "Arrhythmia"),
        _allowed(abnormality_detected, ABNORMALITY_VALUES, "Other"),
        _allowed(st_change, ST_CHANGE_VALUES, "Normal"),
        _confidence_value(confidence_score),
        str(ai_remarks or ""),
        status,
        created_at,
    )

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO tbl_ecg_data (
                ecg_id, patient_id, center_id, heart_rate, rhythm_type,
                abnormality_detected, st_change, confidence_score,
                ai_remarks, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )

    return ecg_id, patient_id


def fetch_ecg_history(patient_id=None):
    """Return ECG rows shaped for the existing ECG history screen."""
    init_db()
    where = ""
    params = ()
    if patient_id:
        where = "WHERE e.patient_id = ?"
        params = (normalize_patient_id(patient_id),)

    query = f"""
        SELECT
            e.ecg_id AS id,
            e.patient_id,
            e.created_at AS timestamp,
            e.center_id,
            c.center_name,
            e.heart_rate,
            CASE
                WHEN e.abnormality_detected = 'No' THEN e.rhythm_type
                ELSE e.abnormality_detected
            END AS diagnosis,
            e.confidence_score AS confidence,
            CASE
                WHEN e.abnormality_detected = 'No' THEN 'Low'
                WHEN e.abnormality_detected IN ('ST Elevation', 'ST Depression') THEN 'High'
                ELSE 'Moderate'
            END AS adjusted_risk,
            e.ai_remarks,
            1.0 AS signal_quality,
            e.status
        FROM tbl_ecg_data e
        LEFT JOIN tbl_centers c ON c.center_id = e.center_id
        {where}
        ORDER BY datetime(e.created_at) DESC, e.ecg_id DESC
    """
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def append_ecg_note(ecg_id, notes):
    """Store physician notes in ai_remarks because tbl_ecg_data has no note column."""
    notes = str(notes or "").strip()
    if not notes:
        return
    init_db()
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT ai_remarks FROM tbl_ecg_data WHERE ecg_id = ?",
            (ecg_id,),
        ).fetchone()
        if not existing:
            return
        current = existing[0] or ""
        updated = f"{current}\nPhysician notes: {notes}".strip()
        conn.execute(
            "UPDATE tbl_ecg_data SET ai_remarks = ? WHERE ecg_id = ?",
            (updated, ecg_id),
        )
