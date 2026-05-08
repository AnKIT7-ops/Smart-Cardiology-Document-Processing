# dashboard_widgets.py
# Reusable PyQt5 widgets for the dashboard
# Keeps dashboard_app.py cleaner - same idea as Module 3's widgets.py

from PyQt5.QtWidgets import (QWidget, QLabel, QFrame, QHBoxLayout,
                              QVBoxLayout, QTableWidget, QTableWidgetItem,
                              QHeaderView, QSizePolicy)
from PyQt5.QtCore    import Qt
from PyQt5.QtGui     import QColor, QFont

from config import (BG, CARD, CARD2, ACCENT, TEXT, SUBTEXT,
                    BORDER, RISK_COLORS)


# ── Stat Card ─────────────────────────────────────────────────────────────────

class StatCard(QFrame):
    # One of the big number summary cards at the top

    def __init__(self, title, value, subtitle, color, icon, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {CARD};
                border: 1px solid {color};
                border-radius: 8px;
                padding: 6px;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(110)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)

        # Top row: icon + title
        top = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"color: {color}; font-size: 18px;")
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {SUBTEXT}; font-size: 9px; font-weight: bold;")
        top.addWidget(icon_lbl)
        top.addWidget(title_lbl)
        top.addStretch()
        layout.addLayout(top)

        # Big number
        value_lbl = QLabel(str(value))
        value_lbl.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold;")
        layout.addWidget(value_lbl)

        # Subtitle
        sub_lbl = QLabel(subtitle)
        sub_lbl.setStyleSheet(f"color: {SUBTEXT}; font-size: 8px;")
        layout.addWidget(sub_lbl)


# ── Section Header ────────────────────────────────────────────────────────────

class SectionHeader(QWidget):

    def __init__(self, title, subtitle="", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 4)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {ACCENT}; font-size: 11px; font-weight: bold;"
        )
        layout.addWidget(title_lbl)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(f"color: {SUBTEXT}; font-size: 8px;")
            layout.addWidget(sub)

        layout.addStretch()


# ── Divider ───────────────────────────────────────────────────────────────────

class Divider(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background-color: {BORDER}; border: none;")


# ── Center Summary Strip ──────────────────────────────────────────────────────

class CenterSummaryStrip(QFrame):
    # Row of small cards showing per-center ECG counts

    def __init__(self, centers_data, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {CARD}; border-radius: 8px;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 10, 16, 10)

        label = QLabel("Center-wise ECG Count")
        label.setStyleSheet(f"color: {SUBTEXT}; font-size: 9px; font-weight: bold;")
        outer.addWidget(label)

        row = QHBoxLayout()
        row.setSpacing(8)

        for center, data in centers_data.items():
            cell = QFrame()
            cell.setStyleSheet(f"""
                QFrame {{
                    background-color: {CARD2};
                    border-radius: 6px;
                }}
            """)
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(10, 8, 10, 8)
            cell_layout.setAlignment(Qt.AlignCenter)

            count = QLabel(str(data["ecgs"]))
            count.setStyleSheet(
                f"color: {ACCENT}; font-size: 20px; font-weight: bold;"
            )
            count.setAlignment(Qt.AlignCenter)
            cell_layout.addWidget(count)

            name = QLabel(center)
            name.setStyleSheet(f"color: {SUBTEXT}; font-size: 7px;")
            name.setAlignment(Qt.AlignCenter)
            name.setWordWrap(True)
            cell_layout.addWidget(name)

            row.addWidget(cell)

        outer.addLayout(row)


# ── Recent Predictions Table ──────────────────────────────────────────────────

class RecentTable(QFrame):

    def __init__(self, rows, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {CARD}; border-radius: 8px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        headers = ["Patient ID", "Center", "Age", "Risk Level", "Probability", "Time"]
        col_widths = [90, 200, 50, 110, 100, 150]

        table = QTableWidget(len(rows), len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setFocusPolicy(Qt.NoFocus)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)

        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {CARD};
                alternate-background-color: {CARD2};
                border: none;
                color: {TEXT};
                font-size: 9px;
                gridline-color: {BORDER};
                outline: none;
            }}
            QHeaderView::section {{
                background-color: {CARD2};
                color: {ACCENT};
                font-size: 8px;
                font-weight: bold;
                padding: 6px;
                border: none;
                border-bottom: 1px solid {BORDER};
            }}
            QTableWidget::item {{
                padding: 6px 8px;
                border-bottom: 1px solid {BORDER};
            }}
            QTableWidget::item:selected {{
                background-color: #0f4c75;
                color: {TEXT};
            }}
        """)

        for col, w in enumerate(col_widths):
            table.setColumnWidth(col, w)

        table.horizontalHeader().setStretchLastSection(True)

        for row_idx, row_data in enumerate(rows):
            patient_id, center, age, risk, prob, time = row_data
            values     = [patient_id, center, str(age), risk, prob, time]
            risk_color = RISK_COLORS.get(risk, TEXT)

            for col_idx, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

                # Color the risk and probability columns
                if col_idx in (3, 4):
                    item.setForeground(QColor(risk_color))

                table.setItem(row_idx, col_idx, item)

        table.setFixedHeight(len(rows) * 36 + 36)
        layout.addWidget(table)
