# Smart Cardiology Document Processing — Complete Integration Guide v2

> **Purpose**: This document is the single source of truth for integrating all modules into one unified desktop application. Send this file to your teammate — they (or their AI agent) should follow it exactly.

---

## 1. Project Overview

This system processes cardiology data across 6 health centers in the Mangaluru/Udupi district. Each module runs independently but shares data through one SQLite database (`smart_cardiology.db`). A main launcher ties all modules into a single app.

### Module Responsibilities

| Module | Name | What It Does | Status |
|--------|------|-------------|--------|
| Module 1 | OCR + NLP | Scans medical documents, extracts patient info | **Needs integration** |
| Module 2 | ECG Signal Analysis | Analyzes ECG signals, detects abnormalities | **Needs integration** |
| Module 3 | Cardiac Risk Prediction | Predicts heart disease risk using ML | ✅ Done |
| Module 5 | Report Generation | Generates formatted patient reports | **Needs integration** |
| Module 6 | Critical Alerts | Flags high-risk patients, sends notifications | **Needs integration** |
| Module 7 | Analytics Dashboard | Visualizes all data with charts and tables | ✅ Done |

---

## 2. Project File Structure

Your module folder MUST follow this naming and structure pattern:

```
Smart Cardiology Document Processing/
│
├── main_app.py                         ← MAIN LAUNCHER (opens all modules)
├── heart_disease_uci.csv               ← Dataset for Module 3
├── smart_cardiology.db                 ← Shared SQLite DB (auto-created)
├── INTEGRATION_GUIDE_V2.md             ← This file
│
├── shared/                             ← SHARED — DO NOT MODIFY
│   ├── __init__.py
│   └── database.py                     ← All DB tables, helpers, read/write functions
│
├── cardiac_risk_prediction/            ← MODULE 3 (done)
│   ├── __init__.py
│   ├── main.py
│   ├── model.py
│   ├── preprocess.py
│   ├── ui.py
│   ├── database.py                     ← Local wrapper that imports from shared/
│   └── saved_models/
│
├── dashboard-Tkinter/                  ← MODULE 7 - Tkinter version (done)
│   ├── main.py
│   ├── config.py
│   ├── data_source.py
│   ├── sample_data.py
│   ├── charts.py
│   ├── dashboard_app.py
│   └── dashboard_widgets.py
│
├── analytics_dashboard-pyQt/           ← MODULE 7 - PyQt5 version (done)
│   ├── main.py
│   ├── config.py
│   ├── sample_data.py
│   ├── charts.py
│   ├── dashboard_app.py
│   └── dashboard_widgets.py
│
├── ocr_nlp/                            ← MODULE 1 (teammate creates this)
│   ├── __init__.py
│   ├── main.py
│   ├── database.py                     ← Must follow wrapper pattern below
│   └── ui.py
│
├── ecg_analysis/                       ← MODULE 2 (teammate creates this)
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   └── ui.py
│
├── report_generation/                  ← MODULE 5 (teammate creates this)
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   └── ui.py
│
└── critical_alerts/                    ← MODULE 6 (teammate creates this)
    ├── __init__.py
    ├── main.py
    ├── database.py
    └── ui.py
```

---

## 3. Golden Rules

1. **Every module gets its own folder** at the project root.
2. **Never import another module's UI or internal files.** Modules talk only through the database.
3. **Use `shared/database.py`** for all database operations. Do NOT create your own tables.
4. **Use the same `patient_id` format** everywhere: `P-0001`, `P-0002`, etc.
5. **Use the same `center_id` values** everywhere (see Section 5).
6. **Your UI must be a Tkinter Toplevel window**, not a standalone `Tk()` root.
7. **DO NOT modify `shared/database.py`** without team approval.

---

## 4. How to Connect to the Shared Database

Every module needs a local `database.py` file that imports from `shared/database.py`. Copy this exact pattern:

### File: `your_module/database.py`

```python
import os
import sys

# Add project root to Python path so we can import shared/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import what you need from the shared database
from shared.database import (  # noqa: E402,F401
    DB_PATH,
    init_db,
    get_connection,
    now_text,
    next_patient_id,
    upsert_patient,
    center_id_for,
    center_name_for,
    normalize_risk_level,
    DEFAULT_CENTERS,
    CENTER_NAME_TO_ID,
    CENTER_ID_TO_NAME,
)
```

Then in your other files (ui.py, main.py, etc.), import from your local database.py:

```python
from database import init_db, get_connection, now_text, upsert_patient
```

