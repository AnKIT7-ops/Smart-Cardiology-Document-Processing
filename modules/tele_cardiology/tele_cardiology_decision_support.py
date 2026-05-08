import os
import re
import sqlite3
import sys
import tkinter as tk
from tkinter import messagebox, ttk


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.database import (  # noqa: E402
    DB_PATH,
    fetch_patient_ids,
    init_db,
    next_patient_id,
    now_text,
    upsert_patient,
)


BG = "#f6f8fb"
PANEL = "#ffffff"
PRIMARY = "#1d4ed8"
TEXT = "#172033"
MUTED = "#64748b"
BORDER = "#dbe3ef"
LOW = "#15803d"
MODERATE = "#b45309"
HIGH = "#b91c1c"

GENDERS = ["Male", "Female", "Other"]
ECG_OPTIONS = [
    "Normal Sinus Rhythm",
    "Atrial Fibrillation",
    "Bradycardia",
    "Bundle Branch Block",
    "ST Depression",
    "ST Elevation",
    "Myocardial Infarction",
    "Supraventricular Tachycardia",
    "Ventricular Tachycardia",
    "Other Abnormality",
]


def init_telecardiology_db():
    """Create the shared DB plus this module's decision table."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tbl_telecardiology_decisions (
                decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                patient_name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                blood_pressure TEXT NOT NULL,
                symptoms TEXT NOT NULL,
                ecg_analysis_result TEXT NOT NULL,
                risk_score REAL NOT NULL,
                suggested_diagnosis TEXT NOT NULL,
                urgency_level TEXT NOT NULL,
                recommended_action TEXT NOT NULL,
                referral_suggestion TEXT NOT NULL,
                source_module TEXT NOT NULL DEFAULT 'TELE_CARDIOLOGY_DSS',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tele_decisions_patient_id
            ON tbl_telecardiology_decisions(patient_id)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tele_decisions_created_at
            ON tbl_telecardiology_decisions(created_at)
            """
        )


def parse_blood_pressure(text):
    """Return systolic and diastolic values from '120/80' or '120'."""
    match = re.search(r"(\d{2,3})(?:\s*/\s*(\d{2,3}))?", text.strip())
    if not match:
        return None, None
    systolic = int(match.group(1))
    diastolic = int(match.group(2)) if match.group(2) else None
    return systolic, diastolic


def parse_ai_remarks(remarks):
    """Extract diagnosis and risk text from Module 2 ECG remarks."""
    remarks = remarks or ""
    diagnosis = ""
    risk = ""

    diagnosis_match = re.search(r"Diagnosis:\s*([^|]+)", remarks, re.I)
    risk_match = re.search(r"Risk:\s*([^|]+)", remarks, re.I)
    if diagnosis_match:
        diagnosis = diagnosis_match.group(1).strip()
    if risk_match:
        risk = risk_match.group(1).strip()

    return diagnosis, risk


def risk_text_to_score(risk_text):
    risk = (risk_text or "").strip().lower()
    if risk == "critical":
        return 95
    if risk == "high":
        return 80
    if risk == "moderate":
        return 55
    if risk == "low":
        return 25
    return None


def fetch_latest_context(patient_id):
    """Read latest patient, ECG, and prediction data from smart_cardiology.db."""
    patient_id = patient_id.strip()
    if not patient_id:
        return None

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        patient = conn.execute(
            """
            SELECT patient_id, patient_name, age, gender, center_id
            FROM tbl_patients
            WHERE patient_id = ?
            """,
            (patient_id,),
        ).fetchone()
        ecg = conn.execute(
            """
            SELECT ecg_id, heart_rate, rhythm_type, abnormality_detected,
                   st_change, confidence_score, ai_remarks, created_at
            FROM tbl_ecg_data
            WHERE patient_id = ? AND status = 'COMPLETED'
            ORDER BY datetime(created_at) DESC, ecg_id DESC
            LIMIT 1
            """,
            (patient_id,),
        ).fetchone()
        prediction = conn.execute(
            """
            SELECT bp, risk_level, probability, ecg_result, created_at
            FROM tbl_ai_predictions
            WHERE patient_id = ?
            ORDER BY datetime(created_at) DESC, prediction_id DESC
            LIMIT 1
            """,
            (patient_id,),
        ).fetchone()

    return {
        "patient": dict(patient) if patient else None,
        "ecg": dict(ecg) if ecg else None,
        "prediction": dict(prediction) if prediction else None,
    }


