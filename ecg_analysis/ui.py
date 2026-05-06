import importlib.util
import sys
from pathlib import Path

from .database import init_db


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LEGACY_ECG_PATH = PROJECT_ROOT / "ecg analysis" / "ecg_ai_system23.py"


def _load_legacy_module():
    legacy_dir = str(LEGACY_ECG_PATH.parent)
    if legacy_dir not in sys.path:
        sys.path.insert(0, legacy_dir)

    spec = importlib.util.spec_from_file_location(
        "smart_cardiology_ecg_ai_system23",
        LEGACY_ECG_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load ECG module from {LEGACY_ECG_PATH}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def launch(parent):
    """Called by the main launcher to open Module 2 as a Toplevel window."""
    init_db()
    legacy = _load_legacy_module()
    window = legacy.tk.Toplevel(parent)
    return legacy.ECGApp(window)
