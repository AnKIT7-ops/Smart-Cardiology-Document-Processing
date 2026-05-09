"""
Smart Cardiology Document Processing — Main Launcher
=====================================================
Run:  python main_app.py

Opens a central dashboard where each module can be launched
as an independent window. All modules share data through
the SQLite database (smart_cardiology.db).
"""

import importlib
import importlib.util
import os
import sys
import tkinter as tk
from tkinter import messagebox

# ── Project root setup ─────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.join(PROJECT_ROOT, "modules")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.database import init_db  # noqa: E402

# ── Module registry ────────────────────────────────────────
# (button_label, icon, folder_inside_modules, launch_strategy)
#
# launch_strategy:
#   "package"   → import modules.<folder> as a package, call .launch(parent)
#   "dashboard" → special handling for Module 7

MODULES = [
    ("AI Document Processing (OCR + NLP)",  "📄", "ocr_nlp",                     "package"),
    ("ECG Signal Analysis AI",              "💓", "ecg_analysis",                "package"),
    ("Cardiac Risk Prediction",             "🎯", "cardiac_risk_prediction",     "package"),
    ("Integrated Clinical Summary",         "📋", "integrated_clinical_summary", "package"),
    ("Tele-Cardiology Decision Support",    "📡", "tele_cardiology",             "package"),
    ("Critical Alert System",               "🚨", "unified_alert_dashboard",     "package"),
    ("Analytics Dashboard",                 "📊", "analytics_dashboard",         "dashboard"),
    ("Offline Data Capture & Sync",         "🔄", "offline_sync",                "package"),
]       

# ── Colors ─────────────────────────────────────────────────
BG          = "#0f172a"
CARD        = "#1e293b"
HEADER_BG   = "#1d4ed8"
TEXT        = "#f1f5f9"
MUTED       = "#94a3b8"
ACCENT      = "#3b82f6"
HOVER       = "#2563eb"
BORDER      = "#334155"
MODULE_COLORS = [
    "#3b82f6", "#8b5cf6", "#ef4444", "#f59e0b",
    "#06b6d4", "#ec4899", "#10b981", "#6366f1",
]


# ── Launch helpers ─────────────────────────────────────────

def _ensure_path(*paths):
    """Add directories to sys.path if not already present."""
    for p in paths:
        if p not in sys.path:
            sys.path.insert(0, p)


def _launch_package(folder, parent):
    """Import a module package from modules/<folder> and call launch(parent)."""
    folder_path = os.path.join(MODULES_DIR, folder)
    _ensure_path(MODULES_DIR, folder_path)

    pkg_name = f"modules.{folder}"
    # Clear stale cache if re-opening the same module
    if pkg_name in sys.modules:
        mod = sys.modules[pkg_name]
    else:
        mod = importlib.import_module(pkg_name)
    mod.launch(parent)


def _launch_dashboard(parent):
    """Special handling for Module 7 — AnalyticsDashboard takes a root window."""
    folder_path = os.path.join(MODULES_DIR, "analytics_dashboard")
    _ensure_path(folder_path)

    from dashboard_app import AnalyticsDashboard  # noqa: E402

    window = tk.Toplevel(parent)
    AnalyticsDashboard(window)


def open_module(label, folder, method, parent):
    """Open a module window, catching errors gracefully."""
    try:
        if method == "package":
            _launch_package(folder, parent)
        elif method == "dashboard":
            _launch_dashboard(parent)
        else:
            raise ValueError(f"Unknown method: {method}")
    except Exception as exc:
        messagebox.showerror(
            f"Cannot Open {label}",
            f"{exc}\n\n"
            f"Make sure all dependencies are installed:\n"
            f"  pip install -r requirements.txt",
        )


# ── Launcher UI ────────────────────────────────────────────

class LauncherApp:
    """Central launcher for all Smart Cardiology modules."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Smart Cardiology — Module Launcher")
        self.root.geometry("640x760")
        self.root.minsize(560, 640)
        self.root.configure(bg=BG)

        try:
            init_db()
        except Exception as e:
            messagebox.showwarning("Database Warning", f"init_db() failed:\n{e}")

        self._build_ui()

    def _build_ui(self):
        # ── Header ──
        header = tk.Frame(self.root, bg=HEADER_BG, height=110)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header, text="",
            bg=HEADER_BG, font=("Segoe UI", 32),
        ).pack(pady=(14, 0))

        tk.Label(
            header, text="Smart Cardiology Document Processing",
            bg=HEADER_BG, fg="white",
            font=("Segoe UI", 15, "bold"),
        ).pack()

        tk.Label(
            header, text="Mangaluru / Udupi District Health Network  ·  8 Modules",
            bg=HEADER_BG, fg="#bfdbfe",
            font=("Segoe UI", 9),
        ).pack()

        # ── Accent bar ──
        tk.Frame(self.root, bg=ACCENT, height=3).pack(fill="x")

        # ── Module buttons ──
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=28, pady=20)

        tk.Label(
            body, text="Launch a Module",
            bg=BG, fg=TEXT,
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        for i, (label, icon, folder, method) in enumerate(MODULES):
            color = MODULE_COLORS[i % len(MODULE_COLORS)]
            self._module_button(body, f"Module {i+1}", label, icon, folder, method, color)

    def _module_button(self, parent, number, label, icon, folder, method, accent_color):
        folder_path = os.path.join(MODULES_DIR, folder)
        exists = os.path.isdir(folder_path)

        outer = tk.Frame(parent, bg=BG)
        outer.pack(fill="x", pady=3)

        # Color indicator
        tk.Frame(outer, bg=accent_color if exists else "#374151", width=4).pack(
            side="left", fill="y")

        btn_bg = CARD if exists else "#111827"
        btn_fg = TEXT if exists else "#4b5563"
        display = f"  {icon}   {number}  —  {label}"
        if not exists:
            display += "  (not found)"

        btn = tk.Button(
            outer, text=display,
            bg=btn_bg, fg=btn_fg,
            activebackground=HOVER if exists else btn_bg,
            activeforeground="white" if exists else btn_fg,
            font=("Segoe UI", 10), relief="flat", anchor="w",
            padx=14, pady=10, bd=0,
            cursor="hand2" if exists else "arrow",
            command=lambda: open_module(label, folder, method, self.root) if exists else None,
        )
        btn.pack(side="left", fill="x", expand=True)

        if exists:
            btn.bind("<Enter>", lambda e, b=btn, c=accent_color: b.config(bg=c))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=CARD))

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    LauncherApp().run()
