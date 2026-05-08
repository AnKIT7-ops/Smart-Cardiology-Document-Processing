import threading
import time
import logging
import requests

from database import (
    fetch_pending_records,
    mark_as_synced,
    mark_as_failed,
    save_offline_record,
    init_db,
)


CENTRAL_API_URL   = "https://central-server.com/api/sync"   # ← update this
PING_URL          = "https://central-server.com/ping"        # ← health-check endpoint
SYNC_INTERVAL_SEC = 300        # auto-sync every 5 minutes
REQUEST_TIMEOUT   = 10         # seconds per HTTP request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [MODULE-8]  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("module8")

_on_sync_done_callbacks: list = []

def on_sync_done(callback):
    """Register a callback(stats: dict) to fire after each sync cycle."""
    _on_sync_done_callbacks.append(callback)

def _fire_callbacks(stats: dict):
    for cb in _on_sync_done_callbacks:
        try:
            cb(stats)
        except Exception as exc:
            log.warning("Callback error: %s", exc)


def is_online() -> bool:
    """
    Returns True if the central server is reachable.
    Uses a lightweight /ping endpoint to avoid heavy payloads.
    """
    try:
        resp = requests.get(PING_URL, timeout=REQUEST_TIMEOUT)
        return resp.status_code == 200
    except requests.exceptions.RequestException:
        return False


def sync_one_record(record: dict) -> bool:
    """
    Push a single PENDING record to the central server.
    Returns True on success, False on failure.
    """
    try:
        resp = requests.post(
            CENTRAL_API_URL,
            json=record,
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 200:
            mark_as_synced(record["local_record_id"])
            log.info("SYNCED   → %s", record["local_record_id"])
            return True
        else:
            mark_as_failed(record["local_record_id"])
            log.warning(
                "FAILED   → %s  (HTTP %s)",
                record["local_record_id"],
                resp.status_code,
            )
            return False
    except requests.exceptions.RequestException as exc:
        mark_as_failed(record["local_record_id"])
        log.error("ERROR    → %s  (%s)", record["local_record_id"], exc)
        return False


def run_sync_cycle(device_id: str = None) -> dict:
    """
    Attempt to sync all PENDING records for a device (or all devices).

    Returns a stats dict:
        { "attempted": int, "synced": int, "failed": int }
    """
    init_db()

    if not is_online():
        log.info("Offline — sync skipped.")
        return {"attempted": 0, "synced": 0, "failed": 0}

    pending = fetch_pending_records(device_id=device_id)
    stats   = {"attempted": len(pending), "synced": 0, "failed": 0}

    if not pending:
        log.info("No pending records to sync.")
    else:
        log.info("Syncing %d pending record(s)…", len(pending))
        for record in pending:
            if sync_one_record(record):
                stats["synced"] += 1
            else:
                stats["failed"] += 1

        log.info(
            "Cycle complete — synced: %d  failed: %d",
            stats["synced"],
            stats["failed"],
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
    """Returns True if the background sync thread is active."""
    return bool(_scheduler_thread and _scheduler_thread.is_alive())


if __name__ == "__main__":
    from database import save_offline_record

    for mod in ["MODULE_1", "MODULE_2", "MODULE_3"]:
        rid = save_offline_record(mod, device_id="DEV-MANGALURU-01")
        print(f"Saved offline record: {rid}  [{mod}]")

    print("\nRunning one manual sync cycle…")
    stats = run_sync_cycle(device_id="DEV-MANGALURU-01")
    print(f"Result: {stats}")
