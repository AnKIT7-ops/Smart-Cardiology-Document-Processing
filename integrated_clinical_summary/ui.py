import os
import sys
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.database import (  # noqa: E402
    fetch_patient_ids,
    fetch_integrated_report_history,
    fetch_latest_integrated_data,
    fetch_unified_alerts,
    init_db,
    now_text,
    save_integrated_summary,
)


def launch(parent):
    init_db()
    window = tk.Toplevel(parent)
    return IntegratedClinicalSummaryApp(window)


class IntegratedClinicalSummaryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Integrated Clinical Summary")
        self.root.geometry("1300x820")
        self.root.configure(bg="#f3f4f6")
        self.root.minsize(1100, 700)
        self.current_payload = None
        self.history_rows = {}
        self._configure_styles()
        self._build_ui()
        self._refresh_patient_ids()
        self._refresh_history()

    def _configure_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("History.Treeview", rowheight=26, font=("Segoe UI", 9))
        style.configure("History.Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.map(
            "History.Treeview",
            background=[("selected", "#dbeafe")],
            foreground=[("selected", "#1e3a8a")],
        )

    def _build_ui(self):
        container = tk.Frame(self.root, bg="#f3f4f6")
        container.pack(fill="both", expand=True, padx=12, pady=12)
        container.grid_columnconfigure(0, weight=3, uniform="col")
        container.grid_columnconfigure(1, weight=7, uniform="col")
        container.grid_rowconfigure(0, weight=1)

        left_panel = tk.Frame(container, bg="#f8fafc", bd=1, relief="solid")
        right_panel = tk.Frame(container, bg="#ffffff", bd=1, relief="solid")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.grid_rowconfigure(3, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        search_card = tk.Frame(left_panel, bg="#ffffff", bd=1, relief="solid", highlightthickness=1, highlightbackground="#e5e7eb")
        search_card.pack(fill="x", padx=10, pady=(10, 8))
        tk.Label(search_card, text="Patient Search", bg="#ffffff", fg="#111827", font=("Segoe UI", 11, "bold")).pack(
            anchor="w", padx=12, pady=(12, 6)
        )
        form = tk.Frame(search_card, bg="#ffffff")
        form.pack(fill="x", padx=12, pady=(0, 10))
        tk.Label(form, text="Patient ID", bg="#ffffff", fg="#4b5563", font=("Segoe UI", 9)).pack(anchor="w")
        self.patient_id_var = tk.StringVar()
        self.patient_id_combo = ttk.Combobox(form, textvariable=self.patient_id_var, width=24, state="normal")
        self.patient_id_combo.pack(fill="x", pady=(4, 8))
        self.load_btn = tk.Button(
            form,
            text="Load Patient Data",
            bg="#2563eb",
            fg="white",
            relief="flat",
            activebackground="#1d4ed8",
            command=self._load_patient_data,
            font=("Segoe UI", 10, "bold"),
            pady=6,
            cursor="hand2",
        )
        self.load_btn.pack(fill="x", pady=(0, 2))
        self._apply_button_hover(self.load_btn, "#2563eb", "#1d4ed8")

        history_card = tk.Frame(left_panel, bg="#ffffff", bd=1, relief="solid", highlightthickness=1, highlightbackground="#e5e7eb")
        history_card.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        tk.Label(history_card, text="Report History", bg="#ffffff", fg="#111827", font=("Segoe UI", 11, "bold")).pack(
            anchor="w", padx=12, pady=(12, 6)
        )
        history_cols = ("Summary ID", "Patient ID", "Timestamp")
        self.history_tree = ttk.Treeview(
            history_card, columns=history_cols, show="headings", height=28, style="History.Treeview", selectmode="browse"
        )
        for col, width in (("Summary ID", 90), ("Patient ID", 100), ("Timestamp", 180)):
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=width, anchor="center")
        history_scroll = ttk.Scrollbar(history_card, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=history_scroll.set)
        self.history_tree.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=(0, 12))
        history_scroll.pack(side="right", fill="y", padx=(6, 12), pady=(0, 12))
        self.history_tree.bind("<<TreeviewSelect>>", self._on_history_select)
        self.history_tree.bind("<Double-1>", self._load_selected_history)

        header = tk.Frame(right_panel, bg="#ffffff")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        tk.Label(header, text="Integrated Clinical Summary", bg="#ffffff", fg="#111827", font=("Segoe UI", 13, "bold")).pack(
            side="left", anchor="w"
        )
        self.timestamp_label = tk.Label(header, text=f"Updated: {self._format_timestamp(now_text())}", bg="#ffffff", fg="#6b7280", font=("Segoe UI", 9))
        self.timestamp_label.pack(side="right")

        banner = tk.Frame(right_panel, bg="#eff6ff", bd=1, relief="solid", highlightthickness=1, highlightbackground="#bfdbfe")
        banner.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        self.patient_status_label = tk.Label(
            banner,
            text="Patient Status: No patient selected",
            bg="#eff6ff",
            fg="#1e3a8a",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=6,
        )
        self.risk_badge = tk.Label(
            banner, text="RISK: N/A", bg="#e5e7eb", fg="#111827", font=("Segoe UI", 9, "bold"), padx=10, pady=4
        )
        self.patient_status_label.pack(side="left")
        self.risk_badge.pack(side="right", padx=(0, 10))

        self.status_label = tk.Label(
            right_panel,
            text="Clinical Status: Awaiting patient selection",
            bg="#ffffff",
            fg="#374151",
            font=("Segoe UI", 10, "bold"),
        )
        self.status_label.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 8))

        text_wrap = tk.Frame(right_panel, bg="#ffffff")
        text_wrap.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 10))
        text_wrap.grid_rowconfigure(0, weight=1)
        text_wrap.grid_columnconfigure(0, weight=1)
        self.content_box = tk.Text(
            text_wrap,
            wrap="word",
            bg="#ffffff",
            fg="#111827",
            font=("Segoe UI", 10),
            relief="solid",
            bd=1,
            padx=10,
            pady=10,
            spacing1=2,
            spacing2=2,
            spacing3=6,
        )
        self.content_box.grid(row=0, column=0, sticky="nsew")
        text_scroll = ttk.Scrollbar(text_wrap, orient="vertical", command=self.content_box.yview)
        text_scroll.grid(row=0, column=1, sticky="ns")
        self.content_box.configure(yscrollcommand=text_scroll.set)
        self.content_box.tag_configure("section_title", font=("Segoe UI", 10, "bold"), foreground="#1f2937")
        self.content_box.tag_configure("section_emphasis", font=("Segoe UI", 10, "bold"), foreground="#b91c1c")
        self.content_box.tag_configure("card_bg", background="#f8fafc")
        self.content_box.tag_configure("critical_bg", background="#fef2f2")
        self.content_box.tag_configure("muted_label", foreground="#6b7280", font=("Segoe UI", 9, "bold"))
        self.content_box.tag_configure("urgent_text", foreground="#991b1b", font=("Segoe UI", 10, "bold"))

        action_bar = tk.Frame(right_panel, bg="#ffffff")
        action_bar.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 12))
        self.pdf_btn = tk.Button(
            action_bar,
            text="Generate PDF",
            bg="#16a34a",
            fg="white",
            relief="flat",
            activebackground="#15803d",
            command=self._generate_pdf,
            width=18,
            font=("Segoe UI", 10, "bold"),
            pady=6,
            cursor="hand2",
        )
        self.pdf_btn.pack(side="left", padx=(0, 8))
        self._apply_button_hover(self.pdf_btn, "#16a34a", "#15803d")
        self.export_btn = tk.Button(
            action_bar,
            text="Export Summary",
            bg="#374151",
            fg="white",
            relief="flat",
            activebackground="#1f2937",
            command=self._export_summary,
            width=18,
            font=("Segoe UI", 10, "bold"),
            pady=6,
            cursor="hand2",
        )
        self.export_btn.pack(side="left")
        self._apply_button_hover(self.export_btn, "#374151", "#1f2937")

    def _apply_button_hover(self, button, normal_bg, hover_bg):
        button.bind("<Enter>", lambda _e: button.config(bg=hover_bg))
        button.bind("<Leave>", lambda _e: button.config(bg=normal_bg))

    def _format_timestamp(self, value):
        text = str(value or "").strip()
        if not text:
            return ""
        try:
            return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").strftime("%d %b %Y, %I:%M %p")
        except ValueError:
            return text

    def _update_risk_visuals(self, payload):
        prediction = payload.get("prediction") or {}
        level = str(prediction.get("risk_level") or "N/A").upper()
        if level == "CRITICAL":
            badge_bg, badge_fg = "#fee2e2", "#991b1b"
        elif level == "HIGH":
            badge_bg, badge_fg = "#ffedd5", "#9a3412"
        elif level in {"MODERATE", "MEDIUM"}:
            badge_bg, badge_fg = "#fef3c7", "#92400e"
        elif level == "LOW":
            badge_bg, badge_fg = "#dcfce7", "#166534"
        else:
            badge_bg, badge_fg = "#e5e7eb", "#111827"
        self.risk_badge.config(text=f"RISK: {level}", bg=badge_bg, fg=badge_fg)
        patient = payload.get("patient") or {}
        patient_id = patient.get("patient_id", "N/A")
        patient_name = patient.get("patient_name") or "Unnamed"
        self.patient_status_label.config(text=f"Patient Status: {patient_name} ({patient_id})")
        self.status_label.config(text=f"Clinical Status: Summary loaded for patient {patient_id}")
        self.timestamp_label.config(text=f"Updated: {self._format_timestamp(now_text())}")

    def _render_payload(self, payload):
        ocr_text = payload.get("ocr_findings", "")
        ecg_text = payload.get("ecg_findings", "")
        risk_text = payload.get("risk_prediction", "")
        ai_summary = payload.get("ai_summary", "")
        key_findings = payload.get("key_findings", "")
        critical_observations = payload.get("critical_observations", "")
        followup = payload.get("followup_recommendation", "")
        Doctor_notes = payload.get("Doctor_notes", "")

        blocks = [
            ("OCR Findings", ocr_text),
            ("ECG Findings", ecg_text),
            ("Risk Prediction", risk_text),
            ("AI Summary", ai_summary),
            ("Key Findings", key_findings),
            ("Critical Observations", critical_observations),
            ("Follow-up Recommendation", followup),
            ("Doctor Notes", Doctor_notes),
        ]
        self.content_box.delete("1.0", "end")
        for title, text in blocks:
            block_start = self.content_box.index("end-1c")
            if block_start != "1.0":
                self.content_box.insert("end", "\n")
            title_start = self.content_box.index("end-1c")
            self.content_box.insert("end", f"{title}\n")
            self.content_box.insert("end", f"{text or 'N/A'}\n")
            self.content_box.insert("end", "-" * 72 + "\n")
            block_end = self.content_box.index("end-1c")
            tag = "critical_bg" if title == "Critical Observations" else "card_bg"
            self.content_box.tag_add(tag, block_start, block_end)
            title_tag = "section_emphasis" if title == "Critical Observations" else "section_title"
            self.content_box.tag_add(title_tag, title_start, f"{title_start}+{len(title)}c")
        for token in ("CRITICAL", "HIGH", "urgent", "emergency", "ST Elevation", "Ventricular Tachycardia"):
            start = "1.0"
            while True:
                pos = self.content_box.search(token, start, stopindex="end", nocase=True)
                if not pos:
                    break
                self.content_box.tag_add("urgent_text", pos, f"{pos}+{len(token)}c")
                start = f"{pos}+1c"
        self._update_risk_visuals(payload)

    def _refresh_patient_ids(self):
        patient_ids = fetch_patient_ids(limit=1000)
        self.patient_id_combo["values"] = patient_ids

    def _build_summary(self, context):
        patient = context.get("patient") or {}
        report = context.get("report") or {}
        ecg = context.get("ecg") or {}
        prediction = context.get("prediction") or {}
        latest_summary = context.get("latest_summary") or {}
        alerts = fetch_unified_alerts(patient_id=patient.get("patient_id"))
        critical_alerts = [a for a in alerts if str(a.get("severity", "")).upper() in {"HIGH", "CRITICAL"}]

        ocr_findings = (
            f"Extracted Text: {report.get('extracted_text') or 'N/A'}\n"
            f"Diagnosis: {report.get('diagnosis_text') or 'N/A'}"
        )
        ecg_findings = (
            f"HR {ecg.get('heart_rate', 'N/A')} bpm, rhythm {ecg.get('rhythm_type', 'N/A')}, "
            f"abnormality {ecg.get('abnormality_detected', 'N/A')}, ST {ecg.get('st_change', 'N/A')}"
        )
        probability = prediction.get("probability")
        probability_text = "N/A" if probability in (None, "") else f"{probability}"
        risk_prediction = (
            f"Risk {prediction.get('risk_level', 'N/A')} ({probability_text}%), "
            f"action: {prediction.get('suggested_action', 'N/A')}"
        )
        generated_ai_summary = (
            f"Patient {patient.get('patient_id', 'N/A')} demonstrates OCR findings suggestive of "
            f"{report.get('diagnosis_text') or 'no definitive diagnosis documented'}. "
            f"ECG review indicates {ecg.get('abnormality_detected') or ecg.get('rhythm_type') or 'no clear abnormality'} "
            f"with heart rate {ecg.get('heart_rate', 'N/A')} bpm. "
            f"Risk prediction currently categorizes the case as {prediction.get('risk_level', 'N/A')} "
            f"({probability_text}%), supporting {prediction.get('suggested_action', 'continued clinical correlation')}."
        )
        generated_key_findings = (
            f"1) OCR diagnosis: {report.get('diagnosis_text') or 'N/A'}\n"
            f"2) ECG: {ecg.get('abnormality_detected') or ecg.get('rhythm_type') or 'N/A'}\n"
            f"3) Risk model: {prediction.get('risk_level', 'N/A')} ({prediction.get('probability', 'N/A')}%)"
        )
        critical_lines = []
        for alert in critical_alerts[:5]:
            critical_lines.append(
                f"- [{alert.get('severity')}] {alert.get('alert_type')}: {alert.get('message')}"
            )
        generated_critical_observations = (
            "\n".join(critical_lines) if critical_lines else "No critical alerts at this time."
        )
        followup = prediction.get("followup_required") or "Clinical follow-up recommended."
        Doctor_notes = report.get("doctor_notes") or ""
        ai_summary = latest_summary.get("ai_summary") or generated_ai_summary
        key_findings = latest_summary.get("key_findings") or generated_key_findings
        critical_observations = (
            latest_summary.get("critical_observations") or generated_critical_observations
        )
        followup = latest_summary.get("followup_recommendation") or followup
        Doctor_notes = latest_summary.get("Doctor_notes") or Doctor_notes

        return {
            "patient": patient,
            "report": report,
            "ecg": ecg,
            "prediction": prediction,
            "ocr_findings": ocr_findings,
            "ecg_findings": ecg_findings,
            "risk_prediction": risk_prediction,
            "ai_summary": ai_summary,
            "key_findings": key_findings,
            "critical_observations": critical_observations,
            "followup_recommendation": followup,
            "Doctor_notes": Doctor_notes,
            "critical_alerts": critical_alerts,
        }

    def _load_patient_data(self):
        patient_id = self.patient_id_var.get().strip()
        if not patient_id:
            messagebox.showwarning("Validation", "Enter Patient ID.")
            return
        valid_ids = set(fetch_patient_ids(limit=5000))
        if patient_id not in valid_ids:
            messagebox.showwarning("Validation", "Invalid Patient ID. Select an existing patient ID.")
            self._refresh_patient_ids()
            return
        context = fetch_latest_integrated_data(patient_id)
        if not any([context.get("patient"), context.get("report"), context.get("ecg"), context.get("prediction")]):
            messagebox.showinfo("Not Found", "No records found for this patient.")
            return
        payload = self._build_summary(context)
        self.current_payload = payload
        self._render_payload(payload)
        self._refresh_history(patient_id=patient_id)

    def _refresh_history(self, patient_id=None):
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
        self.history_rows = {}
        history = fetch_integrated_report_history(patient_id=patient_id, limit=200)
        for row in history:
            summary_id = row.get("summary_id")
            self.history_tree.insert(
                "",
                "end",
                values=(summary_id, row.get("patient_id"), self._format_timestamp(row.get("created_at", ""))),
            )
            self.history_rows[str(summary_id)] = row
        children = self.history_tree.get_children()
        if children:
            self.history_tree.selection_set(children[0])
            self.history_tree.focus(children[0])

    def _on_history_select(self, _event):
        selected = self.history_tree.selection()
        if not selected:
            return
        values = self.history_tree.item(selected[0], "values")
        if values:
            self.patient_id_var.set(values[1])

    def _load_selected_history(self, _event):
        selected = self.history_tree.selection()
        if not selected:
            return
        values = self.history_tree.item(selected[0], "values")
        if not values:
            return
        summary_id = str(values[0])
        patient_id = values[1]
        self.patient_id_var.set(patient_id)
        self._load_patient_data()
        selected_row = self.history_rows.get(summary_id)
        if selected_row and self.current_payload:
            self.current_payload["ai_summary"] = selected_row.get("ai_summary") or self.current_payload.get("ai_summary")
            self.current_payload["key_findings"] = selected_row.get("key_findings") or self.current_payload.get("key_findings")
            self.current_payload["critical_observations"] = selected_row.get("critical_observations") or self.current_payload.get("critical_observations")
            self.current_payload["followup_recommendation"] = selected_row.get("followup_recommendation") or self.current_payload.get("followup_recommendation")
            self.current_payload["Doctor_notes"] = selected_row.get("Doctor_notes") or self.current_payload.get("Doctor_notes")
            self._render_payload(self.current_payload)

    def _generate_pdf(self):
        if not self.current_payload:
            messagebox.showinfo( "Load patient data first.")
            return
        output = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"Integrated_Report_{self.current_payload['patient'].get('patient_id', 'patient')}.pdf",
        )
        if not output:
            return
        self._create_pdf(output, self.current_payload)
        summary_id = save_integrated_summary(
            {
                "patient_id": self.current_payload["patient"].get("patient_id", ""),
                "report_id": self.current_payload["report"].get("report_id"),
                "ecg_id": self.current_payload["ecg"].get("ecg_id"),
                "prediction_id": self.current_payload["prediction"].get("prediction_id"),
                "ai_summary": self.current_payload.get("ai_summary"),
                "key_findings": self.current_payload.get("key_findings"),
                "critical_observations": self.current_payload.get("critical_observations"),
                "followup_recommendation": self.current_payload.get("followup_recommendation"),
                "Doctor_notes": self.current_payload.get("Doctor_notes"),
                "generated_pdf_path": output,
                "created_at": now_text(),
            }
        )
        self._refresh_history(patient_id=self.current_payload["patient"].get("patient_id"))
        self._refresh_patient_ids()
        messagebox.showinfo( f"Integrated PDF generated.\nSummary ID: {summary_id}")

    def _create_pdf(self, output_path, payload):
        styles = getSampleStyleSheet()
        h1 = ParagraphStyle(
            "h1",
            parent=styles["Heading1"],
            textColor=colors.HexColor("#0f172a"),
            fontSize=18,
            spaceAfter=6,
        )
        h2 = ParagraphStyle(
            "h2",
            parent=styles["Heading2"],
            textColor=colors.HexColor("#1e3a8a"),
            fontSize=12,
            spaceBefore=8,
            spaceAfter=4,
        )
        body = ParagraphStyle(
            "body",
            parent=styles["BodyText"],
            leading=15,
            fontSize=10,
            textColor=colors.HexColor("#111827"),
            spaceAfter=4,
        )
        critical_style = ParagraphStyle(
            "critical",
            parent=body,
            backColor=colors.HexColor("#fee2e2"),
            borderPadding=6,
            textColor=colors.HexColor("#991b1b"),
        )
        risk_high_style = ParagraphStyle(
            "risk_high",
            parent=body,
            backColor=colors.HexColor("#ffedd5"),
            borderPadding=6,
            textColor=colors.HexColor("#9a3412"),
        )
        risk_medium_style = ParagraphStyle(
            "risk_medium",
            parent=body,
            backColor=colors.HexColor("#fef3c7"),
            borderPadding=6,
            textColor=colors.HexColor("#92400e"),
        )
        risk_low_style = ParagraphStyle(
            "risk_low",
            parent=body,
            backColor=colors.HexColor("#dcfce7"),
            borderPadding=6,
            textColor=colors.HexColor("#166534"),
        )
        disclaimer_style = ParagraphStyle(
            "disclaimer",
            parent=body,
            textColor=colors.HexColor("#374151"),
            fontSize=9,
            leading=13,
            backColor=colors.HexColor("#f3f4f6"),
            borderPadding=6,
        )
        small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=8, textColor=colors.grey, alignment=2)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
        )
        story = [
            Paragraph("Integrated Clinical Report", h1),
            Paragraph("Digital Cardiology Unit - Clinical Decision Support", body),
            Spacer(1, 8),
        ]

        patient = payload["patient"]
        report = payload["report"]
        ecg = payload["ecg"]
        prediction = payload["prediction"]
        critical_alerts = payload["critical_alerts"]
        risk_level = str(prediction.get("risk_level", "")).upper()

        sections = [
            ("Patient Information", f"Patient ID: {patient.get('patient_id', 'N/A')}<br/>Name: {patient.get('patient_name', 'N/A')}<br/>Age: {patient.get('age', 'N/A')}<br/>Gender: {patient.get('gender', 'N/A')}"),
            ("OCR Findings", payload["ocr_findings"]),
            ("ECG Analysis", payload["ecg_findings"] + f"<br/>AI Remarks: {ecg.get('ai_remarks', 'N/A')}"),
            ("Risk Prediction", payload["risk_prediction"] + f"<br/>Model: {prediction.get('model_used', 'N/A')}"),
            ("AI Summary", payload["ai_summary"]),
            (
                "Critical Alerts",
                "<br/>".join(
                    [
                        f"[{a.get('severity')}] {a.get('alert_type')} - {a.get('message')} ({a.get('timestamp')})"
                        for a in critical_alerts
                    ]
                )
                or "No critical alerts.",
            ),
            ("Follow-up Recommendation", payload["followup_recommendation"]),
            ("Doctor Notes", payload["Doctor_notes"] or report.get("doctor_notes") or "No doctor notes."),
            (
                "Disclaimer",
                "This integrated report is AI-assisted and intended to support clinical review. "
                "Final interpretation and treatment decisions remain the responsibility of qualified physicians.",
            ),
        ]
        for title, text in sections:
            story.append(Paragraph(title, h2))
            section_text = (text or "N/A").replace("\n", "<br/>")
            style_to_use = critical_style if title == "Critical Alerts" else body
            if title == "Risk Prediction":
                if risk_level in {"CRITICAL", "HIGH"}:
                    style_to_use = risk_high_style
                elif risk_level in {"MODERATE", "MEDIUM"}:
                    style_to_use = risk_medium_style
                elif risk_level == "LOW":
                    style_to_use = risk_low_style
            if title == "Disclaimer":
                style_to_use = disclaimer_style
            story.append(Paragraph(section_text, style_to_use))
            story.append(Spacer(1, 8))
        story.append(Paragraph(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", small))
        doc.build(story)

    def _export_summary(self):
        if not self.current_payload:
            messagebox.showinfo("Load patient data first.")
            return
        output = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("All files", "*.*")],
            initialfile=f"Integrated_Summary_{self.current_payload['patient'].get('patient_id', 'patient')}.txt",
        )
        if not output:
            return
        with open(output, "w", encoding="utf-8") as handle:
            handle.write(self.content_box.get("1.0", "end").strip() + "\n")
        summary_id = save_integrated_summary(
            {
                "patient_id": self.current_payload["patient"].get("patient_id", ""),
                "report_id": self.current_payload["report"].get("report_id"),
                "ecg_id": self.current_payload["ecg"].get("ecg_id"),
                "prediction_id": self.current_payload["prediction"].get("prediction_id"),
                "ai_summary": self.current_payload.get("ai_summary"),
                "key_findings": self.current_payload.get("key_findings"),
                "critical_observations": self.current_payload.get("critical_observations"),
                "followup_recommendation": self.current_payload.get("followup_recommendation"),
                "Doctor_notes": self.current_payload.get("Doctor_notes"),
                "generated_pdf_path": None,
                "created_at": now_text(),
            }
        )
        self._refresh_history(patient_id=self.current_payload["patient"].get("patient_id"))
        self._refresh_patient_ids()
        messagebox.showinfo("Summary Exported", f"Summary exported:\n{output}\nSummary ID: {summary_id}")
