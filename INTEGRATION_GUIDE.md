# Smart Cardiology Module Integration Guide

This project should integrate modules through the shared database, not by importing
each other's Tkinter screens or internal Python files.

Shared database:

```text
smart_cardiology.db
```

Shared database code:

```text
shared/database.py
```

## Golden Rule

Every module should write its final output into the agreed table. Other modules
should read from those tables using `patient_id`, `center_id`, and timestamps.

```text
Module 1 writes OCR/report data
Module 2 writes ECG analysis data
Module 3 writes risk prediction data
Module 6 writes alert data
Module 7 reads all tables for analytics
```

## Table Ownership

| Module | Owner Writes To | Main Consumer |
| --- | --- | --- |
| Module 1: OCR + NLP | `tbl_patients`, `tbl_reports` | Module 3, Module 5, Dashboard |
| Module 2: ECG Signal Analysis | `tbl_ecg_data` | Module 3, Module 5, Dashboard |
| Module 3: Cardiac Risk Prediction | `tbl_ai_predictions` | Module 5, Module 6, Dashboard |
| Module 6: Critical Alerts | `tbl_alerts` | Dashboard |
| Module 7: Analytics Dashboard | Reads tables only | Doctors/Admin |

## Common IDs

Use the same `patient_id` across all modules.

Examples:

```text
P-0001
P-0002
P-0003
```

Use the same center IDs:

```text
CEN-001 = Mangaluru Central
CEN-002 = Udupi District
CEN-003 = Puttur PHC
CEN-004 = Bantwal CHC
CEN-005 = Sullia PHC
CEN-006 = Belthangady PHC
```

## What Module 1 Must Save

Module 1 should save patient details into `tbl_patients`.

Required fields:

```text
patient_id
patient_name
age
gender
center_id
source_module = MODULE_1
created_at
updated_at
```

Module 1 should save extracted report data into `tbl_reports`.

Required fields:

```text
report_id
upload_id
patient_id
center_id
document_type
extracted_text
diagnosis_text
doctor_notes
confidence_score
status
created_at
```

Expected `status` values:

```text
PENDING
PROCESSING
COMPLETED
FAILED
```

## What Module 2 Must Save

Module 2 should save ECG analysis output into `tbl_ecg_data`.

Required fields:

```text
ecg_id
patient_id
center_id
heart_rate
rhythm_type
abnormality_detected
st_change
confidence_score
ai_remarks
status
created_at
```

Recommended values:

```text
rhythm_type = Normal / Arrhythmia
abnormality_detected = No / ST Depression / ST Elevation / LV Hypertrophy / Other
st_change = Normal / ST Elevation / ST Depression
```

## What Module 3 Already Does

Module 3 saves every successful prediction into `tbl_ai_predictions`.

Saved fields:

```text
patient_id
center_id
center_name
doctor_name
age
gender
bp
cholesterol
diabetes
smoking
ecg_result
risk_level
probability
suggested_action
followup_required
model_used
source_module = MODULE_3
created_at
```

Risk levels are saved as:

```text
LOW
MODERATE
HIGH
```

For high-risk predictions, Module 3 also creates a basic row in `tbl_alerts`.

## What Module 7 Already Does

Module 7 reads saved predictions from the shared database and builds:

```text
Total ECGs
High/Moderate/Low risk counts
District-wise counts
Daily trends
Doctor activity
Recent predictions
```

If the database has no predictions yet, Module 7 falls back to sample data so the
dashboard still opens for demos.

## What You Should Ask Teammates

Ask each teammate to confirm these points before merging:

```text
1. Which module are you responsible for?
2. Which table will your module write to?
3. What exact fields will your module save?
4. Will you use the same patient_id format, like P-0001?
5. Will you use the same center_id values, like CEN-001?
6. What status values will your module write?
7. Can you provide 5 sample database rows from your module?
8. Can your module run independently and save output without opening my module?
```

## Final Integration Workflow

1. Each module runs independently.
2. Each module saves output to its assigned shared table.
3. Module 3 reads patient and ECG data when available.
4. Module 3 saves risk prediction output.
5. Module 6 reads high-risk predictions and updates alerts.
6. Module 7 reads all final tables and shows analytics.

No module should depend on another module's UI.
