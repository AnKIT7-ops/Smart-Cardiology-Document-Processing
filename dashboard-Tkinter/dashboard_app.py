# dashboard_app.py
# Main dashboard window for Module 7 - Analytics Dashboard
# Pulls charts from charts.py, widgets from dashboard_widgets.py
# and live/sample data from data_source.py

import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from config import (BG, CARD, CARD2, ACCENT, SUCCESS, WARNING,
                    DANGER, SUBTEXT, WINDOW_WIDTH, WINDOW_HEIGHT)
from data_source import load_dashboard_data
from charts import (make_risk_donut, make_district_bar,
                    make_daily_trend, make_doctor_activity)
from dashboard_widgets import (make_stat_card, make_section_header,
                                make_divider, make_recent_table,
                                make_center_summary_row)


class AnalyticsDashboard:

    def __init__(self, root):
        self.root = root
        self.root.title("Analytics Dashboard · CAD Foundation · Module 7")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)
        self._load_data()

        self._apply_styles()
        self._build_header()
        self._build_scrollable_area()
        self._build_stat_cards()
        self._build_center_summary()
        self._build_charts_row()
        self._build_bottom_charts()
        self._build_recent_predictions()


    def _load_data(self):
        data = load_dashboard_data()
        self.summary = data["summary"]
        self.district_data = data["district_data"]
        self.daily_trend = data["daily_trend"]
        self.doctor_activity = data["doctor_activity"]
        self.recent_predictions = data["recent_predictions"]
        self.using_sample_data = data["using_sample_data"]


    # -------------------------------------------------------------------------
    # Style setup
    # -------------------------------------------------------------------------

    def _apply_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TScrollbar",
                        background=CARD,
                        troughcolor=BG,
                        arrowcolor=ACCENT)


    # -------------------------------------------------------------------------
    # Header
    # -------------------------------------------------------------------------

    def _build_header(self):
        header = tk.Frame(self.root, bg=CARD, pady=14)
        header.pack(fill=tk.X)

        left = tk.Frame(header, bg=CARD)
        left.pack(side=tk.LEFT, padx=20)

        tk.Label(left, text="📊  Analytics Dashboard",
                 font=("Segoe UI", 18, "bold"),
                 bg=CARD, fg=ACCENT).pack(anchor=tk.W)

        tk.Label(left,
                 text="CAD Foundation  ·  Smart Cardiology Decision Support System  ·  Module 7",
                 font=("Segoe UI", 9),
                 bg=CARD, fg=SUBTEXT).pack(anchor=tk.W)

        # Right side: last updated info
        right = tk.Frame(header, bg=CARD)
        right.pack(side=tk.RIGHT, padx=20)

        tk.Label(right, text="Last Updated",
                 font=("Segoe UI", 8),
                 bg=CARD, fg=SUBTEXT).pack(anchor=tk.E)
        tk.Label(right, text="27 Apr 2026  14:32",
                 font=("Segoe UI", 10, "bold"),
                 bg=CARD, fg=ACCENT).pack(anchor=tk.E)
        data_mode = "Demo Data" if self.using_sample_data else "Live DB"
        tk.Label(right, text=f"● {self.summary['centers_active']} Centers Active  ·  {data_mode}",
                 font=("Segoe UI", 8),
                 bg=CARD, fg="#00e676").pack(anchor=tk.E)

        tk.Frame(self.root, bg=ACCENT, height=2).pack(fill=tk.X)


    # -------------------------------------------------------------------------
    # Scrollable canvas
    # -------------------------------------------------------------------------

    def _build_scrollable_area(self):
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        scrollbar   = ttk.Scrollbar(outer, orient="vertical",
                                    command=self.canvas.yview)

        self.sf = tk.Frame(self.canvas, bg=BG)
        self.sf.bind("<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")))

        self.canvas.create_window((0, 0), window=self.sf, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.bind_all("<MouseWheel>",
            lambda e: self.canvas.yview_scroll(
                -1 * (e.delta // 120), "units"))


    # -------------------------------------------------------------------------
    # Row 1: Summary stat cards
    # -------------------------------------------------------------------------

    def _build_stat_cards(self):
        make_section_header(self.sf, "📋  System Overview",
                            "All centers combined")

        row = tk.Frame(self.sf, bg=BG)
        row.pack(fill=tk.X, padx=14, pady=(4, 10))

        make_stat_card(row, "Total ECGs",    self.summary["total_ecgs"],
                       "Processed across all centers", ACCENT,  "🫀")
        make_stat_card(row, "High Risk",     self.summary["high_risk"],
                       "Require urgent attention",      DANGER,  "🔴")
        make_stat_card(row, "Moderate Risk", self.summary["moderate_risk"],
                       "Monitor closely",               WARNING, "🟡")
        make_stat_card(row, "Low Risk",      self.summary["low_risk"],
                       "Routine follow-up",             SUCCESS, "🟢")
        make_stat_card(row, "Alerts Sent",   self.summary["alerts_sent"],
                       "Critical notifications",        "#c084fc","🔔")
        make_stat_card(row, "Doctors Active",self.summary["doctors_active"],
                       f"Across {self.summary['centers_active']} centers", "#60a5fa","👨‍⚕️")


    # -------------------------------------------------------------------------
    # Row 2: Center-wise ECG count strip
    # -------------------------------------------------------------------------

    def _build_center_summary(self):
        make_section_header(self.sf, "🏥  Center-wise Overview")
        make_center_summary_row(self.sf, self.district_data)


    # -------------------------------------------------------------------------
    # Row 3: Donut + District bar chart side by side
    # -------------------------------------------------------------------------

    def _build_charts_row(self):
        make_section_header(self.sf, "📈  Risk Analysis")

        row = tk.Frame(self.sf, bg=BG)
        row.pack(fill=tk.X, padx=20, pady=(4, 0))

        # Left: donut chart
        left_card = tk.Frame(row, bg=CARD, padx=10, pady=10)
        left_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 6))

        donut_fig    = make_risk_donut(self.summary)
        donut_canvas = FigureCanvasTkAgg(donut_fig, master=left_card)
        donut_canvas.draw()
        donut_canvas.get_tk_widget().pack()

        # Right: district bar chart
        right_card = tk.Frame(row, bg=CARD, padx=10, pady=10)
        right_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        bar_fig    = make_district_bar(self.district_data)
        bar_canvas = FigureCanvasTkAgg(bar_fig, master=right_card)
        bar_canvas.draw()
        bar_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


    # -------------------------------------------------------------------------
    # Row 4: Daily trends + Doctor activity side by side
    # -------------------------------------------------------------------------

    def _build_bottom_charts(self):
        make_section_header(self.sf, "📅  Daily Trends  &  👨‍⚕️  Doctor Activity")

        row = tk.Frame(self.sf, bg=BG)
        row.pack(fill=tk.X, padx=20, pady=(4, 0))

        # Left: daily trend
        left_card = tk.Frame(row, bg=CARD, padx=10, pady=10)
        left_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        trend_fig    = make_daily_trend(self.daily_trend)
        trend_canvas = FigureCanvasTkAgg(trend_fig, master=left_card)
        trend_canvas.draw()
        trend_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Right: doctor activity
        right_card = tk.Frame(row, bg=CARD, padx=10, pady=10)
        right_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))

        doc_fig    = make_doctor_activity(self.doctor_activity)
        doc_canvas = FigureCanvasTkAgg(doc_fig, master=right_card)
        doc_canvas.draw()
        doc_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


    # -------------------------------------------------------------------------
    # Row 5: Recent predictions table
    # -------------------------------------------------------------------------

    def _build_recent_predictions(self):
        make_section_header(self.sf, "🕐  Recent Predictions",
                            "Latest 8 records across all centers")
        make_recent_table(self.sf, self.recent_predictions)

        # Small disclaimer at the bottom
        source = "sample data" if self.using_sample_data else "the shared database"
        tk.Label(self.sf,
                 text=f"⚠  Data source: {source}. "
                      "Module 3 writes predictions that Module 7 reads here.",
                 font=("Segoe UI", 8, "italic"),
                 bg=BG, fg=SUBTEXT).pack(pady=(4, 20))
