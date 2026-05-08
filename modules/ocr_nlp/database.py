import sqlite3
import json
import os
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

DEFAULT_DB_PATH = os.environ.get("OCR_DB_PATH", "ocr_nlp.db")

_CREATE_UPLOADS = """
CREATE TABLE IF NOT EXISTS uploads (
    upload_id       TEXT PRIMARY KEY,
    patient_id      TEXT NOT NULL,
    file_type       TEXT,
    document_type   TEXT,
    upload_date     TEXT,
    center_id       TEXT,
    technician_name TEXT,
    file_path       TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);
"""

_CREATE_EXTRACTED = """
CREATE TABLE IF NOT EXISTS extracted_data (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    upload_id       TEXT NOT NULL REFERENCES uploads(upload_id),
    patient_name    TEXT,
    age             TEXT,
    gender          TEXT,
    ecg_date        TEXT,
    heart_rate      TEXT,
    pr_interval     TEXT,
    qrs_duration    TEXT,
    qt_interval     TEXT,
    doctor_notes    TEXT,
    diagnosis_text  TEXT,
    confidence_score REAL,
    raw_lines_json  TEXT,
    processed_at    TEXT DEFAULT (datetime('now'))
);
"""


class DatabaseWrapper:
    """
    Thin wrapper around SQLite for the OCR/NLP module.

    Usage
    ─────
        db = DatabaseWrapper()          # uses default path
        db = DatabaseWrapper("my.db")   # custom path

        # As context manager (auto-closes):
        with DatabaseWrapper() as db:
            db.save_upload(meta)

    All public methods accept / return plain dicts or dataclass instances.
    No SQLite objects leak outside this class.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


    def _connect(self):
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row          # rows behave like dicts
        self._conn.execute("PRAGMA journal_mode=WAL")  # safe for concurrent reads
        self._init_schema()

    def _init_schema(self):
        with self._transaction():
            self._conn.execute(_CREATE_UPLOADS)
            self._conn.execute(_CREATE_EXTRACTED)

    @contextmanager
    def _transaction(self):
        """Yields cursor; commits on success, rolls back on exception."""
        cursor = self._conn.cursor()
        try:
            yield cursor
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cursor.close()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None


    def save_upload(self, meta) -> None:
        """
        Insert or replace a row in `uploads`.
        Accepts an UploadMeta dataclass or a plain dict.
        """
        d = meta if isinstance(meta, dict) else vars(meta)
        sql = """
            INSERT OR REPLACE INTO uploads
                (upload_id, patient_id, file_type, document_type,
                 upload_date, center_id, technician_name, file_path)
            VALUES
                (:upload_id, :patient_id, :file_type, :document_type,
                 :upload_date, :center_id, :technician_name, :file_path)
        """
        with self._transaction() as cur:
            cur.execute(sql, d)

    def get_upload(self, upload_id: str) -> Optional[dict]:
        """Fetch a single upload record by ID."""
        row = self._conn.execute(
            "SELECT * FROM uploads WHERE upload_id = ?", (upload_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_uploads(
        self,
        patient_id: Optional[str] = None,
        center_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """List uploads with optional filters."""
        clauses, params = [], []
        if patient_id:
            clauses.append("patient_id = ?")
            params.append(patient_id)
        if center_id:
            clauses.append("center_id = ?")
            params.append(center_id)

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM uploads {where} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def delete_upload(self, upload_id: str) -> bool:
        """Delete an upload and its extracted data. Returns True if found."""
        with self._transaction() as cur:
            cur.execute("DELETE FROM extracted_data WHERE upload_id = ?", (upload_id,))
            cur.execute("DELETE FROM uploads WHERE upload_id = ?", (upload_id,))
            return cur.rowcount > 0


    def save_extracted(self, upload_id: str, data) -> int:
        """
        Insert extracted data for a given upload_id.
        Accepts an ExtractedData dataclass or plain dict.
        Returns the new row id.
        """
        d = data if isinstance(data, dict) else vars(data)
        raw_json = json.dumps(d.get("raw_lines", []))

        sql = """
            INSERT INTO extracted_data
                (upload_id, patient_name, age, gender, ecg_date,
                 heart_rate, pr_interval, qrs_duration, qt_interval,
                 doctor_notes, diagnosis_text, confidence_score, raw_lines_json)
            VALUES
                (:upload_id, :patient_name, :age, :gender, :ecg_date,
                 :heart_rate, :pr_interval, :qrs_duration, :qt_interval,
                 :doctor_notes, :diagnosis_text, :confidence_score, :raw_lines_json)
        """
        params = {
            "upload_id": upload_id,
            "patient_name": d.get("patient_name"),
            "age": d.get("age"),
            "gender": d.get("gender"),
            "ecg_date": d.get("ecg_date"),
            "heart_rate": d.get("heart_rate"),
            "pr_interval": d.get("pr_interval"),
            "qrs_duration": d.get("qrs_duration"),
            "qt_interval": d.get("qt_interval"),
            "doctor_notes": d.get("doctor_notes"),
            "diagnosis_text": d.get("diagnosis_text"),
            "confidence_score": d.get("confidence_score", 0.0),
            "raw_lines_json": raw_json,
        }
        with self._transaction() as cur:
            cur.execute(sql, params)
            return cur.lastrowid

    def get_extracted(self, upload_id: str) -> Optional[dict]:
        """Fetch the most recent extraction result for an upload."""
        row = self._conn.execute(
            """SELECT * FROM extracted_data
               WHERE upload_id = ?
               ORDER BY processed_at DESC LIMIT 1""",
            (upload_id,),
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["raw_lines"] = json.loads(result.pop("raw_lines_json", "[]"))
        return result

    def list_extracted(self, limit: int = 100) -> list[dict]:
        """List all extraction results (latest first)."""
        rows = self._conn.execute(
            "SELECT * FROM extracted_data ORDER BY processed_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["raw_lines"] = json.loads(d.pop("raw_lines_json", "[]"))
            results.append(d)
        return results

    def get_stats(self) -> dict:
        """Quick summary stats for a dashboard."""
        row = self._conn.execute("""
            SELECT
                COUNT(*)                         AS total_uploads,
                COUNT(DISTINCT patient_id)       AS unique_patients,
                COUNT(DISTINCT center_id)        AS unique_centers,
                ROUND(AVG(e.confidence_score),2) AS avg_confidence
            FROM uploads u
            LEFT JOIN extracted_data e USING (upload_id)
        """).fetchone()
        return dict(row) if row else {}
