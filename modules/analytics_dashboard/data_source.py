import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.database import fetch_predictions, init_db  # noqa: E402
from sample_data import (  # noqa: E402
    DAILY_TREND as SAMPLE_DAILY_TREND,
    DISTRICT_DATA as SAMPLE_DISTRICT_DATA,
    DOCTOR_ACTIVITY as SAMPLE_DOCTOR_ACTIVITY,
    RECENT_PREDICTIONS as SAMPLE_RECENT_PREDICTIONS,
    SUMMARY as SAMPLE_SUMMARY,
)


CENTER_TO_DISTRICT = {
    "Mangaluru Central": "Mangaluru",
    "Udupi District": "Udupi",
    "Puttur PHC": "Puttur",
    "Bantwal CHC": "Bantwal",
    "Sullia PHC": "Sullia",
    "Belthangady PHC": "Belthangady",
}


def load_dashboard_data():
    """
    Return dashboard-ready dictionaries/lists.

    Real saved predictions are used when available. Sample data is kept as a
    fallback so Module 7 still works before Module 3 has produced records.
    """
    try:
        init_db()
        rows = fetch_predictions()
    except Exception:
        rows = []

    if not rows:
        return {
            "summary": SAMPLE_SUMMARY,
            "district_data": SAMPLE_DISTRICT_DATA,
            "daily_trend": SAMPLE_DAILY_TREND,
            "doctor_activity": SAMPLE_DOCTOR_ACTIVITY,
            "recent_predictions": SAMPLE_RECENT_PREDICTIONS,
            "using_sample_data": True,
        }

    return {
        "summary": _build_summary(rows),
        "district_data": _build_district_data(rows),
        "daily_trend": _build_daily_trend(rows),
        "doctor_activity": _build_doctor_activity(rows),
        "recent_predictions": _build_recent_predictions(rows[:8]),
        "using_sample_data": False,
    }


def _risk_level(row):
    return str(row.get("risk_level", "")).upper()


def _parse_created_at(value):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return datetime.now()


def _build_summary(rows):
    high = sum(1 for row in rows if _risk_level(row) == "HIGH")
    moderate = sum(1 for row in rows if _risk_level(row) == "MODERATE")
    low = sum(1 for row in rows if _risk_level(row) == "LOW")
    centers = {row.get("center") for row in rows if row.get("center")}
    doctors = {
        row.get("doctor_name")
        for row in rows
        if row.get("doctor_name") and row.get("doctor_name") != "Not Assigned"
    }

    return {
        "total_ecgs": len(rows),
        "high_risk": high,
        "moderate_risk": moderate,
        "low_risk": low,
        "total_patients": len({row.get("patient_id") for row in rows}),
        "alerts_sent": high,
        "centers_active": len(centers),
        "doctors_active": len(doctors),
    }


def _build_district_data(rows):
    data = {
        district: {"ecgs": 0, "high": 0, "moderate": 0, "low": 0}
        for district in CENTER_TO_DISTRICT.values()
    }

    for row in rows:
        center = row.get("center", "")
        district = CENTER_TO_DISTRICT.get(center, center or "Unknown")
        data.setdefault(district, {"ecgs": 0, "high": 0, "moderate": 0, "low": 0})
        data[district]["ecgs"] += 1

        risk = _risk_level(row)
        if risk == "HIGH":
            data[district]["high"] += 1
        elif risk == "MODERATE":
            data[district]["moderate"] += 1
        elif risk == "LOW":
            data[district]["low"] += 1

    return data


def _build_daily_trend(rows):
    today = datetime.now().date()
    days = [today - timedelta(days=offset) for offset in range(13, -1, -1)]
    day_counts = {day: {"ecgs": 0, "high": 0} for day in days}

    for row in rows:
        day = _parse_created_at(row.get("created_at")).date()
        if day not in day_counts:
            continue
        day_counts[day]["ecgs"] += 1
        if _risk_level(row) == "HIGH":
            day_counts[day]["high"] += 1

    return {
        "days": [day.strftime("%b %d") for day in days],
        "ecgs_processed": [day_counts[day]["ecgs"] for day in days],
        "high_risk": [day_counts[day]["high"] for day in days],
    }


def _build_doctor_activity(rows):
    doctors = defaultdict(lambda: {"center": "", "patients": set(), "reviews": 0, "alerts": 0})

    for row in rows:
        doctor = row.get("doctor_name") or "Not Assigned"
        doctors[doctor]["center"] = row.get("center") or "Unknown"
        doctors[doctor]["patients"].add(row.get("patient_id"))
        doctors[doctor]["reviews"] += 1
        if _risk_level(row) == "HIGH":
            doctors[doctor]["alerts"] += 1

    activity = []
    for doctor, data in doctors.items():
        activity.append(
            (
                doctor,
                data["center"],
                len(data["patients"]),
                data["reviews"],
                data["alerts"],
            )
        )

    return sorted(activity, key=lambda item: item[3], reverse=True)


def _build_recent_predictions(rows):
    recent = []
    for row in rows:
        created = _parse_created_at(row.get("created_at"))
        recent.append(
            (
                row.get("patient_id", ""),
                row.get("center", ""),
                row.get("age", ""),
                _risk_level(row),
                f"{float(row.get('probability', 0)):.1f}%",
                created.strftime("%d %b  %H:%M"),
            )
        )
    return recent
