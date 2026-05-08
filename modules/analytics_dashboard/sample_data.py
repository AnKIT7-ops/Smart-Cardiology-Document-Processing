# sample_data.py
# All the sample data for the dashboard
# In the real system this would come from the MySQL database
# For now everything is hardcoded to look realistic

# -- Centers in the system --
CENTERS = [
    "Mangaluru Central",
    "Udupi District",
    "Puttur PHC",
    "Bantwal CHC",
    "Sullia PHC",
    "Belthangady PHC",
]

# -- Top level summary cards --
SUMMARY = {
    "total_ecgs":        1284,
    "high_risk":          318,
    "moderate_risk":      476,
    "low_risk":           490,
    "total_patients":    1102,
    "alerts_sent":        214,
    "centers_active":       6,
    "doctors_active":      18,
}

# -- District-wise ECG count and risk breakdown --
DISTRICT_DATA = {
    "Mangaluru": {"ecgs": 412, "high": 98,  "moderate": 167, "low": 147},
    "Udupi":     {"ecgs": 287, "high": 71,  "moderate": 103, "low": 113},
    "Puttur":    {"ecgs": 198, "high": 52,  "moderate":  74, "low":  72},
    "Bantwal":   {"ecgs": 163, "high": 41,  "moderate":  58, "low":  64},
    "Sullia":    {"ecgs": 134, "high": 34,  "moderate":  48, "low":  52},
    "Belthangady":{"ecgs": 90, "high": 22,  "moderate":  26, "low":  42},
}

# -- Daily ECG trend for the last 14 days --
DAILY_TREND = {
    "days": [
        "Apr 14", "Apr 15", "Apr 16", "Apr 17", "Apr 18",
        "Apr 19", "Apr 20", "Apr 21", "Apr 22", "Apr 23",
        "Apr 24", "Apr 25", "Apr 26", "Apr 27"
    ],
    "ecgs_processed": [72, 88, 95, 64, 80, 91, 103, 77, 85, 98, 110, 92, 87, 102],
    "high_risk":      [18, 22, 24, 15, 19, 23,  26, 20, 21, 25,  28, 23, 22,  26],
}

# -- Doctor activity across centers --
DOCTOR_ACTIVITY = [
    # (name,              center,               patients, reviews, alerts_handled)
    ("Dr. Suresh Kamath",  "Mangaluru Central",   94,       88,      32),
    ("Dr. Priya Nayak",    "Mangaluru Central",   87,       81,      28),
    ("Dr. Ramesh Shetty",  "Udupi District",      76,       70,      24),
    ("Dr. Anitha Rao",     "Udupi District",      68,       63,      19),
    ("Dr. Kiran Prabhu",   "Puttur PHC",          59,       54,      17),
    ("Dr. Deepa Hegde",    "Bantwal CHC",         52,       49,      15),
    ("Dr. Vinod Bhat",     "Sullia PHC",          48,       44,      13),
    ("Dr. Manjula Pai",    "Belthangady PHC",     41,       38,      11),
]

# -- Recent predictions table (latest 8 records) --
RECENT_PREDICTIONS = [
    # (patient_id, center,               age, risk_level,  probability, timestamp)
    ("P-1284", "Mangaluru Central",  67, "HIGH",     "83.2%", "27 Apr  14:32"),
    ("P-1283", "Udupi District",     54, "MODERATE", "61.4%", "27 Apr  14:18"),
    ("P-1282", "Puttur PHC",         72, "HIGH",     "79.8%", "27 Apr  13:55"),
    ("P-1281", "Bantwal CHC",        45, "LOW",      "22.1%", "27 Apr  13:40"),
    ("P-1280", "Mangaluru Central",  58, "MODERATE", "54.7%", "27 Apr  13:27"),
    ("P-1279", "Sullia PHC",         63, "HIGH",     "88.5%", "27 Apr  13:10"),
    ("P-1278", "Belthangady PHC",    49, "LOW",      "18.3%", "27 Apr  12:58"),
    ("P-1277", "Udupi District",     70, "HIGH",     "76.9%", "27 Apr  12:45"),
]