---

## 5. Fixed Center IDs and Names

All modules MUST use these exact center IDs and names:

| center_id | center_name | district |
|-----------|------------|----------|
| `CEN-001` | `Mangaluru Central` | Mangaluru |
| `CEN-002` | `Udupi District` | Udupi |
| `CEN-003` | `Puttur PHC` | Puttur |
| `CEN-004` | `Bantwal CHC` | Bantwal |
| `CEN-005` | `Sullia PHC` | Sullia |
| `CEN-006` | `Belthangady PHC` | Belthangady |

**Helper functions available:**
- `center_id_for("Mangaluru Central")` → returns `"CEN-001"`
- `center_id_for("CEN-001")` → returns `"CEN-001"` (safe to call with either format)
- `center_name_for("CEN-001")` → returns `"Mangaluru Central"`

---

## 6. Patient ID Format

Format: `P-XXXX` where XXXX is zero-padded (e.g., `P-0001`, `P-0042`, `P-0100`).

**To get the next available ID:**
```python
from database import next_patient_id

pid = next_patient_id()  # Returns "P-0001", "P-0002", etc.
```

This function checks both `tbl_patients` and `tbl_ai_predictions` tables to avoid duplicates.

**To save/update a patient:**
```python
from database import upsert_patient

upsert_patient(
    patient_id="P-0001",
    patient_name="Rahul Sharma",
    age=55,
    gender="Male",
    center="CEN-001",           # accepts center_id OR center_name
    source_module="MODULE_1",   # use YOUR module number
)
```

This will INSERT a new patient or UPDATE existing fields if the patient_id already exists.

---

## 7. Database Tables — Complete Schema

The database has 7 tables. All are auto-created when `init_db()` is called.

### 7.1 `tbl_centers` (pre-populated, read-only)

```sql
CREATE TABLE tbl_centers (
    center_id   TEXT PRIMARY KEY,       -- "CEN-001"
    center_name TEXT NOT NULL,          -- "Mangaluru Central"
    district    TEXT NOT NULL,          -- "Mangaluru"
    status      TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at  TEXT NOT NULL           -- "2026-05-06 10:30:00"
);
```

### 7.2 `tbl_patients` (shared by all modules)

```sql
CREATE TABLE tbl_patients (
    patient_id    TEXT PRIMARY KEY,     -- "P-0001"
    patient_name  TEXT,                 -- "Rahul Sharma"
    age           INTEGER,             -- 55
    gender        TEXT,                -- "Male" or "Female"
    center_id     TEXT,                -- "CEN-001"
    source_module TEXT,                -- "MODULE_1", "MODULE_2", "MODULE_3"
    created_at    TEXT NOT NULL,       -- "2026-05-06 10:30:00"
    updated_at    TEXT NOT NULL        -- "2026-05-06 10:30:00"
);
```

**Who writes:** Module 1 creates patients first. Other modules update via `upsert_patient()`.

### 7.3 `tbl_reports` (Module 1 owns this)

```sql
CREATE TABLE tbl_reports (
    report_id        TEXT PRIMARY KEY,  -- "RPT-0001" (you choose format)
    upload_id        TEXT,              -- optional upload tracking ID
    patient_id       TEXT NOT NULL,     -- "P-0001" (must exist in tbl_patients)
    center_id        TEXT,              -- "CEN-001"
    document_type    TEXT,              -- "Discharge Summary", "Lab Report", etc.
    extracted_text   TEXT,              -- full OCR text output
    diagnosis_text   TEXT,              -- extracted diagnosis section
    doctor_notes     TEXT,              -- extracted doctor notes
    confidence_score REAL,             -- OCR confidence 0.0 to 1.0
    status           TEXT NOT NULL DEFAULT 'COMPLETED',
    created_at       TEXT NOT NULL      -- "2026-05-06 10:30:00"
);
```

**Status values:** `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`

**Example insert for Module 1:**
```python
from database import get_connection, init_db, now_text, upsert_patient, center_id_for

def save_report(patient_id, patient_name, age, gender, center,
                report_id, document_type, extracted_text,
                diagnosis_text, doctor_notes, confidence_score):
    init_db()

    # Step 1: Save/update the patient record
    upsert_patient(
        patient_id=patient_id,
        patient_name=patient_name,
        age=age,
        gender=gender,
        center=center,
        source_module="MODULE_1",
    )

    # Step 2: Save the report
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO tbl_reports (
                report_id, patient_id, center_id, document_type,
                extracted_text, diagnosis_text, doctor_notes,
                confidence_score, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'COMPLETED', ?)
            """,
            (
                report_id,
                patient_id,
                center_id_for(center),
                document_type,
                extracted_text,
                diagnosis_text,
                doctor_notes,
                confidence_score,
                now_text(),
            ),
        )
```

