"""Integration status check — verifies all modules under modules/ folder."""
import sys, os, subprocess

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.join(ROOT, "modules")
os.chdir(ROOT)

print("=" * 60)
print("  PROJECT INTEGRATION STATUS CHECK")
print("=" * 60)

# 1. Shared DB
sys.path.insert(0, ROOT)
from shared.database import init_db, fetch_predictions, fetch_patient_ids, fetch_unified_alerts
init_db()
pids = fetch_patient_ids()
preds = fetch_predictions()
alerts = fetch_unified_alerts()
print(f"\n--- SHARED DATABASE ---")
print(f"  init_db(): OK")
print(f"  Patients: {len(pids)}")
print(f"  Predictions: {len(preds)}")
print(f"  Alerts: {len(alerts)}")

# 2. Check each module
modules = [
    ("Module 1 (OCR+NLP)",     "ocr_nlp"),
    ("Module 2 (ECG)",         "ecg_analysis"),
    ("Module 3 (Risk)",        "cardiac_risk_prediction"),
    ("Module 4 (Summary)",     "integrated_clinical_summary"),
    ("Module 5 (Tele-Card)",   "tele_cardiology"),
    ("Module 6 (Alerts)",      "unified_alert_dashboard"),
    ("Module 8 (Sync)",        "offline_sync"),
]

print("\n--- MODULE LAUNCH CHECK ---")
for name, folder in modules:
    folder_path = os.path.join(MODULES_DIR, folder)
    if not os.path.isdir(folder_path):
        print(f"  {name}: FOLDER MISSING (modules/{folder}/)")
        continue

    has_init = os.path.exists(os.path.join(folder_path, "__init__.py"))
    has_ui = os.path.exists(os.path.join(folder_path, "ui.py"))
    flags = []
    if has_init: flags.append("init")
    if has_ui: flags.append("ui")

    # Test import in subprocess
    check_code = (
        f"import sys; sys.path[:0]=[r'{ROOT}',r'{folder_path}'];"
        f"from modules.{folder} import launch; print(callable(launch))"
    )
    result = subprocess.run(
        [sys.executable, "-c", check_code],
        capture_output=True, text=True, timeout=15, cwd=ROOT,
    )
    if result.returncode == 0 and "True" in result.stdout:
        status = "OK — launch() ready"
    else:
        err = (result.stderr or "").strip().split("\n")[-1][:70]
        status = f"ERROR: {err}"

    print(f"  {name}: [{','.join(flags)}] {status}")

# Dashboard
print("\n--- DASHBOARD ---")
dash_path = os.path.join(MODULES_DIR, "analytics_dashboard")
if os.path.isdir(dash_path):
    try:
        sys.path.insert(0, dash_path)
        from dashboard_app import AnalyticsDashboard
        print("  Module 7 (Analytics Dashboard): OK")
    except Exception as e:
        print(f"  Module 7 (Analytics Dashboard): FAIL — {e}")
else:
    print("  Module 7: FOLDER MISSING")

# Files
print("\n--- PROJECT FILES ---")
for f in ["main_app.py", "README.md", "requirements.txt", "INTEGRATION_GUIDE_V2.md"]:
    exists = os.path.exists(os.path.join(ROOT, f))
    print(f"  {f}: {'EXISTS' if exists else 'MISSING'}")

print("\n" + "=" * 60)
