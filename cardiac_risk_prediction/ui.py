# ============================================================
# MODULE 3 - CARDIAC RISK PREDICTION
# File: ui.py
# Purpose: Tkinter GUI for patient data input and risk display
# ============================================================
#
# FUTURE INTEGRATION NOTE:
# -----------------------------------------------------------------
# The "ECG Result" dropdown currently takes manual input.
# When Module 2 (ECG Signal Analysis) is connected:
#   1. Add a "Load ECG from Module 2" button.
#   2. Import the Module 2 result (e.g., ecg_analysis.get_result()).
#   3. Auto-fill the ECG dropdown with the Module 2 output.
#   4. The rest of the prediction pipeline stays unchanged.
# -----------------------------------------------------------------

import tkinter as tk
from tkinter import messagebox
import numpy as np

from model import CardiacRiskModel
from database import init_db, next_patient_id, save_prediction
from preprocess import prepare_input


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

        # Patient ID
        self.entries["patient_id"] = self._add_entry(card, "Patient ID:", row)
        self._set_next_patient_id()
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



# ======================== STANDALONE LAUNCH ========================
if __name__ == "__main__":
    root = tk.Tk()
    app = CardiacRiskApp(root)
    root.mainloop()