### 7.4 `tbl_ecg_data` (Module 2 owns this)

```sql
CREATE TABLE tbl_ecg_data (
    ecg_id                TEXT PRIMARY KEY,  -- "ECG-0001" (you choose format)
    patient_id            TEXT NOT NULL,      -- "P-0001"
    center_id             TEXT,               -- "CEN-001"
    heart_rate            INTEGER,            -- 72
    rhythm_type           TEXT,               -- "Normal" or "Arrhythmia"
    abnormality_detected  TEXT,               -- "No", "ST Depression", "ST Elevation", "LV Hypertrophy", "Other"
    st_change             TEXT,               -- "Normal", "ST Elevation", "ST Depression"
    confidence_score      REAL,               -- 0.0 to 1.0
    ai_remarks            TEXT,               -- free text AI analysis notes
    status                TEXT NOT NULL DEFAULT 'COMPLETED',
    created_at            TEXT NOT NULL       -- "2026-05-06 10:30:00"
);
```

**Allowed values for `rhythm_type`:** `Normal`, `Arrhythmia`
**Allowed values for `abnormality_detected`:** `No`, `ST Depression`, `ST Elevation`, `LV Hypertrophy`, `Other`
**Allowed values for `st_change`:** `Normal`, `ST Elevation`, `ST Depression`
**Status values:** `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`

**Example insert for Module 2:**
```python
from database import get_connection, init_db, now_text, upsert_patient, center_id_for

def save_ecg_result(patient_id, center, ecg_id, heart_rate, rhythm_type,
                    abnormality_detected, st_change, confidence_score, ai_remarks):
    init_db()

    # Save ECG analysis result
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO tbl_ecg_data (
                ecg_id, patient_id, center_id, heart_rate, rhythm_type,
                abnormality_detected, st_change, confidence_score,
                ai_remarks, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'COMPLETED', ?)
            """,
            (
                ecg_id,
                patient_id,
                center_id_for(center),
                heart_rate,
                rhythm_type,
                abnormality_detected,
                st_change,
                confidence_score,
                ai_remarks,
                now_text(),
            ),
        )
```

**Important:** Module 3 reads ECG data using `fetch_latest_patient_context(patient_id)`. This function returns the most recent COMPLETED ECG for a patient. Module 2 MUST set `status = 'COMPLETED'` for results to be visible.

### 7.5 `tbl_ai_predictions` (Module 3 owns this — already done)

```sql
CREATE TABLE tbl_ai_predictions (
    prediction_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id       TEXT NOT NULL,     -- "P-0001"
    center_id        TEXT NOT NULL,     -- "CEN-001"
    center_name      TEXT NOT NULL,     -- "Mangaluru Central"
    doctor_name      TEXT NOT NULL,     -- "Dr. Rao"
    age              INTEGER NOT NULL,
    gender           TEXT NOT NULL,     -- "Male" or "Female"
    bp               INTEGER NOT NULL,  -- resting blood pressure mmHg
    cholesterol      INTEGER NOT NULL,  -- serum cholesterol mg/dL
    diabetes         TEXT NOT NULL,     -- "Yes" or "No"
    smoking          TEXT NOT NULL,     -- "Yes" or "No"
    ecg_result       TEXT NOT NULL,     -- "Normal", "LV Hypertrophy", "ST-T Abnormality"
    risk_level       TEXT NOT NULL,     -- "LOW", "MODERATE", or "HIGH"
    probability      REAL NOT NULL,     -- 0.0 to 100.0
    suggested_action TEXT NOT NULL,
    followup_required TEXT NOT NULL,    -- "Yes" or "No"
    model_used       TEXT NOT NULL,     -- "Logistic Regression" or "XGBoost"
    source_module    TEXT NOT NULL DEFAULT 'MODULE_3',
    created_at       TEXT NOT NULL
);
```

**Risk levels (always uppercase in DB):** `LOW`, `MODERATE`, `HIGH`

**To read predictions (for Module 5, 6, 7):**
```python
from shared.database import fetch_predictions

rows = fetch_predictions()        # all predictions, newest first
rows = fetch_predictions(limit=8) # latest 8 only
# Each row is a dict with all columns above
```

### 7.6 `tbl_alerts` (Module 6 owns this)

