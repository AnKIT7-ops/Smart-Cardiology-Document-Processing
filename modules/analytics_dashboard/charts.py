# charts.py
# Functions to draw each chart using matplotlib
# Each function returns a Figure object that gets embedded in the Tkinter window

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.figure import Figure

from config import (CHART_BG, CHART_FG, CHART_GRID,
                    COLOR_HIGH, COLOR_MOD, COLOR_LOW, COLOR_BLUE, COLOR_BAR)
from sample_data import DISTRICT_DATA, DAILY_TREND, SUMMARY


def _base_figure(width, height):
    # Every chart starts with this - sets the dark background
    fig = Figure(figsize=(width, height), facecolor=CHART_BG)
    return fig


def _style_axis(ax, title):
    # Applies the dark theme to an axis and sets the title
    ax.set_facecolor(CHART_BG)
    ax.tick_params(colors=CHART_FG, labelsize=8)
    ax.set_title(title, color=CHART_FG, fontsize=10, fontweight="bold", pad=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(CHART_GRID)
    ax.spines["bottom"].set_color(CHART_GRID)
    ax.xaxis.label.set_color(CHART_FG)
    ax.yaxis.label.set_color(CHART_FG)
    ax.grid(color=CHART_GRID, linestyle="--", linewidth=0.5, alpha=0.7)


# ── Chart 1: Risk Donut Chart ─────────────────────────────────────────────────

def make_risk_donut(summary=None):
    summary = summary or SUMMARY
    fig = _base_figure(3.2, 3.0)
    ax  = fig.add_subplot(111)
    ax.set_facecolor(CHART_BG)

    values = [
        summary["high_risk"],
        summary["moderate_risk"],
        summary["low_risk"],
    ]
    colors = [COLOR_HIGH, COLOR_MOD, COLOR_LOW]
    labels = [
        f"High  ({summary['high_risk']})",
        f"Moderate  ({summary['moderate_risk']})",
        f"Low  ({summary['low_risk']})",
    ]

    wedges, _ = ax.pie(
        values,
        colors=colors,
        startangle=90,
        wedgeprops=dict(width=0.5, edgecolor=CHART_BG, linewidth=2),
    )

    # Center text showing total
    ax.text(0, 0.08, str(summary["total_ecgs"]),
            ha="center", va="center",
            fontsize=18, fontweight="bold", color=CHART_FG)
    ax.text(0, -0.18, "Total ECGs",
            ha="center", va="center",
            fontsize=7, color="#9e9e9e")

    # Legend
    legend = ax.legend(wedges, labels,
                       loc="lower center",
                       bbox_to_anchor=(0.5, -0.12),
                       ncol=1,
                       fontsize=7.5,
                       frameon=False,
                       labelcolor=CHART_FG)

    ax.set_title("Risk Distribution", color=CHART_FG,
                 fontsize=10, fontweight="bold", pad=8)
    fig.tight_layout()
    return fig


# ── Chart 2: District-wise Bar Chart ─────────────────────────────────────────

def make_district_bar(district_data=None):
    district_data = district_data or DISTRICT_DATA
    fig = _base_figure(5.5, 3.0)
    ax  = fig.add_subplot(111)

    districts = list(district_data.keys())
    highs     = [district_data[d]["high"]     for d in districts]
    mods      = [district_data[d]["moderate"] for d in districts]
    lows      = [district_data[d]["low"]      for d in districts]

    x     = np.arange(len(districts))
    width = 0.25

    ax.bar(x - width, highs, width, color=COLOR_HIGH, label="High",     alpha=0.9)
    ax.bar(x,         mods,  width, color=COLOR_MOD,  label="Moderate", alpha=0.9)
    ax.bar(x + width, lows,  width, color=COLOR_LOW,  label="Low",      alpha=0.9)

    ax.set_xticks(x)
    ax.set_xticklabels(districts, rotation=15, ha="right", fontsize=7.5)
    ax.set_ylabel("Cases", color=CHART_FG, fontsize=8)

    legend = ax.legend(fontsize=8, frameon=False, labelcolor=CHART_FG)

    _style_axis(ax, "District-wise Risk Breakdown")
    fig.tight_layout()
    return fig


# ── Chart 3: Daily Trend Line Chart ──────────────────────────────────────────

def make_daily_trend(daily_trend=None):
    daily_trend = daily_trend or DAILY_TREND
    fig = _base_figure(5.5, 3.0)
    ax  = fig.add_subplot(111)

    days = daily_trend["days"]
    ecgs = daily_trend["ecgs_processed"]
    high = daily_trend["high_risk"]

    x = np.arange(len(days))

    # ECGs processed line
    ax.plot(x, ecgs, color=COLOR_BLUE, linewidth=2.0,
            marker="o", markersize=4, label="ECGs Processed")

    # High risk line
    ax.plot(x, high, color=COLOR_HIGH, linewidth=1.8,
            marker="s", markersize=4, linestyle="--", label="High Risk")

    # Shade under the ECG line
    ax.fill_between(x, ecgs, alpha=0.1, color=COLOR_BLUE)

    ax.set_xticks(x[::2])  # every other day to avoid crowding
    ax.set_xticklabels(days[::2], rotation=15, ha="right", fontsize=7)
    ax.set_ylabel("Count", color=CHART_FG, fontsize=8)

    legend = ax.legend(fontsize=8, frameon=False, labelcolor=CHART_FG)

    _style_axis(ax, "Daily Trends (Last 14 Days)")
    fig.tight_layout()
    return fig


# ── Chart 4: Doctor Activity Horizontal Bar ───────────────────────────────────

def make_doctor_activity(doctor_activity=None):
    fig = _base_figure(4.8, 3.0)
    ax  = fig.add_subplot(111)

    from sample_data import DOCTOR_ACTIVITY
    doctor_activity = doctor_activity or DOCTOR_ACTIVITY

    # Just top 6 doctors
    doctors  = [row[0].replace("Dr. ", "") for row in doctor_activity[:6]]
    patients = [row[2] for row in doctor_activity[:6]]
    reviews  = [row[3] for row in doctor_activity[:6]]

    y     = np.arange(len(doctors))
    width = 0.35

    ax.barh(y + width/2, patients, width, color=COLOR_BLUE,  label="Patients",     alpha=0.9)
    ax.barh(y - width/2, reviews,  width, color=COLOR_LOW,   label="Reviews Done", alpha=0.9)

    ax.set_yticks(y)
    ax.set_yticklabels(doctors, fontsize=7.5)
    ax.set_xlabel("Count", color=CHART_FG, fontsize=8)

    legend = ax.legend(fontsize=8, frameon=False, labelcolor=CHART_FG)

    _style_axis(ax, "Doctor Activity (Top 6)")
    fig.tight_layout()
    return fig
