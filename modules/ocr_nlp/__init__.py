import tkinter as tk
from tkinter import messagebox


def _missing_deps_launch(parent):
    """Fallback launch when paddleocr/cv2 are not installed."""
    window = tk.Toplevel(parent)
    window.title("Module 1 — OCR + NLP (Dependencies Missing)")
    window.geometry("500x200")
    window.configure(bg="#f8fafc")

    tk.Label(
        window, text="⚠️  Module 1 — Dependencies Not Installed",
        font=("Segoe UI", 13, "bold"), bg="#f8fafc", fg="#b91c1c",
    ).pack(pady=(30, 10))
    tk.Label(
        window,
        text="This module requires: paddlepaddle, paddleocr, opencv-python, pymupdf\n\n"
             "Run:  python -m pip install paddlepaddle paddleocr opencv-python pymupdf",
        font=("Segoe UI", 10), bg="#f8fafc", fg="#334155",
        justify="center",
    ).pack(pady=10)
    return window


try:
    from .ui import launch  # noqa: F401
except ImportError:
    try:
        from ui import launch  # noqa: F401
    except ImportError:
        launch = _missing_deps_launch
