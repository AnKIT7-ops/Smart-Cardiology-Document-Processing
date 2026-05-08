# ============================================================
# MODULE 3 - CARDIAC RISK PREDICTION
# File: ui.py
# Purpose: Tkinter GUI for patient data input and risk display
# ============================================================
#
# INTEGRATION:
#   - "Load Patient" button reads patient + ECG data from Modules 1 & 2
#   - ECG Result dropdown auto-fills from Module 2's tbl_ecg_data
#   - High-risk predictions create alerts for Module 6
# ============================================================

import os
import sys
import tkinter as tk
from tkinter import messagebox
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from model import CardiacRiskModel
from database import init_db, next_patient_id, save_prediction
from preprocess import prepare_input
from shared.database import (
    fetch_latest_patient_context,
    fetch_patient_ids,
    get_connection,
    now_text,
)


# ======================== COLOR PALETTE ========================
BG = "#f8fafc"         # light background
CARD_BG = "#ffffff"    # card background
PRIMARY = "#2563eb"    # blue
DANGER = "#dc2626"     # red
WARNING = "#f59e0b"    # amber
SUCCESS = "#16a34a"    # green
TEXT = "#1e293b"       # dark text
SUBTEXT = "#64748b"    # gray text
BORDER = "#e2e8f0"     # border gray

CENTER_OPTIONS = [
    "Mangaluru Central",
    "Udupi District",
    "Puttur PHC",
    "Bantwal CHC",
    "Sullia PHC",
    "Belthangady PHC",
]


# ======================== APPLICATION CLASS ========================

