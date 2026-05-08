import sqlite3
import threading
import time
import logging
from pathlib import Path

from database import (
    fetch_pending_records,
    mark_as_synced,
    mark_as_failed,
    init_db,
    DB_PATH as LOCAL_DB_PATH,
)


MAIN_DB_PATH      = "smart_cardiology.db"   
SYNC_INTERVAL_SEC = 300                   

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [MODULE-8]  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("module8")

_on_sync_done_callbacks: list = []

def on_sync_done(callback):
    """Register a callback(stats: dict) fired after every sync cycle."""
    _on_sync_done_callbacks.append(callback)

def _fire_callbacks(stats: dict):
    for cb in _on_sync_done_callbacks:
        try:
            cb(stats)
        except Exception as exc:
            log.warning("Callback error: %s", exc)



def is_main_db_accessible() -> bool:
    """
    Returns True if smart_cardiology.db exists and can be opened.
    Replaces the old HTTP /ping check — no network needed.
    """
    try:
        if not Path(MAIN_DB_PATH).exists():
            return False
        conn = sqlite3.connect(MAIN_DB_PATH)
        conn.execute("SELECT 1")
        conn.close()
        return True
    except sqlite3.Error:
        return False



def _ensure_main_table():
    """
    Create tbl_sync_status in smart_cardiology.db if it doesn't exist yet.
    Uses the exact same schema as the local copy.
    """
    conn = sqlite3.connect(MAIN_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tbl_sync_status (
            local_record_id TEXT PRIMARY KEY,
            module_name     TEXT NOT NULL,
            sync_status     TEXT NOT NULL CHECK(sync_status IN ('PENDING','SYNCED','FAILED')),
            device_id       TEXT,
            last_sync_time  TEXT
        )
    """)
    conn.commit()
    conn.close()



def sync_one_record(record: dict) -> bool:
    """
    Upsert a single PENDING record into smart_cardiology.db → tbl_sync_status.
    Returns True on success, False on failure.
    """
    try:
        _ensure_main_table()
        conn = sqlite3.connect(MAIN_DB_PATH)
        conn.execute(
            """
            INSERT INTO tbl_sync_status
                (local_record_id, module_name, sync_status, device_id, last_sync_time)
            VALUES (?, ?, 'SYNCED', ?, ?)
            ON CONFLICT(local_record_id) DO UPDATE SET
                sync_status    = 'SYNCED',
                last_sync_time = excluded.last_sync_time
            """,
            (
                record["local_record_id"],
                record["module_name"],
                record.get("device_id"),
                record.get("last_sync_time"),
            ),
        )
        conn.commit()
        conn.close()

        mark_as_synced(record["local_record_id"])
        log.info("SYNCED   → %s", record["local_record_id"])
        return True

    except sqlite3.Error as exc:
        mark_as_failed(record["local_record_id"])
        log.error("FAILED   → %s  (%s)", record["local_record_id"], exc)
        return False


def run_sync_cycle(device_id: str = None) -> dict:
    """
    Sync all PENDING local records into smart_cardiology.db.

    Returns stats dict: { "attempted": int, "synced": int, "failed": int }
    """
    init_db()

    if not is_main_db_accessible():
        log.warning("smart_cardiology.db not accessible — sync skipped.")
        return {"attempted": 0, "synced": 0, "failed": 0}

    pending = fetch_pending_records(device_id=device_id)
    stats   = {"attempted": len(pending), "synced": 0, "failed": 0}

    if not pending:
        log.info("No pending records to sync.")
    else:
        log.info("Syncing %d pending record(s) → %s …", len(pending), MAIN_DB_PATH)
        for record in pending:
            if sync_one_record(record):
                stats["synced"] += 1
            else:
                stats["failed"] += 1
        log.info(
            "Cycle complete — synced: %d  failed: %d",
            stats["synced"], stats["failed"],
        )

    _fire_callbacks(stats)
    return stats



_scheduler_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _scheduler_loop(device_id: str = None):
    """Internal loop — runs sync every SYNC_INTERVAL_SEC seconds."""
    log.info("Scheduler started (interval: %ds).", SYNC_INTERVAL_SEC)
    while not _stop_event.is_set():
        run_sync_cycle(device_id=device_id)
        for _ in range(SYNC_INTERVAL_SEC * 2):
            if _stop_event.is_set():
                break
            time.sleep(0.5)
    log.info("Scheduler stopped.")


def start_scheduler(device_id: str = None):
    """Start the background auto-sync thread (idempotent)."""
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        log.info("Scheduler already running.")
        return
    _stop_event.clear()
    _scheduler_thread = threading.Thread(
        target=_scheduler_loop,
        args=(device_id,),
        daemon=True,
        name="Module8-Sync",
    )
    _scheduler_thread.start()


def stop_scheduler():
    """Signal the background sync thread to stop."""
    _stop_event.set()
    log.info("Stop signal sent to scheduler.")


def scheduler_is_running() -> bool:
    return bool(_scheduler_thread and _scheduler_thread.is_alive())



if __name__ == "__main__":
    from database import save_offline_record

    for mod in ["MODULE_1", "MODULE_2", "MODULE_3"]:
        rid = save_offline_record(mod, device_id="DEV-MANGALURU-01")
        print(f"Saved offline record: {rid}  [{mod}]")

    print(f"\nMain DB accessible: {is_main_db_accessible()}")
    print("Running one manual sync cycle…")
    stats = run_sync_cycle(device_id="DEV-MANGALURU-01")
    print(f"Result: {stats}")
