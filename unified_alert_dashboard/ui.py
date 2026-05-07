import os
import sys
import tkinter as tk
from tkinter import ttk


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.database import fetch_unified_alerts, init_db  # noqa: E402


def launch(parent):
    init_db()
    window = tk.Toplevel(parent)
    return UnifiedAlertDashboardApp(window)


class UnifiedAlertDashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Module 6 - Unified Alert Monitoring Dashboard")
        self.root.geometry("1400x760")
        self.root.configure(bg="#111827")
        self._build_ui()
        self._refresh_alerts()

    def _build_ui(self):
        top = tk.Frame(self.root, bg="#1f2937")
        top.pack(fill="x", padx=10, pady=10)

        tk.Button(
            top,
            text="Refresh",
            bg="#2563eb",
            fg="white",
            relief="flat",
            command=self._refresh_alerts,
            width=12,
        ).pack(side="left", padx=(0, 8), pady=8)

        tk.Label(top, text="Severity", bg="#1f2937", fg="#f3f4f6").pack(side="left")
        self.severity_var = tk.StringVar(value="ALL")
        ttk.Combobox(
            top,
            textvariable=self.severity_var,
            values=["ALL", "CRITICAL", "HIGH", "MODERATE", "LOW"],
            width=12,
            state="readonly",
        ).pack(side="left", padx=6)

        tk.Label(top, text="Patient ID", bg="#1f2937", fg="#f3f4f6").pack(side="left", padx=(10, 0))
        self.patient_var = tk.StringVar()
        tk.Entry(top, textvariable=self.patient_var, width=16).pack(side="left", padx=6)

        tk.Button(
            top,
            text="Apply Filter",
            bg="#4b5563",
            fg="white",
            relief="flat",
            command=self._refresh_alerts,
            width=12,
        ).pack(side="left", padx=6)

        self.status_lbl = tk.Label(top, text="", bg="#1f2937", fg="#d1d5db", font=("Segoe UI", 9))
        self.status_lbl.pack(side="right", padx=8)

        cols = (
            "Alert ID",
            "Patient ID",
            "Alert Source",
            "Alert Type",
            "Severity",
            "Message",
            "Timestamp",
            "Status",
        )
        table_frame = tk.Frame(self.root, bg="#111827")
        table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        self.tree.pack(side="left", fill="both", expand=True)

        widths = {
            "Alert ID": 110,
            "Patient ID": 100,
            "Alert Source": 140,
            "Alert Type": 170,
            "Severity": 95,
            "Message": 420,
            "Timestamp": 160,
            "Status": 90,
        }
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=widths[col], anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.tag_configure("CRITICAL", background="#7f1d1d", foreground="#fee2e2")
        self.tree.tag_configure("HIGH", background="#7c2d12", foreground="#ffedd5")
        self.tree.tag_configure("MODERATE", background="#78350f", foreground="#fef3c7")
        self.tree.tag_configure("LOW", background="#14532d", foreground="#dcfce7")
        self.tree.tag_configure("DEFAULT", background="#1f2937", foreground="#f3f4f6")

    @staticmethod
    def _dedupe(rows):
        deduped = []
        seen = set()
        for row in rows:
            key = (
                row.get("patient_id"),
                row.get("alert_source"),
                row.get("alert_type"),
                row.get("severity"),
                row.get("message"),
                row.get("timestamp"),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        return deduped

    def _refresh_alerts(self):
        severity = self.severity_var.get().strip().upper()
        patient_id = self.patient_var.get().strip() or None
        rows = fetch_unified_alerts(
            patient_id=patient_id,
            severity=None if severity == "ALL" else severity,
        )
        deduped = self._dedupe(rows)

        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in deduped:
            sev = str(row.get("severity", "MODERATE")).upper()
            tag = sev if sev in {"CRITICAL", "HIGH", "MODERATE", "LOW"} else "DEFAULT"
            self.tree.insert(
                "",
                "end",
                values=(
                    row.get("alert_id", ""),
                    row.get("patient_id", ""),
                    row.get("alert_source", ""),
                    row.get("alert_type", ""),
                    sev,
                    row.get("message", ""),
                    row.get("timestamp", ""),
                    row.get("status", ""),
                ),
                tags=(tag,),
            )
        self.status_lbl.config(text=f"Alert history loaded: {len(deduped)} alerts")
