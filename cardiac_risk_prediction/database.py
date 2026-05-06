import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.database import (  # noqa: E402,F401
    DB_PATH,
    fetch_latest_patient_context,
    fetch_predictions,
    init_db,
    next_patient_id,
    save_prediction,
)