class CardiacRiskApp:
    """Tkinter GUI application for cardiac risk prediction."""

    def __init__(self, root):
        self.root = root
        self.root.title("Cardiac Risk Prediction")
        self.root.geometry("600x860")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        # --- Load or initialize model ---
        self.model = CardiacRiskModel()
        self._try_load_models()
        self._try_init_storage()

        # --- Build the UI ---
        self._build_header()
        self._build_input_section()
        self._build_controls()
        self._build_results_section()
        self._build_footer()

    # ---- MODEL LOADING ----

    def _try_load_models(self):
        """Attempt to load saved models; if none exist, train fresh."""
        if self.model.models_exist_on_disk():
            self.model.load_models()
        else:
            print("[ui] No saved models found. Training now...")
            self.model.train()

    def _try_init_storage(self):
        """Create the local prediction database used by the dashboard."""
        self.storage_ready = True
        try:
            init_db()
        except Exception as e:
            self.storage_ready = False
            messagebox.showwarning(
                "Storage Warning",
                f"Predictions will be shown, but not saved:\n{e}"
            )

    # ---- HEADER ----

    def _build_header(self):
        header = tk.Frame(self.root, bg=PRIMARY, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header, text="❤  Cardiac Risk Prediction",
            font=("Arial", 16, "bold"), bg=PRIMARY, fg="white"
        ).pack(pady=(15, 0))
        tk.Label(
            header, text="Enter patient details to predict heart disease risk",
            font=("Arial", 9), bg=PRIMARY, fg="#bfdbfe"
        ).pack()

    # ---- INPUT FIELDS ----

    def _build_input_section(self):
        # Card-style frame
        card = tk.Frame(self.root, bg=CARD_BG, bd=1, relief="solid",
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(padx=20, pady=(15, 5), fill="x")

        tk.Label(card, text="Patient Information", font=("Arial", 11, "bold"),
                 bg=CARD_BG, fg=TEXT).grid(row=0, column=0, columnspan=2,
                                           padx=10, pady=(10, 5), sticky="w")

        self.entries = {}
        row = 1

        # Patient ID + Load Patient button
        self.entries["patient_id"] = self._add_entry(card, "Patient ID:", row)
        self._set_next_patient_id()
        tk.Button(
            card, text="Load Patient", font=("Arial", 9),
            bg="#0ea5e9", fg="white", padx=8, pady=2,
            cursor="hand2", relief="flat",
            command=self._load_patient_from_db,
        ).grid(row=row, column=2, padx=(4, 10), pady=4, sticky="w")
        row += 1

        # Center
        self.entries["center"] = self._add_dropdown(
            card, "Center:", row, CENTER_OPTIONS)
        row += 1

        # Doctor name
        self.entries["doctor_name"] = self._add_entry(card, "Doctor Name:", row)
        row += 1

        # Age
        self.entries["age"] = self._add_entry(card, "Age:", row)
        row += 1

        # Gender
        self.entries["gender"] = self._add_dropdown(
            card, "Gender:", row, ["Male", "Female"])
        row += 1

        # Blood Pressure
        self.entries["bp"] = self._add_entry(card, "Blood Pressure (mmHg):", row)
        row += 1

        # Cholesterol
        self.entries["chol"] = self._add_entry(card, "Cholesterol (mg/dL):", row)
        row += 1

        # Diabetes
        self.entries["diabetes"] = self._add_dropdown(
            card, "Diabetes:", row, ["No", "Yes"])
        row += 1

        # Smoking
        self.entries["smoking"] = self._add_dropdown(
            card, "Smoking:", row, ["No", "Yes"])
        row += 1

        # ECG Result (simulates Module 2 output)
        self.entries["ecg"] = self._add_dropdown(
            card, "ECG Result:", row,
            ["Normal", "LV Hypertrophy", "ST-T Abnormality"])
        row += 1



        # Padding at bottom of card
        tk.Label(card, text="", bg=CARD_BG).grid(row=row, column=0, pady=2)

    def _add_entry(self, parent, label, row):
        tk.Label(parent, text=label, font=("Arial", 10), bg=CARD_BG,
                 fg=TEXT, anchor="w").grid(row=row, column=0, padx=10,
                                           pady=4, sticky="w")
        entry = tk.Entry(parent, font=("Arial", 10), width=22,
                         relief="solid", bd=1)
        entry.grid(row=row, column=1, padx=10, pady=4, sticky="w")
        return entry

    def _add_dropdown(self, parent, label, row, options):
        tk.Label(parent, text=label, font=("Arial", 10), bg=CARD_BG,
                 fg=TEXT, anchor="w").grid(row=row, column=0, padx=10,
                                           pady=4, sticky="w")
        var = tk.StringVar(value=options[0])
        menu = tk.OptionMenu(parent, var, *options)
        menu.config(font=("Arial", 10), width=18, relief="solid", bd=1)
        menu.grid(row=row, column=1, padx=10, pady=4, sticky="w")
        return var

    # ---- BUTTONS ----

    def _build_controls(self):
        btn_frame = tk.Frame(self.root, bg=BG)
        btn_frame.pack(pady=8)

        tk.Button(
            btn_frame, text="Predict Risk", font=("Arial", 12, "bold"),
            bg=PRIMARY, fg="white", padx=20, pady=5,
            activebackground="#1d4ed8", cursor="hand2",
            command=self._predict
        ).pack(side="left", padx=5)



        tk.Button(
            btn_frame, text="Clear", font=("Arial", 10),
            bg="#6b7280", fg="white", padx=12, pady=5,
            activebackground="#4b5563", cursor="hand2",
            command=self._clear
        ).pack(side="left", padx=5)

    # ---- RESULTS SECTION ----

    def _build_results_section(self):
        card = tk.Frame(self.root, bg=CARD_BG, bd=1, relief="solid",
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(padx=20, pady=5, fill="x")

        tk.Label(card, text="Prediction Results", font=("Arial", 11, "bold"),
                 bg=CARD_BG, fg=TEXT).pack(anchor="w", padx=10, pady=(10, 5))

        self.risk_label = tk.Label(
            card, text="Risk Level:  —", font=("Arial", 12, "bold"),
            bg=CARD_BG, fg=TEXT)
        self.risk_label.pack(anchor="w", padx=10, pady=2)

        self.prob_label = tk.Label(
            card, text="Probability:  —", font=("Arial", 10),
            bg=CARD_BG, fg=TEXT)
        self.prob_label.pack(anchor="w", padx=10, pady=2)

        self.action_label = tk.Label(
            card, text="Suggested Action:  —", font=("Arial", 10),
            bg=CARD_BG, fg=TEXT, wraplength=520, justify="left")
        self.action_label.pack(anchor="w", padx=10, pady=2)

        self.followup_label = tk.Label(
            card, text="Follow-up Required:  —", font=("Arial", 10),
            bg=CARD_BG, fg=TEXT)
        self.followup_label.pack(anchor="w", padx=10, pady=2)

        self.saved_label = tk.Label(
            card, text="Saved Record:  --", font=("Arial", 10),
            bg=CARD_BG, fg=SUBTEXT)
        self.saved_label.pack(anchor="w", padx=10, pady=(2, 10))



    # ---- FOOTER ----

    def _build_footer(self):
        tk.Label(
            self.root,
            text="Smart Cardiology Document Processing",
            font=("Arial", 8), bg=BG, fg=SUBTEXT
        ).pack(side="bottom", pady=5)

    # ======================== ACTIONS ========================

    def _predict(self):
        """Validate inputs, run prediction, and display results."""
        age_txt = self.entries["age"].get().strip()
        bp_txt = self.entries["bp"].get().strip()
        chol_txt = self.entries["chol"].get().strip()

        if not age_txt or not bp_txt or not chol_txt:
            messagebox.showwarning(
                "Missing Input",
                "Please fill in Age, Blood Pressure, and Cholesterol."
            )
            return

        try:
            age = int(age_txt)
            bp = int(bp_txt)
            chol = int(chol_txt)
        except ValueError:
            messagebox.showerror(
                "Invalid Input",
                "Age, Blood Pressure, and Cholesterol must be whole numbers."
            )
            return

        # Basic range checks
        if age < 1 or age > 120:
            messagebox.showerror("Invalid Age", "Age must be between 1 and 120.")
            return
        if bp < 50 or bp > 250:
            messagebox.showerror("Invalid BP", "Blood Pressure must be 50–250 mmHg.")
            return
        if chol < 50 or chol > 600:
            messagebox.showerror("Invalid Cholesterol", "Cholesterol must be 50–600 mg/dL.")
            return

        gender = self.entries["gender"].get()
        diabetes = self.entries["diabetes"].get()
        smoking = self.entries["smoking"].get()
        ecg = self.entries["ecg"].get()
        patient_id = self.entries["patient_id"].get().strip()
        center = self.entries["center"].get()
        doctor_name = self.entries["doctor_name"].get().strip() or "Not Assigned"
        model_choice = "Logistic Regression"

        # Build feature array
        features = prepare_input(age, gender, bp, chol, diabetes, smoking, ecg)

        try:
            result = self.model.predict(features, model_choice)
        except RuntimeError as e:
            messagebox.showerror("Model Error", str(e))
            return

        # Update UI
        self.risk_label.config(
            text=f"Risk Level:  {result['risk_level']}",
            fg=result["risk_color"]
        )
        self.prob_label.config(
            text=f"Probability:  {result['probability']:.1f}%"
        )
        self.action_label.config(
            text=f"Suggested Action:  {result['action']}"
        )
        self.followup_label.config(
            text=f"Follow-up Required:  {result['followup']}"
        )

        saved_patient_id = self._save_prediction_record(
            patient_id=patient_id,
            center=center,
            doctor_name=doctor_name,
            age=age,
            gender=gender,
            bp=bp,
            chol=chol,
            diabetes=diabetes,
            smoking=smoking,
            ecg=ecg,
            result=result,
            model_choice=model_choice,
        )
        if saved_patient_id:
            self.saved_label.config(
                text=f"Saved Record:  {saved_patient_id}",
                fg=SUCCESS
            )
            # Create alert for Module 6 if high risk
            self._create_alert_if_high_risk(saved_patient_id, result)
            self._set_next_patient_id()


    def _save_prediction_record(self, patient_id, center, doctor_name, age, gender,
                                bp, chol, diabetes, smoking, ecg, result,
                                model_choice):
        """Persist one successful prediction for dashboard analytics."""
        if not self.storage_ready:
            self.saved_label.config(text="Saved Record:  Storage unavailable", fg=DANGER)
            return None

        try:
            return save_prediction({
                "patient_id": patient_id,
                "center": center,
                "doctor_name": doctor_name,
                "age": age,
                "gender": gender,
                "bp": bp,
                "cholesterol": chol,
                "diabetes": diabetes,
                "smoking": smoking,
                "ecg_result": ecg,
                "risk_level": result["risk_level"],
                "probability": result["probability"],
                "action": result["action"],
                "followup": result["followup"],
                "model_used": model_choice,
            })
        except Exception as e:
            self.saved_label.config(text="Saved Record:  Not saved", fg=DANGER)
            messagebox.showwarning(
                "Storage Warning",
                f"Prediction was shown, but could not be saved:\n{e}"
            )
            return None


    def _set_next_patient_id(self):
        if "patient_id" not in self.entries:
            return
        self.entries["patient_id"].delete(0, "end")
        if not getattr(self, "storage_ready", False):
            return
        try:
            self.entries["patient_id"].insert(0, next_patient_id())
        except Exception:
            self.storage_ready = False

    # ---- LOAD FROM PREVIOUS MODULES ----

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
            messagebox.showinfo(
                "No Patients",
                "No patients found in the shared database.\n\nUse Module 1 or 2 first to register a patient.",
            )
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
            font=("Arial", 10, "bold"),
            wraplength=260,
            justify="left",
        ).pack(pady=(10, 5), padx=10, anchor="w")
        listbox = tk.Listbox(pick, font=("Arial", 10), height=12)
        for pid in ids:
            listbox.insert("end", pid)
        listbox.pack(padx=10, fill="both", expand=True)

        def on_select():
            sel = listbox.curselection()
            if not sel:
                return
            self.entries["patient_id"].delete(0, "end")
            self.entries["patient_id"].insert(0, listbox.get(sel[0]))
            pick.destroy()
            self._load_patient_from_db()

        listbox.bind("<Double-1>", lambda _event: on_select())
        tk.Button(
            pick,
            text="Load",
            bg=PRIMARY,
            fg="white",
            font=("Arial", 10, "bold"),
            command=on_select,
        ).pack(pady=8)
        return True

    def _load_patient_from_db(self):
        """Load patient data + latest ECG result from Modules 1 & 2."""
        patient_id = self.entries["patient_id"].get().strip()
        if not patient_id or self._is_new_patient_placeholder(patient_id):
            self._open_patient_picker()
            return

        try:
            ctx = fetch_latest_patient_context(patient_id)
        except Exception as exc:
            messagebox.showerror("Database Error", str(exc))
            return

        if not ctx or not any(ctx.values()):
            opened = self._open_patient_picker(
                f"No data found for {patient_id}. Select an existing patient instead:"
            )
            if not opened:
                messagebox.showinfo("No Data", f"No data found for {patient_id}.\n\nRun Module 1 or 2 first.")
            return

        patient = ctx.get("patient") or {}
        ecg = ctx.get("ecg") or {}

        # Auto-fill patient demographics
        if patient.get("age"):
            self.entries["age"].delete(0, "end")
            self.entries["age"].insert(0, str(patient["age"]))
        if patient.get("gender"):
            self.entries["gender"].set(patient["gender"])
        if patient.get("center"):
            center_name = patient["center"]
            if center_name in CENTER_OPTIONS:
                self.entries["center"].set(center_name)

        # Auto-fill ECG result from Module 2
        if ecg:
            ecg_mapping = self._map_ecg_to_dropdown(ecg)
            self.entries["ecg"].set(ecg_mapping)
            self.saved_label.config(
                text=f"Loaded patient + ECG data for {patient_id}",
                fg="#0ea5e9"
            )
        else:
            self.saved_label.config(
                text=f"Loaded patient {patient_id} (no ECG data yet — run Module 2)",
                fg=WARNING
            )

    def _map_ecg_to_dropdown(self, ecg_data):
        """Map Module 2 ECG results to Module 3 dropdown options."""
        abnormality = (ecg_data.get("abnormality_detected") or "").strip()
        st_change = (ecg_data.get("st_change") or "").strip()

        if abnormality == "LV Hypertrophy":
            return "LV Hypertrophy"
        if abnormality in ("ST Depression", "ST Elevation") or st_change in ("ST Depression", "ST Elevation"):
            return "ST-T Abnormality"
        if abnormality not in ("", "No", "Normal"):
            return "ST-T Abnormality"  # Other abnormalities
        return "Normal"

    # ---- ALERT GENERATION ----

    def _create_alert_if_high_risk(self, patient_id, result):
        """Create an alert in tbl_alerts for Module 6 when risk is High."""
        if result.get("risk_level") != "High":
            return
        try:
            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO tbl_alerts (
                        patient_id, prediction_id, alert_type, message,
                        status, created_at
                    )
                    VALUES (?, NULL, 'High Risk Prediction', ?, 'OPEN', ?)
                    """,
                    (
                        patient_id,
                        f"Module 3: {result['risk_level']} risk ({result['probability']:.0f}%) — {result['action']}",
                        now_text(),
                    ),
                )
        except Exception:
            pass  # Don't fail the prediction if alert creation fails

    def _clear(self):
        """Reset all input fields and result labels."""
        self._set_next_patient_id()
        self.entries["center"].set(CENTER_OPTIONS[0])
        self.entries["doctor_name"].delete(0, "end")
        self.entries["age"].delete(0, "end")
        self.entries["bp"].delete(0, "end")
        self.entries["chol"].delete(0, "end")
        self.entries["gender"].set("Male")
        self.entries["diabetes"].set("No")
        self.entries["smoking"].set("No")
        self.entries["ecg"].set("Normal")

        self.risk_label.config(text="Risk Level:  —", fg=TEXT)
        self.prob_label.config(text="Probability:  —")
        self.action_label.config(text="Suggested Action:  —")
        self.followup_label.config(text="Follow-up Required:  —")
        self.saved_label.config(text="Saved Record:  --", fg=SUBTEXT)


def launch(parent):
    """Called by the main launcher to open Module 3 as a Toplevel window."""
    window = tk.Toplevel(parent)
    return CardiacRiskApp(window)


# ======================== STANDALONE LAUNCH ========================
if __name__ == "__main__":
    root = tk.Tk()
    app = CardiacRiskApp(root)
    root.mainloop()
