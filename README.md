# 🫀 Smart Cardiology Document Processing

**AI-powered cardiology document processing system for the Mangaluru/Udupi District Health Network.**

A desktop application built with Python and Tkinter that processes ECG documents, predicts cardiac risk, generates clinical summaries, and manages patient alerts — all connected through a single shared SQLite database.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Modules](#modules)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Database Architecture](#database-architecture)
- [Running Individual Modules](#running-individual-modules)
- [For Developers / Teammates](#for-developers--teammates)
- [Dependencies](#dependencies)
- [Tech Stack](#tech-stack)

---

## Overview

This system is designed to support **6 Primary Health Centers** in the Mangaluru/Udupi district. It processes cardiology data across 8 specialized modules, each handling a different aspect of cardiac care — from document scanning to risk prediction to alert management.

**Key Design Principle:** All modules run independently but share data through one central SQLite database (`smart_cardiology.db`). No module imports another module's code directly.

---

## Modules

| # | Module | Folder | Description |
|---|--------|--------|-------------|
| 1 | **AI Document Processing** | `ocr_nlp/` | Scans medical documents using PaddleOCR, extracts patient info via NLP |
| 2 | **ECG Signal Analysis AI** | `ecg_analysis/` | Analyzes ECG signals, detects rhythm abnormalities and ST changes |
| 3 | **Cardiac Risk Prediction** | `cardiac_risk_prediction/` | Predicts heart disease risk using Logistic Regression + XGBoost |
| 4 | **Report Summarization AI** | `integrated_clinical_summary/` | Aggregates all patient data into unified clinical reports + PDF export |
| 5 | **Tele-Cardiology Decision Support** | `Decision Support/` | Remote cardiac triage with diagnosis, urgency level, and referral suggestions |
| 6 | **Critical Alert System** | `unified_alert_dashboard/` | Monitors high-risk patients with severity-filtered alert dashboard |
| 7 | **Analytics Dashboard** | `dashboard-Tkinter/` | Visual analytics with charts, trends, and center-wise statistics |
| 8 | **Offline Data Capture & Sync** | `offline_sync/` | Supports rural areas with offline data entry and sync-when-online |

---

## Quick Start

### Prerequisites

- **Python 3.10+** (Tkinter comes built-in)
- **pip** (Python package manager)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/YOUR-ORG/Smart-Cardiology-Document-Processing.git
cd Smart-Cardiology-Document-Processing

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the application
python main_app.py
```

The launcher will:
- Initialize the shared database (`smart_cardiology.db`) automatically
- Show buttons for all 8 modules
- Open each module in its own window

### Module 1 (OCR) — Extra Setup

Module 1 requires heavy OCR dependencies (~1 GB). Install only if needed:

```bash
pip install paddlepaddle paddleocr opencv-python PyMuPDF
```

---

## Project Structure

```
Smart Cardiology Document Processing/
│
├── main_app.py                    ← 🚀 MAIN LAUNCHER (run this)
├── requirements.txt               ← Python dependencies
├── smart_cardiology.db            ← Shared SQLite database (auto-created)
├── heart_disease_uci.csv          ← Training dataset for Module 3
├── INTEGRATION_GUIDE_V2.md        ← Full technical integration guide
├── README.md                      ← This file
│
├── shared/                        ← Shared database layer
│   ├── __init__.py
│   └── database.py                ← All tables, helpers, read/write functions
│
├── ocr_nlp/                       ← Module 1
├── ecg_analysis/                  ← Module 2
├── cardiac_risk_prediction/       ← Module 3
├── integrated_clinical_summary/   ← Module 4
├── Decision Support/              ← Module 5
├── unified_alert_dashboard/       ← Module 6
├── dashboard-Tkinter/             ← Module 7
└── offline_sync/                  ← Module 8
```

---

## Database Architecture

All modules communicate through **one SQLite database** with 9 tables:

```
┌─────────────────────┐     ┌──────────────────────┐
│   tbl_centers (6)   │     │   tbl_patients       │
│   Pre-populated     │◄────│   All modules write   │
└─────────────────────┘     └──────────┬───────────┘
                                       │
                    ┌──────────────────┬┼──────────────────┐
                    ▼                  ▼│                  ▼
            ┌──────────────┐  ┌────────┴───────┐  ┌──────────────┐
            │ tbl_reports  │  │ tbl_ecg_data   │  │tbl_ai_predict│
            │ Module 1     │  │ Module 2       │  │ Module 3     │
            └──────────────┘  └────────────────┘  └──────┬───────┘
                    │                  │                   │
                    ▼                  ▼                   ▼
            ┌─────────────────────────────────────────────────────┐
            │  tbl_integrated_summaries  (Module 4 — reads all)  │
            └─────────────────────────────────────────────────────┘
                                       │
                    ┌──────────────────┬┴──────────────────┐
                    ▼                  ▼                   ▼
            ┌──────────────┐  ┌────────────────┐  ┌──────────────┐
            │ tbl_alerts   │  │tbl_telecardio  │  │tbl_sync_stat │
            │ Module 6     │  │ Module 5       │  │ Module 8     │
            └──────────────┘  └────────────────┘  └──────────────┘
```

| Table | Owner | Purpose |
|-------|-------|---------|
| `tbl_centers` | Pre-populated | 6 health centers (CEN-001 to CEN-006) |
| `tbl_patients` | All modules | Patient demographics (P-0001 format) |
| `tbl_reports` | Module 1 | OCR-extracted document text |
| `tbl_ecg_data` | Module 2 | ECG analysis results |
| `tbl_ai_predictions` | Module 3 | Risk prediction scores |
| `tbl_integrated_summaries` | Module 4 | Generated clinical reports |
| `tbl_telecardiology_decisions` | Module 5 | Tele-cardiology decisions |
| `tbl_alerts` | Module 3 & 6 | Patient alerts with severity |
| `tbl_sync_status` | Module 8 | Offline sync tracking |

---

## Running Individual Modules

Each module can also run standalone for testing:

```bash
# Module 1 — OCR + NLP
cd ocr_nlp && python main.py

# Module 2 — ECG Analysis
cd ecg_analysis && python main.py

# Module 3 — Cardiac Risk Prediction
cd cardiac_risk_prediction && python main.py

# Module 4 — Report Summarization
cd integrated_clinical_summary && python main.py

# Module 5 — Tele-Cardiology
cd "Decision Support" && python tele_cardiology_decision_support.py

# Module 6 — Alert Dashboard
cd unified_alert_dashboard && python main.py

# Module 7 — Analytics Dashboard
cd dashboard-Tkinter && python main.py

# Module 8 — Offline Sync
cd offline_sync && python ui.py
```

---

## For Developers / Teammates

### Integration Rules

1. **Never import another module's code directly.** Use the shared database.
2. **Use `shared/database.py`** for all DB operations — don't create your own tables.
3. **Patient ID format:** `P-XXXX` (e.g., `P-0001`)
4. **Center IDs:** `CEN-001` through `CEN-006`
5. **Timestamps:** Always use `now_text()` → `"2026-05-06 14:30:00"`
6. **Your UI must use `Toplevel(parent)`**, not standalone `Tk()`
7. **Export a `launch(parent)` function** in your module's `ui.py`

### Adding a New Module

1. Create a folder at the project root (e.g., `my_module/`)
2. Add these files:
   - `__init__.py` → `from .ui import launch`
   - `database.py` → Import from `shared/database.py` (see Integration Guide)
   - `ui.py` → Tkinter UI with `launch(parent)` function
   - `main.py` → Standalone test entry point
3. Register your module in `main_app.py`'s `MODULES` list
4. Read `INTEGRATION_GUIDE_V2.md` for the complete specification

### Verifying Your Data

```python
import sqlite3

conn = sqlite3.connect("smart_cardiology.db")
conn.row_factory = sqlite3.Row

# Check any table
rows = conn.execute("SELECT * FROM tbl_patients LIMIT 5").fetchall()
for row in rows:
    print(dict(row))

conn.close()
```

---

## Dependencies

### Required (all modules)

```
numpy, pandas, matplotlib, scikit-learn, xgboost, reportlab
```

### Optional (Module 1 only)

```
paddlepaddle, paddleocr, opencv-python, PyMuPDF
```

Install everything:

```bash
pip install -r requirements.txt
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| GUI Framework | Tkinter (built-in) |
| Database | SQLite3 (file-based, zero-config) |
| ML Models | scikit-learn, XGBoost |
| OCR Engine | PaddleOCR |
| Charts | Matplotlib |
| PDF Export | ReportLab |

---

## Health Centers

| ID | Center | District |
|----|--------|----------|
| CEN-001 | Mangaluru Central | Mangaluru |
| CEN-002 | Udupi District | Udupi |
| CEN-003 | Puttur PHC | Puttur |
| CEN-004 | Bantwal CHC | Bantwal |
| CEN-005 | Sullia PHC | Sullia |
| CEN-006 | Belthangady PHC | Belthangady |

---

## License

This project is developed as part of an internship program for the CAD Foundation's Smart Cardiology initiative.
