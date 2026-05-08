"""Final integration status check — tests each module in its proper context."""
import sys, os, subprocess

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

print("=" * 60)
print("  PROJECT INTEGRATION STATUS CHECK (FINAL)")
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

# 2. Check each module by running a subprocess that mimics the main_app.py import
modules = [
    ("Module 1 (OCR+NLP)",     "ocr_nlp",                     "import ocr_nlp; print(hasattr(ocr_nlp, 'launch'))"),
    ("Module 2 (ECG)",         "ecg_analysis",                 "import ecg_analysis; print(hasattr(ecg_analysis, 'launch'))"),
    ("Module 3 (Risk)",        "cardiac_risk_prediction",      "import cardiac_risk_prediction; print(hasattr(cardiac_risk_prediction, 'launch'))"),
    ("Module 4 (Summary)",     "integrated_clinical_summary",  "import integrated_clinical_summary; print(hasattr(integrated_clinical_summary, 'launch'))"),
    ("Module 5 (Tele-Card)",   "Decision Support",             "import importlib.util, sys; sys.path.insert(0,'Decision Support'); spec=importlib.util.spec_from_file_location('m5','Decision Support/tele_cardiology_decision_support.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); print(hasattr(mod,'launch'))"),
    ("Module 6 (Alerts)",      "unified_alert_dashboard",      "import unified_alert_dashboard; print(hasattr(unified_alert_dashboard, 'launch'))"),
    ("Module 8 (Sync)",        "offline_sync",                 "import offline_sync; print(hasattr(offline_sync, 'launch'))"),
]

print("\n--- MODULE LAUNCH CHECK ---")
for name, folder, check_code in modules:
    folder_path = os.path.join(ROOT, folder)
    if not os.path.isdir(folder_path):
        print(f"  {name}: FOLDER MISSING")
        continue

    has_init = os.path.exists(os.path.join(folder_path, "__init__.py"))
    has_ui = os.path.exists(os.path.join(folder_path, "ui.py"))

    # Run import test in subprocess with correct paths
    env_paths = os.pathsep.join([ROOT, folder_path])
    full_code = f"import sys; sys.path[:0]=[r'{ROOT}',r'{folder_path}']; {check_code}"
    result = subprocess.run(
        [sys.executable, "-c", full_code],
        capture_output=True, text=True, timeout=15, cwd=ROOT
    )

    if result.returncode == 0 and "True" in result.stdout:
        status = "OK — launch() ready"
    elif result.returncode == 0:
        status = "IMPORTED but no launch()"
    else:
        err = (result.stderr or "").strip().split("\n")[-1][:70]
        status = f"ERROR: {err}"

    flags = []
    if has_init:
        flags.append("init")
    if has_ui:
        flags.append("ui")
    flag_str = ",".join(flags) if flags else "no init/ui"

    print(f"  {name}: [{flag_str}] {status}")

# Dashboard
print("\n--- DASHBOARD ---")
try:
    sys.path.insert(0, os.path.join(ROOT, "dashboard-Tkinter"))
    from dashboard_app import AnalyticsDashboard
    print("  Module 7 (Dashboard-Tkinter): OK")
except Exception as e:
    print(f"  Module 7 (Dashboard-Tkinter): FAIL — {e}")

# Main launcher
print("\n--- MAIN LAUNCHER ---")
if os.path.exists(os.path.join(ROOT, "main_app.py")):
    print("  main_app.py: EXISTS")
else:
    print("  main_app.py: MISSING")

print("\n" + "=" * 60)