def build_ecg_summary(ecg_row):
    if not ecg_row:
        return ""

    diagnosis, _risk = parse_ai_remarks(ecg_row.get("ai_remarks", ""))
    if diagnosis:
        return diagnosis

    parts = [
        ecg_row.get("rhythm_type"),
        ecg_row.get("abnormality_detected"),
        ecg_row.get("st_change"),
    ]
    clean = [str(part) for part in parts if part and str(part).lower() != "no"]
    return " / ".join(clean)


def make_decision(age, blood_pressure, symptoms, ecg_result, risk_score):
    systolic, diastolic = parse_blood_pressure(blood_pressure)
    symptoms_l = symptoms.lower()
    ecg_l = ecg_result.lower()

    severe_symptoms = any(
        term in symptoms_l
        for term in [
            "chest pain",
            "chest pressure",
            "syncope",
            "fainting",
            "severe breath",
            "shortness of breath",
            "sweating",
            "diaphoresis",
            "radiating pain",
        ]
    )
    moderate_symptoms = any(
        term in symptoms_l
        for term in ["palpitation", "dizziness", "fatigue", "breathless", "edema"]
    )

    emergency_ecg = any(
        term in ecg_l
        for term in [
            "ventricular tachycardia",
            "myocardial infarction",
            "st elevation",
            "stemi",
        ]
    )
    abnormal_ecg = emergency_ecg or any(
        term in ecg_l
        for term in [
            "atrial fibrillation",
            "bradycardia",
            "tachycardia",
            "block",
            "st depression",
            "hypertrophy",
            "arrhythmia",
            "abnormal",
        ]
    )

    hypertensive_crisis = (
        systolic is not None
        and (systolic >= 180 or (diastolic is not None and diastolic >= 120))
    )
    high_bp = (
        systolic is not None
        and (systolic >= 140 or (diastolic is not None and diastolic >= 90))
    )

    if emergency_ecg or hypertensive_crisis or risk_score >= 75:
        urgency = "High"
    elif severe_symptoms and risk_score >= 50:
        urgency = "High"
    elif risk_score >= 40 or abnormal_ecg or high_bp or moderate_symptoms or age >= 65:
        urgency = "Moderate"
    else:
        urgency = "Low"

    if "myocardial infarction" in ecg_l or "st elevation" in ecg_l:
        diagnosis = "Possible acute coronary syndrome or myocardial infarction"
    elif "ventricular tachycardia" in ecg_l:
        diagnosis = "High-risk ventricular arrhythmia suspected"
    elif "atrial fibrillation" in ecg_l:
        diagnosis = "Atrial fibrillation with embolic-risk assessment needed"
    elif "bradycardia" in ecg_l:
        diagnosis = "Bradyarrhythmia requiring clinical correlation"
    elif hypertensive_crisis:
        diagnosis = "Hypertensive crisis with possible cardiac strain"
    elif severe_symptoms and risk_score >= 50:
        diagnosis = "Possible ischemic cardiac presentation"
    elif abnormal_ecg:
        diagnosis = "ECG abnormality requiring cardiology review"
    elif risk_score >= 40:
        diagnosis = "Moderate cardiac risk presentation"
    else:
        diagnosis = "Low-risk cardiac presentation"

    if urgency == "High":
        action = (
            "Arrange immediate clinician review, repeat ECG/vitals, and follow "
            "local emergency cardiac protocol."
        )
        referral = "Urgent referral to emergency cardiac care or nearest cardiology center."
    elif urgency == "Moderate":
        action = (
            "Schedule priority tele-cardiology review, monitor symptoms, and "
            "consider confirmatory ECG/lab evaluation."
        )
        referral = "Refer to cardiologist or district cardiac clinic within 24-48 hours."
    else:
        action = (
            "Continue routine monitoring, risk-factor counselling, and outpatient "
            "follow-up if symptoms persist."
        )
        referral = "Primary-care follow-up; cardiology referral only if symptoms worsen."

    return {
        "suggested_diagnosis": diagnosis,
        "urgency_level": urgency,
        "recommended_action": action,
        "referral_suggestion": referral,
    }


class TeleCardiologyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Tele-Cardiology Decision Support")
        self.root.geometry("820x780")
        self.root.minsize(760, 720)
        self.root.configure(bg=BG)

        self.storage_ready = True
        try:
            init_telecardiology_db()
        except Exception as exc:
            self.storage_ready = False
            messagebox.showwarning(
                "Database Warning",
                f"The app will run, but records may not save:\n{exc}",
            )

        self.vars = {}
        self.output_vars = {}
        self.output_labels = {}
        self._build_style()
        self._build_layout()
        self._new_patient_id()
        self._load_recent_decisions()

    def _build_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL, relief="flat")
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure(
            "Panel.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 10)
        )
        style.configure(
            "Title.TLabel", background=PRIMARY, foreground="white",
            font=("Segoe UI", 17, "bold")
        )
        style.configure(
            "Subtitle.TLabel", background=PRIMARY, foreground="#dbeafe",
            font=("Segoe UI", 9)
        )
        style.configure("TButton", font=("Segoe UI", 10), padding=(10, 6))
        style.configure(
            "Primary.TButton", background=PRIMARY, foreground="white",
            font=("Segoe UI", 10, "bold")
        )
        style.map("Primary.TButton", background=[("active", "#1e40af")])
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=24)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_layout(self):
        header = tk.Frame(self.root, bg=PRIMARY, height=76)
        header.pack(fill="x")
        header.pack_propagate(False)
        ttk.Label(
            header,
            text="AI Tele-Cardiology Decision Support",
            style="Title.TLabel",
        ).pack(anchor="w", padx=24, pady=(14, 0))
        ttk.Label(
            header,
            text="Remote cardiac triage connected to smart_cardiology.db",
            style="Subtitle.TLabel",
        ).pack(anchor="w", padx=24)

        body = ttk.Frame(self.root, padding=16)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(1, weight=1)

        input_panel = self._panel(body)
        input_panel.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 10))
        output_panel = self._panel(body)
        output_panel.grid(row=0, column=1, sticky="nsew")
        history_panel = self._panel(body)
        history_panel.grid(row=1, column=1, sticky="nsew", pady=(12, 0))

        self._build_inputs(input_panel)
        self._build_outputs(output_panel)
        self._build_history(history_panel)

    def _panel(self, parent):
        frame = tk.Frame(
            parent,
            bg=PANEL,
            highlightthickness=1,
            highlightbackground=BORDER,
            padx=14,
            pady=14,
        )
        return frame

    def _build_inputs(self, parent):
        tk.Label(
            parent,
            text="Input Data",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        row = 1
        self.vars["patient_id"] = tk.StringVar()
        self._entry(parent, "Patient ID", "patient_id", row)
        ttk.Button(parent, text="Load DB", command=self._load_from_db).grid(
            row=row, column=2, padx=(8, 0), pady=5, sticky="ew"
        )
        row += 1

        self._entry(parent, "Patient Name", "patient_name", row)
        ttk.Button(parent, text="New ID", command=self._new_patient_id).grid(
            row=row, column=2, padx=(8, 0), pady=5, sticky="ew"
        )
        row += 1

        self._entry(parent, "Age", "age", row)
        row += 1

        self.vars["gender"] = tk.StringVar(value=GENDERS[0])
        self._combo(parent, "Gender", "gender", GENDERS, row)
        row += 1

        self._entry(parent, "Blood Pressure", "blood_pressure", row)
        row += 1

        tk.Label(
            parent,
            text="Symptoms",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 10),
        ).grid(row=row, column=0, sticky="nw", pady=5)
        self.symptoms_text = tk.Text(
            parent,
            height=5,
            width=38,
            wrap="word",
            relief="solid",
            bd=1,
            font=("Segoe UI", 10),
        )
        self.symptoms_text.grid(row=row, column=1, columnspan=2, sticky="ew", pady=5)
        row += 1

        self.vars["ecg_analysis_result"] = tk.StringVar(value=ECG_OPTIONS[0])
        self._combo(
            parent,
            "ECG Analysis Result",
            "ecg_analysis_result",
            ECG_OPTIONS,
            row,
        )
        row += 1

        self._entry(parent, "Risk Score", "risk_score", row)
        row += 1

        controls = tk.Frame(parent, bg=PANEL)
        controls.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(16, 0))
        ttk.Button(
            controls,
            text="Analyze and Save",
            style="Primary.TButton",
            command=self._analyze,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Clear", command=self._clear).pack(side="left")

        parent.columnconfigure(1, weight=1)

    def _entry(self, parent, label, key, row):
        tk.Label(
            parent,
            text=label,
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 10),
        ).grid(row=row, column=0, sticky="w", pady=5)
        self.vars.setdefault(key, tk.StringVar())
        entry = ttk.Entry(parent, textvariable=self.vars[key], font=("Segoe UI", 10))
        entry.grid(row=row, column=1, sticky="ew", pady=5)
        return entry

    def _combo(self, parent, label, key, values, row):
        tk.Label(
            parent,
            text=label,
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 10),
        ).grid(row=row, column=0, sticky="w", pady=5)
        combo = ttk.Combobox(
            parent,
            textvariable=self.vars[key],
            values=values,
            font=("Segoe UI", 10),
        )
        combo.grid(row=row, column=1, columnspan=2, sticky="ew", pady=5)
        return combo

    def _build_outputs(self, parent):
        tk.Label(
            parent,
            text="Decision Output",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", pady=(0, 12))

        for key, label in [
            ("suggested_diagnosis", "Suggested Diagnosis"),
            ("urgency_level", "Urgency Level"),
            ("recommended_action", "Recommended Action"),
            ("referral_suggestion", "Referral Suggestion"),
        ]:
            self.output_vars[key] = tk.StringVar(value="--")
            block = tk.Frame(parent, bg=PANEL)
            block.pack(fill="x", pady=(0, 10))
            tk.Label(
                block,
                text=label,
                bg=PANEL,
                fg=MUTED,
                font=("Segoe UI", 9, "bold"),
            ).pack(anchor="w")
            value_label = tk.Label(
                block,
                textvariable=self.output_vars[key],
                bg=PANEL,
                fg=TEXT,
                font=("Segoe UI", 10),
                wraplength=280,
                justify="left",
            )
            value_label.pack(anchor="w")
            self.output_labels[key] = value_label

        self.saved_var = tk.StringVar(value="")
        tk.Label(
            parent,
            textvariable=self.saved_var,
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
            wraplength=280,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

    def _build_history(self, parent):
        tk.Label(
            parent,
            text="Recent Decisions",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        columns = ("patient", "urgency", "risk")
        self.history = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            height=8,
        )
        self.history.heading("patient", text="Patient")
        self.history.heading("urgency", text="Urgency")
        self.history.heading("risk", text="Risk")
        self.history.column("patient", width=110, anchor="w")
        self.history.column("urgency", width=80, anchor="center")
        self.history.column("risk", width=60, anchor="center")
        self.history.pack(fill="both", expand=True)

    def _new_patient_id(self):
        if not self.storage_ready:
            self.vars.get("patient_id", tk.StringVar()).set("")
            return
        try:
            self.vars["patient_id"].set(next_patient_id())
        except Exception:
            self.vars["patient_id"].set("")

    def _is_new_patient_placeholder(self, patient_id):
        try:
            return patient_id == next_patient_id()
        except Exception:
            return False

    def _open_patient_picker(self, notice=None):
        try:
            ids = fetch_patient_ids(limit=50)
        except Exception as exc:
            messagebox.showerror("Database Error", str(exc))
            return False

        if not ids:
            messagebox.showinfo("No Patients", "No patients found in the shared database.")
            return False

        pick = tk.Toplevel(self.root)
        pick.title("Select Patient")
        pick.geometry("300x360")
        pick.configure(bg=BG)
        tk.Label(
            pick,
            text=notice or "Select an existing Patient ID:",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
            wraplength=260,
            justify="left",
        ).pack(pady=(10, 5), padx=10, anchor="w")
        listbox = tk.Listbox(pick, font=("Segoe UI", 10), height=12)
        for pid in ids:
            listbox.insert("end", pid)
        listbox.pack(padx=10, fill="both", expand=True)

        def on_select():
            selected = listbox.curselection()
            if not selected:
                return
            self.vars["patient_id"].set(listbox.get(selected[0]))
            pick.destroy()
            self._load_from_db()

        listbox.bind("<Double-1>", lambda _event: on_select())
        ttk.Button(pick, text="Load", command=on_select).pack(pady=8)
        return True

    def _load_from_db(self):
        patient_id = self.vars["patient_id"].get().strip()
        if not patient_id or self._is_new_patient_placeholder(patient_id):
            self._open_patient_picker()
            return

        try:
            context = fetch_latest_context(patient_id)
        except Exception as exc:
            messagebox.showerror("Database Error", str(exc))
            return

        if not context or not any(context.values()):
            opened = self._open_patient_picker(
                f"No records found for {patient_id}. Select an existing patient instead:"
            )
            if not opened:
                messagebox.showinfo("No Data", f"No records found for {patient_id}.")
            return

        patient = context.get("patient") or {}
        ecg = context.get("ecg") or {}
        prediction = context.get("prediction") or {}

        if patient.get("patient_name"):
            self.vars["patient_name"].set(patient["patient_name"])
        if patient.get("age") is not None:
            self.vars["age"].set(str(patient["age"]))
        if patient.get("gender"):
            self.vars["gender"].set(patient["gender"])
        if prediction.get("bp") is not None:
            self.vars["blood_pressure"].set(str(prediction["bp"]))

        ecg_summary = build_ecg_summary(ecg)
        if prediction.get("ecg_result"):
            ecg_summary = prediction["ecg_result"]
        if ecg_summary:
            self.vars["ecg_analysis_result"].set(ecg_summary)

        risk_score = None
        if prediction.get("probability") is not None:
            risk_score = float(prediction["probability"])
        else:
            _diagnosis, risk_text = parse_ai_remarks(ecg.get("ai_remarks", ""))
            risk_score = risk_text_to_score(risk_text)
        if risk_score is not None:
            self.vars["risk_score"].set(f"{risk_score:.0f}")

        self.saved_var.set(f"Loaded latest DB context for {patient_id}.")

    def _validate_inputs(self):
        patient_name = self.vars["patient_name"].get().strip()
        age_text = self.vars["age"].get().strip()
        bp_text = self.vars["blood_pressure"].get().strip()
        symptoms = self.symptoms_text.get("1.0", "end").strip()
        ecg_result = self.vars["ecg_analysis_result"].get().strip()
        risk_text = self.vars["risk_score"].get().strip()

        if not all([patient_name, age_text, bp_text, symptoms, ecg_result, risk_text]):
            raise ValueError("Please fill all required input fields.")

        try:
            age = int(age_text)
            risk_score = float(risk_text)
        except ValueError as exc:
            raise ValueError("Age and Risk Score must be numeric.") from exc

        if age < 1 or age > 120:
            raise ValueError("Age must be between 1 and 120.")
        if risk_score < 0 or risk_score > 100:
            raise ValueError("Risk Score must be between 0 and 100.")

        systolic, diastolic = parse_blood_pressure(bp_text)
        if systolic is None:
            raise ValueError("Blood Pressure must be like 120/80 or 120.")
        if systolic < 50 or systolic > 260:
            raise ValueError("Systolic Blood Pressure must be between 50 and 260.")
        if diastolic is not None and (diastolic < 30 or diastolic > 160):
            raise ValueError("Diastolic Blood Pressure must be between 30 and 160.")

        return {
            "patient_id": self.vars["patient_id"].get().strip() or next_patient_id(),
            "patient_name": patient_name,
            "age": age,
            "gender": self.vars["gender"].get().strip(),
            "blood_pressure": bp_text,
            "symptoms": symptoms,
            "ecg_analysis_result": ecg_result,
            "risk_score": risk_score,
        }

    def _analyze(self):
        try:
            data = self._validate_inputs()
        except ValueError as exc:
            messagebox.showwarning("Invalid Input", str(exc))
            return

        decision = make_decision(
            age=data["age"],
            blood_pressure=data["blood_pressure"],
            symptoms=data["symptoms"],
            ecg_result=data["ecg_analysis_result"],
            risk_score=data["risk_score"],
        )

        for key, value in decision.items():
            self.output_vars[key].set(value)
        self._set_urgency_color(decision["urgency_level"])

        if self.storage_ready:
            try:
                decision_id = self._save_decision(data, decision)
                self.saved_var.set(
                    f"Saved decision #{decision_id} for {data['patient_id']}."
                )
                self._load_recent_decisions()
            except Exception as exc:
                self.saved_var.set("Decision shown, but not saved.")
                messagebox.showwarning("Database Warning", str(exc))
        else:
            self.saved_var.set("Decision shown, but database is unavailable.")

    def _set_urgency_color(self, urgency):
        color = {"Low": LOW, "Moderate": MODERATE, "High": HIGH}.get(urgency, TEXT)
        self.output_labels["urgency_level"].configure(
            fg=color,
            font=("Segoe UI", 10, "bold"),
        )

    def _save_decision(self, data, decision):
        timestamp = now_text()
        upsert_patient(
            patient_id=data["patient_id"],
            age=data["age"],
            gender=data["gender"],
            center="CEN-001",
            patient_name=data["patient_name"],
            source_module="TELE_CARDIOLOGY_DSS",
        )

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute(
                """
                INSERT INTO tbl_telecardiology_decisions (
                    patient_id, patient_name, age, gender, blood_pressure,
                    symptoms, ecg_analysis_result, risk_score,
                    suggested_diagnosis, urgency_level, recommended_action,
                    referral_suggestion, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["patient_id"],
                    data["patient_name"],
                    data["age"],
                    data["gender"],
                    data["blood_pressure"],
                    data["symptoms"],
                    data["ecg_analysis_result"],
                    data["risk_score"],
                    decision["suggested_diagnosis"],
                    decision["urgency_level"],
                    decision["recommended_action"],
                    decision["referral_suggestion"],
                    timestamp,
                ),
            )
            decision_id = cursor.lastrowid
            if decision["urgency_level"] == "High":
                conn.execute(
                    """
                    INSERT INTO tbl_alerts (
                        patient_id, prediction_id, alert_type, message,
                        status, created_at
                    )
                    VALUES (?, NULL, 'Tele-Cardiology High Urgency', ?, 'OPEN', ?)
                    """,
                    (
                        data["patient_id"],
                        "High urgency tele-cardiology decision requires review.",
                        timestamp,
                    ),
                )
        return decision_id

    def _load_recent_decisions(self):
        for item in self.history.get_children():
            self.history.delete(item)
        if not self.storage_ready:
            return

        try:
            with sqlite3.connect(DB_PATH) as conn:
                rows = conn.execute(
                    """
                    SELECT patient_id, patient_name, urgency_level, risk_score
                    FROM tbl_telecardiology_decisions
                    ORDER BY datetime(created_at) DESC, decision_id DESC
                    LIMIT 10
                    """
                ).fetchall()
        except Exception:
            return

        for patient_id, name, urgency, risk in rows:
            patient = name or patient_id
            self.history.insert("", "end", values=(patient, urgency, f"{risk:.0f}"))

    def _clear(self):
        self._new_patient_id()
        for key in [
            "patient_name",
            "age",
            "blood_pressure",
            "risk_score",
        ]:
            self.vars[key].set("")
        self.vars["gender"].set(GENDERS[0])
        self.vars["ecg_analysis_result"].set(ECG_OPTIONS[0])
        self.symptoms_text.delete("1.0", "end")

        for var in self.output_vars.values():
            var.set("--")
        self.output_labels["urgency_level"].configure(
            fg=TEXT,
            font=("Segoe UI", 10),
        )
        self.saved_var.set("")


def launch(parent):
    """Called by the main launcher to open Module 5 as a Toplevel window."""
    window = tk.Toplevel(parent)
    return TeleCardiologyApp(window)


if __name__ == "__main__":
    root = tk.Tk()
    app = TeleCardiologyApp(root)
    root.mainloop()
