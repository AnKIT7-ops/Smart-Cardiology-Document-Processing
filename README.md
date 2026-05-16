<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776ab?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Tkinter-GUI-blue?style=for-the-badge" alt="Tkinter">
  <img src="https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/PaddleOCR-AI-red?style=for-the-badge" alt="PaddleOCR">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
</p>

<h1 align="center">🫀 Smart Cardiology Document Processing</h1>

<p align="center">
  <b>AI-powered cardiology document processing system for the Mangaluru / Udupi District Health Network</b><br>
  <sub>Desktop application • 8 integrated modules • Shared SQLite database • Built with Python & Tkinter</sub>
</p>

---

## 📖 Overview

A comprehensive desktop application that processes ECG documents, predicts cardiac risk, generates clinical summaries, and manages patient alerts — designed to support **6 Primary Health Centers** in the Mangaluru/Udupi district.

All modules run independently but share data through one central SQLite database (`smart_cardiology.db`). No module imports another module's code directly.

---

## ✨ Features

- 📄 **AI Document Processing** — Scan medical documents using PaddleOCR + rule-based NLP extraction
- 💓 **ECG Signal Analysis** — Detect rhythm abnormalities and ST-segment changes
- 🎯 **Cardiac Risk Prediction** — Logistic Regression + XGBoost on UCI Heart Disease dataset
- 📋 **Clinical Report Summarization** — Aggregate patient data into unified reports with PDF export
- 📡 **Tele-Cardiology Decision Support** — Remote triage with diagnosis, urgency, and referral suggestions
- 🚨 **Critical Alert System** — Severity-filtered real-time alert dashboard
- 📊 **Analytics Dashboard** — Visual analytics with charts, trends, and center-wise statistics
- 🔄 **Offline Data Capture & Sync** — Offline data entry for rural areas with sync-when-online

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** (Tkinter ships built-in)
- **pip** (Python package manager)

### Installation

```bash
# Clone the repository
git clone https://github.com/AnKIT7-ops/Smart-Cardiology-Document-Processing.git
cd Smart-Cardiology-Document-Processing

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Launch the application
python main_app.py
```

> **Note:** The launcher will auto-initialize `smart_cardiology.db` on first run.

---

## 📁 Project Structure

```
Smart-Cardiology-Document-Processing/
│
├── main_app.py                          # 🚀 Main launcher (entry point)
├── requirements.txt                     # Python dependencies
├── heart_disease_uci.csv                # Training dataset (Module 3)
├── LICENSE                              # MIT License
│
├── shared/                              # Shared integration layer
│   ├── __init__.py
│   └── database.py                      # Tables, helpers, CRUD functions
│
└── modules/                             # All 8 application modules
    ├── __init__.py
    ├── ocr_nlp/                         # Module 1: AI Document Processing
    ├── ecg_analysis/                    # Module 2: ECG Signal Analysis
    ├── cardiac_risk_prediction/         # Module 3: Risk Prediction
    ├── integrated_clinical_summary/     # Module 4: Report Summarization
    ├── tele_cardiology/                 # Module 5: Tele-Cardiology DSS
    ├── unified_alert_dashboard/         # Module 6: Critical Alert System
    ├── analytics_dashboard/             # Module 7: Analytics Dashboard
    └── offline_sync/                    # Module 8: Offline Data Sync
```

---

## 🗄️ Database Architecture

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
| `tbl_patients` | All modules | Patient demographics (P-XXXX format) |
| `tbl_reports` | Module 1 | OCR-extracted document text |
| `tbl_ecg_data` | Module 2 | ECG analysis results |
| `tbl_ai_predictions` | Module 3 | Risk prediction scores |
| `tbl_integrated_summaries` | Module 4 | Generated clinical reports |
| `tbl_telecardiology_decisions` | Module 5 | Tele-cardiology decisions |
| `tbl_alerts` | Module 3 & 6 | Patient alerts with severity |
| `tbl_sync_status` | Module 8 | Offline sync tracking |

---

## 🔄 Data Flow

```
Module 1 (OCR)      → tbl_patients, tbl_reports
Module 2 (ECG)      → tbl_patients, tbl_ecg_data
Module 3 (Risk)     → reads patients + ECG → tbl_ai_predictions, tbl_alerts
Module 4 (Summary)  → reads ALL above → tbl_integrated_summaries
Module 5 (Tele)     → reads patients + ECG + predictions → tbl_telecardiology_decisions
Module 6 (Alerts)   → reads tbl_alerts (from Modules 3 & 5)
Module 7 (Dashboard)→ reads all tables for analytics
Module 8 (Sync)     → tbl_sync_status
```

---

## 🏥 Health Centers

| ID | Center | District |
|----|--------|----------|
| CEN-001 | Mangaluru Central | Mangaluru |
| CEN-002 | Udupi District | Udupi |
| CEN-003 | Puttur PHC | Puttur |
| CEN-004 | Bantwal CHC | Bantwal |
| CEN-005 | Sullia PHC | Sullia |
| CEN-006 | Belthangady PHC | Belthangady |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.10+ |
| GUI Framework | Tkinter (built-in) |
| Database | SQLite3 (file-based, zero-config) |
| ML Models | scikit-learn, XGBoost |
| OCR Engine | PaddleOCR |
| Charts | Matplotlib |
| PDF Export | ReportLab |

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/your-feature`)
3. **Commit** your changes (`git commit -m "Add your feature"`)
4. **Push** to the branch (`git push origin feature/your-feature`)
5. **Open** a Pull Request

### Module Development Rules

- Never import another module's code directly — use the shared database
- Use `shared/database.py` for all DB operations
- Patient ID format: `P-XXXX` (e.g., `P-0001`)
- Center IDs: `CEN-001` through `CEN-006`
- Your UI must use `Toplevel(parent)`, not standalone `Tk()`
- Export a `launch(parent)` function in your module's `__init__.py`

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  Developed as part of the <b>CAD Foundation's Smart Cardiology Initiative</b><br>
  <sub>Internship Program — Mangaluru / Udupi District Health Network</sub>
</p>
