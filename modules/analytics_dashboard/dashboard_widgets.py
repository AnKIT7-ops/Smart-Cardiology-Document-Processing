# dashboard_widgets.py
# Reusable UI pieces for the dashboard
# Same idea as widgets.py in Module 3 - keeps dashboard_app.py cleaner

import tkinter as tk
from config import (BG, CARD, CARD2, ACCENT, SUCCESS, WARNING,
                    DANGER, TEXT, SUBTEXT, BORDER, RISK_COLORS)


def make_stat_card(parent, title, value, subtitle, color, icon):
    # Makes one of the big number cards at the top of the dashboard
    card = tk.Frame(parent, bg=CARD, padx=18, pady=14,
                    highlightbackground=color,
                    highlightthickness=1)
    card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)

    top = tk.Frame(card, bg=CARD)
    top.pack(fill=tk.X)
    tk.Label(top, text=icon, font=("Segoe UI", 16),
             bg=CARD, fg=color).pack(side=tk.LEFT)
    tk.Label(top, text=title, font=("Segoe UI", 9, "bold"),
             bg=CARD, fg=SUBTEXT).pack(side=tk.LEFT, padx=8)

    tk.Label(card, text=str(value),
             font=("Segoe UI", 26, "bold"),
             bg=CARD, fg=color).pack(anchor=tk.W, pady=(4, 0))

    tk.Label(card, text=subtitle,
             font=("Segoe UI", 8),
             bg=CARD, fg=SUBTEXT).pack(anchor=tk.W)

    return card


def make_section_header(parent, title, subtitle=""):
    frame = tk.Frame(parent, bg=BG)
    frame.pack(fill=tk.X, padx=20, pady=(16, 4))

    tk.Label(frame, text=title,
             font=("Segoe UI", 11, "bold"),
             bg=BG, fg=ACCENT).pack(side=tk.LEFT)

    if subtitle:
        tk.Label(frame, text=subtitle,
                 font=("Segoe UI", 8),
                 bg=BG, fg=SUBTEXT).pack(side=tk.LEFT, padx=10)


def make_divider(parent):
    tk.Frame(parent, bg=BORDER, height=1).pack(fill=tk.X, pady=4)


def make_recent_table(parent, rows):
    # Builds the recent predictions table
    card = tk.Frame(parent, bg=CARD, padx=16, pady=12)
    card.pack(fill=tk.X, padx=20, pady=(0, 10))

    headers = ["Patient ID", "Center", "Age", "Risk Level", "Probability", "Time"]
    widths   = [90, 200, 50, 110, 100, 140]

    header_row = tk.Frame(card, bg=CARD2)
    header_row.pack(fill=tk.X, pady=(0, 4))

    for h, w in zip(headers, widths):
        tk.Label(header_row, text=h,
                 font=("Segoe UI", 8, "bold"),
                 bg=CARD2, fg=ACCENT,
                 width=w // 8,
                 anchor=tk.W).pack(side=tk.LEFT, padx=6, pady=5)

    for i, row in enumerate(rows):
        patient_id, center, age, risk, prob, time = row
        row_bg    = CARD if i % 2 == 0 else CARD2
        data_row  = tk.Frame(card, bg=row_bg)
        data_row.pack(fill=tk.X)

        risk_color = RISK_COLORS.get(risk, TEXT)
        values     = [patient_id, center, str(age), risk, prob, time]
        colors     = [TEXT, SUBTEXT, SUBTEXT, risk_color, risk_color, SUBTEXT]

        for val, col, w in zip(values, colors, widths):
            tk.Label(data_row, text=val,
                     font=("Segoe UI", 9),
                     bg=row_bg, fg=col,
                     width=w // 8,
                     anchor=tk.W).pack(side=tk.LEFT, padx=6, pady=5)

        tk.Frame(card, bg=BORDER, height=1).pack(fill=tk.X)


def make_center_summary_row(parent, centers_data):
    card = tk.Frame(parent, bg=CARD, padx=16, pady=10)
    card.pack(fill=tk.X, padx=20, pady=(0, 10))

    tk.Label(card, text="Center-wise ECG Count",
             font=("Segoe UI", 9, "bold"),
             bg=CARD, fg=SUBTEXT).pack(anchor=tk.W, pady=(0, 8))

    row = tk.Frame(card, bg=CARD)
    row.pack(fill=tk.X)

    for center, data in centers_data.items():
        cell = tk.Frame(row, bg=CARD2, padx=12, pady=8)
        cell.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        tk.Label(cell, text=str(data["ecgs"]),
                 font=("Segoe UI", 18, "bold"),
                 bg=CARD2, fg=ACCENT).pack()
        tk.Label(cell, text=center,
                 font=("Segoe UI", 7),
                 bg=CARD2, fg=SUBTEXT,
                 wraplength=90).pack()