```sql
CREATE TABLE tbl_alerts (
    alert_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id    TEXT NOT NULL,        -- "P-0001"
    prediction_id INTEGER,             -- links to tbl_ai_predictions
    alert_type    TEXT NOT NULL,        -- "High Risk", "Critical ECG", etc.
    message       TEXT NOT NULL,        -- human-readable alert message
    status        TEXT NOT NULL DEFAULT 'OPEN',
    created_at    TEXT NOT NULL
);
```

**Status values:** `OPEN`, `ACKNOWLEDGED`, `RESOLVED`

Module 3 already auto-creates a basic alert row when risk_level is HIGH. Module 6 should:
1. READ existing alerts from this table
2. UPDATE alert status (OPEN → ACKNOWLEDGED → RESOLVED)
3. CREATE new alerts based on ECG abnormalities or other triggers

**Example for Module 6:**
```python
from database import get_connection, init_db, now_text

def fetch_open_alerts():
    init_db()
    with get_connection() as conn:
        conn.row_factory = __import__("sqlite3").Row
        return [dict(row) for row in conn.execute(
            "SELECT * FROM tbl_alerts WHERE status = 'OPEN' ORDER BY created_at DESC"
        ).fetchall()]

def update_alert_status(alert_id, new_status):
    """new_status must be 'ACKNOWLEDGED' or 'RESOLVED'"""
    init_db()
    with get_connection() as conn:
        conn.execute(
            "UPDATE tbl_alerts SET status = ? WHERE alert_id = ?",
            (new_status, alert_id),
        )

def create_alert(patient_id, alert_type, message, prediction_id=None):
    init_db()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO tbl_alerts (patient_id, prediction_id, alert_type, message, status, created_at)
            VALUES (?, ?, ?, ?, 'OPEN', ?)
            """,
            (patient_id, prediction_id, alert_type, message, now_text()),
        )
```

### 7.7 `tbl_sync_status` (future use)

```sql
CREATE TABLE tbl_sync_status (
    local_record_id TEXT PRIMARY KEY,
    module_name     TEXT NOT NULL,
    sync_status     TEXT NOT NULL,
    device_id       TEXT,
    last_sync_time  TEXT
);
```

Reserved for multi-device sync. Ignore for now.

---

## 8. How to Build Your Module UI (Tkinter)

Every module MUST expose a `launch(parent)` function that opens a `Toplevel` window. This is how the main launcher opens your module.

### Required File: `your_module/ui.py`

```python
import tkinter as tk
from tkinter import messagebox

# Import your module's database functions
from database import init_db  # your local database.py wrapper


class YourModuleApp:
    """Your module's main UI window."""

    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("Your Module Name")
        self.window.geometry("600x500")
        self.window.configure(bg="#f8fafc")

        try:
            init_db()
        except Exception as e:
            messagebox.showwarning("DB Warning", f"Database issue: {e}")

        # Build your UI here
        self._build_header()
        self._build_content()

    def _build_header(self):
        header = tk.Frame(self.window, bg="#2563eb", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header, text="Your Module Name",
            font=("Arial", 14, "bold"), bg="#2563eb", fg="white"
        ).pack(pady=15)

    def _build_content(self):
        # Add your input fields, buttons, etc.
        pass


def launch(parent):
    """Called by the main launcher to open this module."""
    return YourModuleApp(parent)
```

### Required File: `your_module/main.py`

This allows standalone testing:

```python
import tkinter as tk
from ui import YourModuleApp


def main():
    root = tk.Tk()
    root.withdraw()  # hide the empty root
    app = YourModuleApp(root)
    app.window.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
```

### Required File: `your_module/__init__.py`

```python
from .ui import launch
```

---

## 9. Data Flow Between Modules

```
Module 1 (OCR + NLP)
    │
    ├── Writes patient info ──────► tbl_patients
    ├── Writes extracted reports ──► tbl_reports
    │
    ▼
Module 2 (ECG Analysis)
    │
    ├── Reads patient from ────────► tbl_patients
    ├── Writes ECG results ────────► tbl_ecg_data
    │
    ▼
Module 3 (Cardiac Risk Prediction)  ← ALREADY DONE
    │
    ├── Reads patient + ECG from ──► tbl_patients, tbl_ecg_data
    ├── Writes predictions ────────► tbl_ai_predictions
    ├── Auto-creates HIGH alerts ──► tbl_alerts
    │
    ▼
Module 5 (Report Generation)
    │
    ├── Reads all data from ───────► tbl_patients, tbl_reports,
    │                                 tbl_ecg_data, tbl_ai_predictions
    ├── Generates PDF/printable reports
    │
    ▼
Module 6 (Critical Alerts)
    │
    ├── Reads predictions from ────► tbl_ai_predictions
    ├── Reads/writes alerts ───────► tbl_alerts
    ├── Updates status: OPEN → ACKNOWLEDGED → RESOLVED
    │
    ▼
Module 7 (Analytics Dashboard)  ← ALREADY DONE
    │
    └── Reads everything from ─────► ALL tables (read-only)
```

