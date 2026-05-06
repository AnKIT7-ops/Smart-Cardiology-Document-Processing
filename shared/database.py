import os
import sqlite3
from datetime import datetime


PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(PACKAGE_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "smart_cardiology.db")


DEFAULT_CENTERS = [
    ("CEN-001", "Mangaluru Central", "Mangaluru"),
    ("CEN-002", "Udupi District", "Udupi"),
    ("CEN-003", "Puttur PHC", "Puttur"),
    ("CEN-004", "Bantwal CHC", "Bantwal"),
    ("CEN-005", "Sullia PHC", "Sullia"),
    ("CEN-006", "Belthangady PHC", "Belthangady"),
]

RISK_LEVEL_MAP = {
    "Low": "LOW",
    "Medium": "MODERATE",
    "Moderate": "MODERATE",
    "High": "HIGH",
    "LOW": "LOW",
    "MODERATE": "MODERATE",
    "HIGH": "HIGH",
}

CENTER_NAME_TO_ID = {name: center_id for center_id, name, _ in DEFAULT_CENTERS}
CENTER_ID_TO_NAME = {center_id: name for center_id, name, _ in DEFAULT_CENTERS}


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_connection():
    return sqlite3.connect(DB_PATH)


def normalize_risk_level(risk_level):
    text = str(risk_level).strip()
    return RISK_LEVEL_MAP.get(text, text.upper())


def center_id_for(center):
    center = str(center or "").strip()
    if center in CENTER_ID_TO_NAME:
        return center
    return CENTER_NAME_TO_ID.get(center, "CEN-001")


def center_name_for(center):
    center = str(center or "").strip()
    if center in CENTER_ID_TO_NAME:
        return CENTER_ID_TO_NAME[center]
    return center or "Mangaluru Central"


def init_db():
    """Create all shared tables used by the project modules."""
    with get_connection() as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tbl_centers (
                center_id TEXT PRIMARY KEY,
                center_name TEXT NOT NULL,
                district TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at TEXT NOT NULL
            )
            """
        )

        conn.executemany(
            """
            INSERT OR IGNORE INTO tbl_centers (
                center_id, center_name, district, status, created_at
            )
            VALUES (?, ?, ?, 'ACTIVE', ?)
            """,
            [(center_id, name, district, now_text()) for center_id, name, district in DEFAULT_CENTERS],
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tbl_patients (
                patient_id TEXT PRIMARY KEY,
                patient_name TEXT,
                age INTEGER,
                gender TEXT,
                center_id TEXT,
                source_module TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tbl_reports (
                report_id TEXT PRIMARY KEY,
                upload_id TEXT,
                patient_id TEXT NOT NULL,
                center_id TEXT,
                document_type TEXT,
                extracted_text TEXT,
                diagnosis_text TEXT,
                doctor_notes TEXT,
                confidence_score REAL,
                status TEXT NOT NULL DEFAULT 'COMPLETED',
                created_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tbl_ecg_data (
                ecg_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                center_id TEXT,
                heart_rate INTEGER,
                rhythm_type TEXT,
                abnormality_detected TEXT,
                st_change TEXT,
                confidence_score REAL,
                ai_remarks TEXT,
                status TEXT NOT NULL DEFAULT 'COMPLETED',
                created_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tbl_ai_predictions (
                prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                center_id TEXT NOT NULL,
                center_name TEXT NOT NULL,
                doctor_name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                bp INTEGER NOT NULL,
                cholesterol INTEGER NOT NULL,
                diabetes TEXT NOT NULL,
                smoking TEXT NOT NULL,
                ecg_result TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                probability REAL NOT NULL,
                suggested_action TEXT NOT NULL,
                followup_required TEXT NOT NULL,
                model_used TEXT NOT NULL,
                source_module TEXT NOT NULL DEFAULT 'MODULE_3',
                created_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tbl_alerts (
                alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                prediction_id INTEGER,
                alert_type TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN',
                created_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tbl_sync_status (
                local_record_id TEXT PRIMARY KEY,
                module_name TEXT NOT NULL,
                sync_status TEXT NOT NULL,
                device_id TEXT,
                last_sync_time TEXT
            )
            """
        )

        _create_indexes(conn)
        _migrate_legacy_predictions(conn)


