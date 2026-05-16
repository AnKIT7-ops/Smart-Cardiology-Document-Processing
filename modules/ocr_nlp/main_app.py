"""
main_app.py — Smart Cardiology Document Processing
Central launcher. Initializes the shared DB and shows buttons for all 8 modules.
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.database import init_db

# ── Color palette ──────────────────────────────────────────────────────────────
BG      = "#1a1a2e"
CARD    = "#16213e"
ACCENT  = "#e94560"
TEXT    = "#eaeaea"
MUTED   = "#888888"
SUCCESS = "#00b894"
BLUE    = "#0984e3"
PURPLE  = "#6c5ce7"
TEAL    = "#00cec9"
ORANGE  = "#e17055"
YELLOW  = "#fdcb6e"
PINK    = "#fd79a8"
FONT_B  = ("Segoe UI", 10, "bold")
FONT_H  = ("Segoe UI", 18, "bold")

# ── Module registry ────────────────────────────────────────────────────────────
MODULES = [
    {
        "num": 1,
        "name": "AI Document Processing",
        "desc": "OCR scan + NLP extraction",
        "color": ACCENT,
        "import_path": ("modules.ocr_nlp", "launch"),
    },
    {
        "num": 2,
        "name": "ECG Signal Analysis",
        "desc": "Rhythm & ST-change detection",
        "color": BLUE,
        "import_path": ("modules.ecg_analysis", "launch"),
    },
    {
        "num": 3,
        "name": "Cardiac Risk Prediction",
        "desc": "Logistic Regression + XGBoost",
        "color": ORANGE,
        "import_path": ("modules.cardiac_risk_prediction", "launch"),
    },
    {
        "num": 4,
        "name": "Report Summarization AI",
        "desc": "Integrated clinical reports + PDF",
        "color": TEAL,
        "import_path": ("modules.integrated_clinical_summary", "launch"),
    },
    {
        "num": 5,
        "name": "Tele-Cardiology DSS",
        "desc": "Remote triage & referral support",
        "color": PURPLE,
        "import_path": ("modules.tele_cardiology", "launch"),
    },
    {
        "num": 6,
        "name": "Critical Alert System",
        "desc": "High-risk patient monitoring",
        "color": ACCENT,
        "import_path": ("modules.unified_alert_dashboard", "launch"),
    },
    {
        "num": 7,
        "name": "Analytics Dashboard",
        "desc": "Charts, trends & center stats",
        "color": SUCCESS,
        "import_path": ("modules.analytics_dashboard", "launch"),
    },
    {
        "num": 8,
        "name": "Offline Data Capture & Sync",
        "desc": "Rural offline entry + sync",
        "color": YELLOW,
        "import_path": ("modules.offline_sync", "launch"),
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# LAUNCHER WINDOW
# ──────────────────────────────────────────────────────────────────────────────

class LauncherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🫀  Smart Cardiology Document Processing")
        self.geometry("840x620")
        self.configure(bg=BG)
        self.resizable(False, False)
        self._build_ui()

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=ACCENT, pady=18)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🫀  Smart Cardiology Decision Support System",
                 font=FONT_H, bg=ACCENT, fg="white").pack()
        tk.Label(hdr, text="CAD Foundation · Mangaluru/Udupi District Health Network",
                 font=("Segoe UI", 10), bg=ACCENT, fg="white").pack()

        # Subtitle
        tk.Label(self, text="Select a module to launch:", font=("Segoe UI", 11),
                 bg=BG, fg=MUTED).pack(pady=(18, 8))

        # Module grid
        grid = tk.Frame(self, bg=BG)
        grid.pack(pady=4, padx=30)

        for i, mod in enumerate(MODULES):
            row, col = divmod(i, 4)
            self._module_card(grid, mod).grid(row=row, column=col, padx=10, pady=10)

        # Footer
        tk.Label(self, text="All modules share smart_cardiology.db · Python 3.10+ · Tkinter",
                 font=("Segoe UI", 8), bg=BG, fg=MUTED).pack(side="bottom", pady=10)

    def _module_card(self, parent, mod):
        frame = tk.Frame(parent, bg=CARD, width=172, height=110, relief="groove", bd=1)
        frame.pack_propagate(False)

        num_lbl = tk.Label(frame, text=f"Module {mod['num']}", font=("Segoe UI", 8),
                            bg=CARD, fg=MUTED)
        num_lbl.pack(anchor="w", padx=10, pady=(10, 0))

        title = tk.Label(frame, text=mod["name"], font=("Segoe UI", 9, "bold"),
                          bg=CARD, fg=TEXT, wraplength=150, justify="left")
        title.pack(anchor="w", padx=10)

        desc = tk.Label(frame, text=mod["desc"], font=("Segoe UI", 8),
                         bg=CARD, fg=MUTED, wraplength=150, justify="left")
        desc.pack(anchor="w", padx=10)

        btn = tk.Button(frame, text="Open →",
                         bg=mod["color"], fg="white", font=("Segoe UI", 8, "bold"),
                         relief="flat", padx=8, pady=3, cursor="hand2",
                         command=lambda m=mod: self._launch_module(m))
        btn.pack(anchor="e", padx=10, pady=(6, 10))

        return frame

    def _launch_module(self, mod):
        module_name, func_name = mod["import_path"]
        try:
            import importlib
            m = importlib.import_module(module_name)
            launch_fn = getattr(m, func_name)
            launch_fn(self)
        except ImportError as e:
            messagebox.showerror(
                "Module Not Ready",
                f"Module {mod['num']} ({mod['name']}) is not yet implemented.\n\nError: {e}"
            )
        except Exception as e:
            messagebox.showerror("Launch Error", str(e))


# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init  _db()
    app = LauncherApp()
    app.mainloop()