---

## 10. Timestamp Format

All `created_at` and `updated_at` fields MUST use this exact format:

```
YYYY-MM-DD HH:MM:SS
```

Example: `2026-05-06 14:30:00`

Use the helper function:
```python
from database import now_text

timestamp = now_text()  # Returns "2026-05-06 14:30:00"
```

**NEVER use `datetime.now().isoformat()` or any other format.** The dashboard parses timestamps using `strptime("%Y-%m-%d %H:%M:%S")` and will break with other formats.

---

## 11. Testing Your Module

Before submitting your code, verify these checks pass:

### Checklist

```
[ ] My module folder is at the project root (e.g., ecg_analysis/)
[ ] I have __init__.py with `from .ui import launch`
[ ] I have database.py that imports from shared/database.py
[ ] I call init_db() before any database operation
[ ] I use patient_id format P-XXXX
[ ] I use center_id values CEN-001 through CEN-006
[ ] I use now_text() for all timestamps
[ ] I write to ONLY my assigned table(s)
[ ] I set status = 'COMPLETED' on finished records
[ ] My UI opens as Toplevel(parent), not Tk()
[ ] My module has a launch(parent) function
[ ] I can run standalone via `python main.py`
[ ] I inserted 5 test rows and verified them in the DB
```

### How to Verify Your Data Was Saved

Run this from the project root in a Python shell:

```python
import sqlite3

conn = sqlite3.connect("smart_cardiology.db")
conn.row_factory = sqlite3.Row

# Check your table (change table name as needed)
rows = conn.execute("SELECT * FROM tbl_ecg_data ORDER BY created_at DESC LIMIT 5").fetchall()
for row in rows:
    print(dict(row))

conn.close()
```

---

## 12. 5 Sample Rows Each Module Must Provide

Before merging, every module must insert 5 sample rows so other modules can test. Use these patient IDs:

| patient_id | patient_name | age | gender | center_id |
|-----------|-------------|-----|--------|-----------|
| P-0001 | Ramesh Kumar | 58 | Male | CEN-001 |
| P-0002 | Lakshmi Devi | 45 | Female | CEN-002 |
| P-0003 | Suresh Nayak | 62 | Male | CEN-003 |
| P-0004 | Priya Shetty | 38 | Female | CEN-004 |
| P-0005 | Mohan Rai | 70 | Male | CEN-005 |

---

## 13. Common Mistakes to Avoid

| Mistake | Why It Breaks Things |
|---------|---------------------|
| Using `risk_level = "Low"` instead of `"LOW"` | Dashboard filters by uppercase values |
| Using `datetime.now().isoformat()` | Dashboard parser expects `%Y-%m-%d %H:%M:%S` |
| Creating `root = tk.Tk()` in your UI | Causes multiple root window errors in launcher |
| Writing to a table you don't own | Other module overwrites or conflicts |
| Using center name `"Mangalore"` instead of `"Mangaluru Central"` | Center lookup returns wrong ID |
| Not calling `init_db()` before DB operations | Tables may not exist yet |
| Forgetting `status = 'COMPLETED'` | Other modules ignore non-completed records |

---

## 14. Dependencies

All teammates must install these packages:

```
pip install pandas numpy scikit-learn xgboost matplotlib
```

If using PyQt5 dashboard version, also:
```
pip install PyQt5
```

Tkinter comes built-in with Python — no install needed.

---

## 15. Questions to Confirm With Your Teammate

Send these questions to each teammate before they start coding:

```
1. Which module number are you responsible for?
2. Which table(s) will your module write to?
3. Have you created your database.py wrapper using the pattern in Section 4?
4. Does your ui.py have a launch(parent) function?
5. Are you using patient_id format P-XXXX?
6. Are you using center_id values CEN-001 to CEN-006?
7. Are you using now_text() for timestamps?
8. Can you provide 5 sample database rows?
9. Does your module run standalone with python main.py?
```