def _create_indexes(conn):
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_predictions_created_at
        ON tbl_ai_predictions(created_at)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_predictions_patient_id
        ON tbl_ai_predictions(patient_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_predictions_center_id
        ON tbl_ai_predictions(center_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_predictions_risk_level
        ON tbl_ai_predictions(risk_level)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ecg_patient_id
        ON tbl_ecg_data(patient_id)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_reports_patient_id
        ON tbl_reports(patient_id)
        """
    )


def _migrate_legacy_predictions(conn):
    legacy_exists = conn.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type = 'table' AND name = 'predictions'
        """
    ).fetchone()
    if not legacy_exists:
        return

    old_count = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
    new_count = conn.execute("SELECT COUNT(*) FROM tbl_ai_predictions").fetchone()[0]
    if old_count == 0 or new_count > 0:
        return

    rows = conn.execute(
        """
        SELECT patient_id, center, doctor_name, age, gender, bp, cholesterol,
               diabetes, smoking, ecg_result, risk_level, probability, action,
               followup, model_used, created_at
        FROM predictions
        ORDER BY id
        """
    ).fetchall()

    for row in rows:
        center_id = center_id_for(row[1])
        conn.execute(
            """
            INSERT INTO tbl_ai_predictions (
                patient_id, center_id, center_name, doctor_name, age, gender,
                bp, cholesterol, diabetes, smoking, ecg_result, risk_level,
                probability, suggested_action, followup_required, model_used,
                source_module, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'MODULE_3', ?)
            """,
            (
                row[0],
                center_id,
                center_name_for(row[1]),
                row[2],
                row[3],
                row[4],
                row[5],
                row[6],
                row[7],
                row[8],
                row[9],
                normalize_risk_level(row[10]),
                row[11],
                row[12],
                row[13],
                row[14],
                row[15],
            ),
        )


def next_patient_id():
    """Return the next simple patient ID, for example P-0001."""
    init_db()
    with get_connection() as conn:
        max_prediction = conn.execute(
            """
            SELECT COALESCE(MAX(CAST(SUBSTR(patient_id, 3) AS INTEGER)), 0)
            FROM tbl_ai_predictions
            WHERE patient_id LIKE 'P-%'
            """
        ).fetchone()[0]
        max_patient = conn.execute(
            """
            SELECT COALESCE(MAX(CAST(SUBSTR(patient_id, 3) AS INTEGER)), 0)
            FROM tbl_patients
            WHERE patient_id LIKE 'P-%'
            """
        ).fetchone()[0]
    return f"P-{max(max_prediction, max_patient) + 1:04d}"


def upsert_patient(patient_id, age=None, gender=None, center=None, patient_name=None,
                   source_module="MODULE_3"):
    init_db()
    center_id = center_id_for(center)
    timestamp = now_text()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO tbl_patients (
                patient_id, patient_name, age, gender, center_id,
                source_module, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(patient_id) DO UPDATE SET
                patient_name = COALESCE(excluded.patient_name, tbl_patients.patient_name),
                age = COALESCE(excluded.age, tbl_patients.age),
                gender = COALESCE(excluded.gender, tbl_patients.gender),
                center_id = COALESCE(excluded.center_id, tbl_patients.center_id),
                source_module = excluded.source_module,
                updated_at = excluded.updated_at
            """,
            (
                patient_id,
                patient_name,
                age,
                gender,
                center_id,
                source_module,
                timestamp,
                timestamp,
            ),
        )


def save_prediction(data):
    """
    Save one Module 3 prediction and return the patient ID used.

    Expected keys: patient_id, center, doctor_name, age, gender, bp,
    cholesterol, diabetes, smoking, ecg_result, risk_level, probability,
    action, followup, model_used.
    """
    init_db()
    patient_id = str(data.get("patient_id") or "").strip() or next_patient_id()
    center = data.get("center") or data.get("center_name") or "Mangaluru Central"
    center_id = center_id_for(center)
    center_name = center_name_for(center)
    doctor_name = str(data.get("doctor_name") or "Not Assigned").strip()
    created_at = data.get("created_at") or now_text()

    upsert_patient(
        patient_id=patient_id,
        age=int(data["age"]),
        gender=str(data["gender"]),
        center=center_id,
        source_module="MODULE_3",
    )

    values = (
        patient_id,
        center_id,
        center_name,
        doctor_name,
        int(data["age"]),
        str(data["gender"]),
        int(data["bp"]),
        int(data["cholesterol"]),
        str(data["diabetes"]),
        str(data["smoking"]),
        str(data["ecg_result"]),
        normalize_risk_level(data["risk_level"]),
        float(data["probability"]),
        str(data["action"]),
        str(data["followup"]),
        str(data["model_used"]),
        created_at,
    )

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tbl_ai_predictions (
                patient_id, center_id, center_name, doctor_name, age, gender,
                bp, cholesterol, diabetes, smoking, ecg_result, risk_level,
                probability, suggested_action, followup_required, model_used,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        prediction_id = cursor.lastrowid
        if normalize_risk_level(data["risk_level"]) == "HIGH":
            conn.execute(
                """
                INSERT INTO tbl_alerts (
                    patient_id, prediction_id, alert_type, message, status, created_at
                )
                VALUES (?, ?, 'High Risk', ?, 'OPEN', ?)
                """,
                (
                    patient_id,
                    prediction_id,
                    "High cardiac risk prediction requires urgent review.",
                    created_at,
                ),
            )

    return patient_id


def fetch_predictions(limit=None):
    """Fetch saved Module 3 predictions, newest first."""
    init_db()
    query = """
        SELECT
            patient_id,
            center_name AS center,
            doctor_name,
            age,
            gender,
            bp,
            cholesterol,
            diabetes,
            smoking,
            ecg_result,
            risk_level,
            probability,
            suggested_action AS action,
            followup_required AS followup,
            model_used,
            created_at
        FROM tbl_ai_predictions
        ORDER BY datetime(created_at) DESC, prediction_id DESC
    """
    params = ()
    if limit is not None:
        query += " LIMIT ?"
        params = (int(limit),)

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def fetch_latest_patient_context(patient_id):
    """Return data Module 3 can auto-fill once Modules 1 and 2 are connected."""
    init_db()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        patient = conn.execute(
            """
            SELECT p.patient_id, p.patient_name, p.age, p.gender,
                   c.center_name AS center
            FROM tbl_patients p
            LEFT JOIN tbl_centers c ON c.center_id = p.center_id
            WHERE p.patient_id = ?
            """,
            (patient_id,),
        ).fetchone()
        ecg = conn.execute(
            """
            SELECT heart_rate, rhythm_type, abnormality_detected, st_change,
                   confidence_score, ai_remarks
            FROM tbl_ecg_data
            WHERE patient_id = ? AND status = 'COMPLETED'
            ORDER BY datetime(created_at) DESC
            LIMIT 1
            """,
            (patient_id,),
        ).fetchone()

    return {
        "patient": dict(patient) if patient else None,
        "ecg": dict(ecg) if ecg else None,
    }
