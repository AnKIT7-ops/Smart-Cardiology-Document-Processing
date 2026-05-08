import sqlite3
import uuid
from datetime import datetime

DB_PATH = "local_cad_sync.db"


def now_text() -> str:
    """Return current timestamp as a formatted string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection to the local database."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")   # safe for concurrent reads/writes
    return conn


def init_db():
    """Create tbl_sync_status if it does not exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tbl_sync_status (
                local_record_id TEXT PRIMARY KEY,
                module_name     TEXT NOT NULL,
                sync_status     TEXT NOT NULL CHECK(sync_status IN ('PENDING','SYNCED','FAILED')),
                device_id       TEXT,
                last_sync_time  TEXT
            )
        """)

def save_offline_record(module_name: str, device_id: str) -> str:
    """
    Mark a locally-saved record as pending sync.
    Returns the generated local_record_id.
    """
    init_db()
    record_id = f"SYNC-{uuid.uuid4().hex[:8].upper()}"
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO tbl_sync_status (
                local_record_id, module_name, sync_status,
                device_id, last_sync_time
            )
            VALUES (?, ?, 'PENDING', ?, ?)
            """,
            (record_id, module_name, device_id, now_text()),
        )
    return record_id


def mark_as_synced(local_record_id: str):
    """Update status to SYNCED after a successful sync."""
    init_db()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE tbl_sync_status
            SET sync_status = 'SYNCED', last_sync_time = ?
            WHERE local_record_id = ?
            """,
            (now_text(), local_record_id),
        )


def mark_as_failed(local_record_id: str):
    """Update status to FAILED after a sync attempt error."""
    init_db()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE tbl_sync_status
            SET sync_status = 'FAILED', last_sync_time = ?
            WHERE local_record_id = ?
            """,
            (now_text(), local_record_id),
        )


def delete_record(local_record_id: str):
    """Remove a record from the local sync table."""
    init_db()
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM tbl_sync_status WHERE local_record_id = ?",
            (local_record_id,),
        )


# ─────────────────────────────────────────────
# READ OPERATIONS
# ─────────────────────────────────────────────

def fetch_pending_records(device_id: str = None) -> list[dict]:
    """Return all PENDING records, optionally filtered by device_id."""
    init_db()
    query = "SELECT * FROM tbl_sync_status WHERE sync_status = 'PENDING'"
    params = []
    if device_id:
        query += " AND device_id = ?"
        params.append(device_id)
    query += " ORDER BY last_sync_time DESC"
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def fetch_all_records() -> list[dict]:
    """Return every record in tbl_sync_status, newest first."""
    init_db()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM tbl_sync_status ORDER BY last_sync_time DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def count_by_status() -> dict:
    """Return counts grouped by sync_status: {PENDING, SYNCED, FAILED}."""
    init_db()
    counts = {"PENDING": 0, "SYNCED": 0, "FAILED": 0}
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT sync_status, COUNT(*) FROM tbl_sync_status GROUP BY sync_status"
        ).fetchall()
        for status, count in rows:
            counts[status] = count
    return counts
