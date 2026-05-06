# config.py
# Colors and constants - same palette as Module 3 so both modules match

# -- App colors (used in stylesheets) --
BG      = "#0d0d1a"
CARD    = "#1a1a2e"
CARD2   = "#16213e"
ACCENT  = "#00c8ff"
SUCCESS = "#00e676"
WARNING = "#ffab40"
DANGER  = "#ff5252"
TEXT    = "#e8eaf6"
SUBTEXT = "#9e9e9e"
BORDER  = "#2a2a4a"

# -- Chart colors (for matplotlib) --
CHART_BG   = "#1a1a2e"
CHART_FG   = "#e8eaf6"
CHART_GRID = "#2a2a4a"
COLOR_HIGH = "#ff5252"
COLOR_MOD  = "#ffab40"
COLOR_LOW  = "#00e676"
COLOR_BLUE = "#00c8ff"

# -- Risk color lookup --
RISK_COLORS = {
    "HIGH":     "#ff5252",
    "MODERATE": "#ffab40",
    "LOW":      "#00e676",
}

# -- Window --
WINDOW_WIDTH  = 1280
WINDOW_HEIGHT = 860


# -- Global stylesheet applied to the whole window --
APP_STYLESHEET = f"""
    QMainWindow, QWidget {{
        background-color: {BG};
        color: {TEXT};
        font-family: 'Segoe UI';
    }}
    QScrollArea {{
        border: none;
        background-color: {BG};
    }}
    QScrollBar:vertical {{
        background: {BG};
        width: 8px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {ACCENT};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QLabel {{
        background: transparent;
    }}
"""
