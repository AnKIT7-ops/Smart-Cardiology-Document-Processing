# ============================================================
# MODULE 3 - CARDIAC RISK PREDICTION
# File: main.py
# Purpose: Entry point — launches the Tkinter application
# ============================================================
#
# HOW TO RUN:
#   1. Make sure you are in the cardiac_risk_prediction folder:
#        cd cardiac_risk_prediction
#   2. Run this file:
#        python main.py
#
# PREREQUISITES:
#   pip install pandas numpy scikit-learn xgboost
#
# WHAT HAPPENS:
#   - On first run, the models are trained automatically from
#     heart_disease_uci.csv and saved to saved_models/.
#   - On subsequent runs, saved models are loaded instantly.
#   - You can re-train anytime using the "Train Model" button.
#
# FUTURE INTEGRATION NOTE:
# -----------------------------------------------------------------
# To connect Module 2 (ECG Analysis):
#   - Import the ECG module in ui.py
#   - Add a button "Load ECG" that calls the ECG analysis function
#   - Populate the ECG Result dropdown with the analysis output
# -----------------------------------------------------------------

import tkinter as tk

try:
    from .ui import CardiacRiskApp
except ImportError:
    from ui import CardiacRiskApp


def main():
    """Create the Tkinter root window and start the application."""
    root = tk.Tk()
    app = CardiacRiskApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
