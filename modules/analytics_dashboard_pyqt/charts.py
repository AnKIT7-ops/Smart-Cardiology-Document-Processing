# charts.py
# All chart drawing functions using matplotlib
# Returns Figure objects that get embedded into PyQt5 using FigureCanvasQTAgg

import numpy as np
from matplotlib.figure import Figure

from config import (CHART_BG, CHART_FG, CHART_GRID,
                    COLOR_HIGH, COLOR_MOD, COLOR_LOW, COLOR_BLUE)
from sample_data import DISTRICT_DATA, DAILY_TREND, SUMMARY, DOCTOR_ACTIVITY


def _base_figure(width, height):
    # Creates a figure with the dark background
    fig = Figure(figsize=(width, height), facecolor=CHART_BG)
    fig.subplots_adjust(left=0.12, right=0.97, top=0.88, bottom=0.22)
    return fig


def _style_axis(ax, title):
    # Applies the dark theme to any axis
    ax.set_facecolor(CHART_BG)
    ax.tick_params(colors=CHART_FG, labelsize=8)
    ax.set_title(title, color=CHART_FG, fontsize=10,
                 fontweight="bold", pad=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(CHART_GRID)
    ax.spines["bottom"].set_color(CHART_GRID)
    ax.xaxis.label.set_color(CHART_FG)
    ax.yaxis.label.set_color(CHART_FG)
    ax.grid(color=CHART_GRID, linestyle="--", linewidth=0.5, alpha=0.6)


# ── Chart 1: Risk Donut ───────────────────────────────────────────────────────

def make_risk_donut():
    fig = Figure(figsize=(3.4, 3.2), facecolor=CHART_BG)
    fig.subplots_adjust(left=0.05, right=0.95, top=0.90, bottom=0.18)
    ax = fig.add_subplot(111)
    ax.set_facecolor(CHART_BG)

    values = [SUMMARY["high_risk"], SUMMARY["moderate_risk"], SUMMARY["low_risk"]]
    colors = [COLOR_HIGH, COLOR_MOD, COLOR_LOW]
    labels = [
        f"High  ({SUMMARY['high_risk']})",
        f"Moderate  ({SUMMARY['moderate_risk']})",
        f"Low  ({SUMMARY['low_risk']})",
    ]

    wedges, _ = ax.pie(
        values,
        colors=colors,
        startangle=90,
        wedgeprops=dict(width=0.52, edgecolor=CHART_BG, linewidth=2),
    )

    # Center text
    ax.text(0,  0.10, str(SUMMARY["total_ecgs"]),
            ha="center", va="center",
            fontsize=18, fontweight="bold", color=CHART_FG)
    ax.text(0, -0.15, "Total ECGs",
            ha="center", va="center",
            fontsize=7, color=CHART_GRID)

    ax.legend(wedges, labels,
              loc="lower center",
              bbox_to_anchor=(0.5, -0.14),
              ncol=1, fontsize=7.5,
              frameon=False,
              labelcolor=CHART_FG)

    ax.set_title("Risk Distribution", color=CHART_FG,
                 fontsize=10, fontweight="bold", pad=8)
    return fig


# ── Chart 2: District-wise Grouped Bar ───────────────────────────────────────

def make_district_bar():
    fig = _base_figure(5.6, 3.2)
    ax  = fig.add_subplot(111)

    districts = list(DISTRICT_DATA.keys())
    highs     = [DISTRICT_DATA[d]["high"]     for d in districts]
    mods      = [DISTRICT_DATA[d]["moderate"] for d in districts]
    lows      = [DISTRICT_DATA[d]["low"]      for d in districts]

    x     = np.arange(len(districts))
    width = 0.25

    ax.bar(x - width, highs, width, color=COLOR_HIGH, label="High",     alpha=0.9)
    ax.bar(x,         mods,  width, color=COLOR_MOD,  label="Moderate", alpha=0.9)
    ax.bar(x + width, lows,  width, color=COLOR_LOW,  label="Low",      alpha=0.9)

    ax.set_xticks(x)
    ax.set_xticklabels(districts, rotation=15, ha="right", fontsize=7.5)
    ax.set_ylabel("Cases", color=CHART_FG, fontsize=8)
    ax.legend(fontsize=8, frameon=False, labelcolor=CHART_FG)

    _style_axis(ax, "District-wise Risk Breakdown")
    return fig


# ── Chart 3: Daily Trend Line ─────────────────────────────────────────────────

def make_daily_trend():
    fig = _base_figure(5.6, 3.2)
    ax  = fig.add_subplot(111)

    days = DAILY_TREND["days"]
    ecgs = DAILY_TREND["ecgs_processed"]
    high = DAILY_TREND["high_risk"]
    x    = np.arange(len(days))

    ax.plot(x, ecgs, color=COLOR_BLUE, linewidth=2.0,
            marker="o", markersize=4, label="ECGs Processed")
    ax.plot(x, high, color=COLOR_HIGH, linewidth=1.8,
            marker="s", markersize=4, linestyle="--", label="High Risk")
    ax.fill_between(x, ecgs, alpha=0.10, color=COLOR_BLUE)

    ax.set_xticks(x[::2])
    ax.set_xticklabels(days[::2], rotation=15, ha="right", fontsize=7)
    ax.set_ylabel("Count", color=CHART_FG, fontsize=8)
    ax.legend(fontsize=8, frameon=False, labelcolor=CHART_FG)

    _style_axis(ax, "Daily Trends  (Last 14 Days)")
    return fig


# ── Chart 4: Doctor Activity Horizontal Bar ───────────────────────────────────

def make_doctor_activity():
    fig = _base_figure(5.0, 3.2)
    ax  = fig.add_subplot(111)

    # Top 6 doctors only
    doctors  = [row[0].replace("Dr. ", "") for row in DOCTOR_ACTIVITY[:6]]
    patients = [row[2] for row in DOCTOR_ACTIVITY[:6]]
    reviews  = [row[3] for row in DOCTOR_ACTIVITY[:6]]

    y     = np.arange(len(doctors))
    width = 0.35

    ax.barh(y + width / 2, patients, width, color=COLOR_BLUE, label="Patients",     alpha=0.9)
    ax.barh(y - width / 2, reviews,  width, color=COLOR_LOW,  label="Reviews Done", alpha=0.9)

    ax.set_yticks(y)
    ax.set_yticklabels(doctors, fontsize=7.5)
    ax.set_xlabel("Count", color=CHART_FG, fontsize=8)
    ax.legend(fontsize=8, frameon=False, labelcolor=CHART_FG)

    _style_axis(ax, "Doctor Activity  (Top 6)")
    return fig
