# dashboard_app.py
# Main dashboard window for Module 7 - built with PyQt5
# Assembles charts, widgets and data into one scrollable window

from PyQt5.QtWidgets import (QMainWindow, QWidget, QLabel, QFrame,
                              QScrollArea, QVBoxLayout, QHBoxLayout,
                              QSizePolicy)
from PyQt5.QtCore    import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from config          import (BG, CARD, CARD2, ACCENT, SUCCESS, WARNING,
                              DANGER, SUBTEXT, BORDER,
                              WINDOW_WIDTH, WINDOW_HEIGHT, APP_STYLESHEET)
from sample_data     import (SUMMARY, DISTRICT_DATA, RECENT_PREDICTIONS)
from charts          import (make_risk_donut, make_district_bar,
                              make_daily_trend, make_doctor_activity)
from dashboard_widgets import (StatCard, SectionHeader, Divider,
                                CenterSummaryStrip, RecentTable)


class AnalyticsDashboard(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analytics Dashboard · CAD Foundation · Module 7")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setStyleSheet(APP_STYLESHEET)

        # Scrollable area wraps everything
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Main content widget goes inside the scroll area
        content = QWidget()
        content.setStyleSheet(f"background-color: {BG};")
        self.main_layout = QVBoxLayout(content)
        self.main_layout.setContentsMargins(20, 0, 20, 30)
        self.main_layout.setSpacing(6)

        scroll_area.setWidget(content)
        self.setCentralWidget(scroll_area)

        # Build all sections
        self._build_header()
        self._build_stat_cards()
        self._build_center_summary()
        self._build_charts_row()
        self._build_bottom_charts()
        self._build_recent_predictions()
        self._build_disclaimer()


    # -------------------------------------------------------------------------
    # Header
    # -------------------------------------------------------------------------

    def _build_header(self):
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {CARD};
                border-bottom: 2px solid {ACCENT};
            }}
        """)
        header.setFixedHeight(72)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)

        # Left: title + subtitle
        left = QVBoxLayout()
        left.setSpacing(2)

        title = QLabel("📊  Analytics Dashboard")
        title.setStyleSheet(
            f"color: {ACCENT}; font-size: 20px; font-weight: bold;"
        )
        subtitle = QLabel(
            "CAD Foundation  ·  Smart Cardiology Decision Support System  ·  Module 7"
        )
        subtitle.setStyleSheet(f"color: {SUBTEXT}; font-size: 9px;")

        left.addWidget(title)
        left.addWidget(subtitle)
        layout.addLayout(left)
        layout.addStretch()

        # Right: last updated + status
        right = QVBoxLayout()
        right.setSpacing(2)
        right.setAlignment(Qt.AlignRight)

        updated_label = QLabel("Last Updated")
        updated_label.setStyleSheet(f"color: {SUBTEXT}; font-size: 8px;")
        updated_label.setAlignment(Qt.AlignRight)

        time_label = QLabel("27 Apr 2026  14:32")
        time_label.setStyleSheet(
            f"color: {ACCENT}; font-size: 10px; font-weight: bold;"
        )
        time_label.setAlignment(Qt.AlignRight)

        status_label = QLabel(f"●  {SUMMARY['centers_active']} Centers Active")
        status_label.setStyleSheet(f"color: {SUCCESS}; font-size: 8px;")
        status_label.setAlignment(Qt.AlignRight)

        right.addWidget(updated_label)
        right.addWidget(time_label)
        right.addWidget(status_label)
        layout.addLayout(right)

        # Put the header outside the scroll margin
        self.main_layout.addWidget(header)


    # -------------------------------------------------------------------------
    # Row 1: Stat cards
    # -------------------------------------------------------------------------

    def _build_stat_cards(self):
        self.main_layout.addWidget(
            SectionHeader("📋  System Overview", "All centers combined")
        )

        row = QHBoxLayout()
        row.setSpacing(8)

        cards = [
            ("Total ECGs",     SUMMARY["total_ecgs"],      "Processed across all centers", ACCENT,   "🫀"),
            ("High Risk",      SUMMARY["high_risk"],        "Require urgent attention",     DANGER,   "🔴"),
            ("Moderate Risk",  SUMMARY["moderate_risk"],    "Monitor closely",              WARNING,  "🟡"),
            ("Low Risk",       SUMMARY["low_risk"],         "Routine follow-up",            SUCCESS,  "🟢"),
            ("Alerts Sent",    SUMMARY["alerts_sent"],      "Critical notifications",       "#c084fc","🔔"),
            ("Doctors Active", SUMMARY["doctors_active"],
             f"Across {SUMMARY['centers_active']} centers",                                 "#60a5fa","👨‍⚕️"),
        ]

        for title, value, subtitle, color, icon in cards:
            row.addWidget(StatCard(title, value, subtitle, color, icon))

        container = QWidget()
        container.setLayout(row)
        self.main_layout.addWidget(container)


    # -------------------------------------------------------------------------
    # Row 2: Center summary strip
    # -------------------------------------------------------------------------

    def _build_center_summary(self):
        self.main_layout.addWidget(SectionHeader("🏥  Center-wise Overview"))
        self.main_layout.addWidget(CenterSummaryStrip(DISTRICT_DATA))


    # -------------------------------------------------------------------------
    # Helper: wraps a matplotlib Figure inside a dark QFrame card
    # -------------------------------------------------------------------------

    def _chart_card(self, fig):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {CARD};
                border-radius: 8px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 8, 8, 8)

        canvas = FigureCanvas(fig)
        canvas.setStyleSheet("background-color: transparent;")
        card_layout.addWidget(canvas)

        return card


    # -------------------------------------------------------------------------
    # Row 3: Donut + District bar
    # -------------------------------------------------------------------------

    def _build_charts_row(self):
        self.main_layout.addWidget(SectionHeader("📈  Risk Analysis"))

        row = QHBoxLayout()
        row.setSpacing(10)

        # Donut gets a fixed width, bar stretches
        donut_card = self._chart_card(make_risk_donut())
        donut_card.setFixedWidth(340)
        row.addWidget(donut_card)

        bar_card = self._chart_card(make_district_bar())
        bar_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        row.addWidget(bar_card)

        container = QWidget()
        container.setLayout(row)
        self.main_layout.addWidget(container)


    # -------------------------------------------------------------------------
    # Row 4: Daily trend + Doctor activity
    # -------------------------------------------------------------------------

    def _build_bottom_charts(self):
        self.main_layout.addWidget(
            SectionHeader("📅  Daily Trends  &  👨‍⚕️  Doctor Activity")
        )

        row = QHBoxLayout()
        row.setSpacing(10)

        trend_card = self._chart_card(make_daily_trend())
        trend_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        row.addWidget(trend_card)

        doc_card = self._chart_card(make_doctor_activity())
        doc_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        row.addWidget(doc_card)

        container = QWidget()
        container.setLayout(row)
        self.main_layout.addWidget(container)


    # -------------------------------------------------------------------------
    # Row 5: Recent predictions table
    # -------------------------------------------------------------------------

    def _build_recent_predictions(self):
        self.main_layout.addWidget(
            SectionHeader("🕐  Recent Predictions",
                          "Latest 8 records across all centers")
        )
        self.main_layout.addWidget(RecentTable(RECENT_PREDICTIONS))


    # -------------------------------------------------------------------------
    # Disclaimer at the bottom
    # -------------------------------------------------------------------------

    def _build_disclaimer(self):
        disclaimer = QLabel(
            "⚠  Data shown is for demonstration purposes. "
            "In production this dashboard reads live from the database."
        )
        disclaimer.setStyleSheet(
            f"color: {SUBTEXT}; font-size: 8px; font-style: italic;"
        )
        disclaimer.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(disclaimer)
