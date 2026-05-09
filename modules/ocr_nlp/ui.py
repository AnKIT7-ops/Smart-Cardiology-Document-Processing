import uuid
import threading
import datetime
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from .main import UploadMeta, run_pipeline
    from .database import DatabaseWrapper
except ImportError:
    from main import UploadMeta, run_pipeline
    from database import DatabaseWrapper
from shared.database import save_ocr_report


C = {
    "bg":          "#F5F7FB",
    "sidebar":     "#1C2B4A",
    "sidebar_sel": "#2E4A7A",
    "sidebar_txt": "#FFFFFF",
    "card":        "#FFFFFF",
    "border":      "#DDE3EE",
    "primary":     "#2E4A7A",
    "accent":      "#4F7BE8",
    "success":     "#1A7A3F",
    "warning":     "#B87800",
    "error":       "#B00020",
    "label":       "#5A6480",
    "value":       "#1A2140",
    "text":        "#1A2140",
}
PAD  = 12
PAD2 = 24


def _card(parent, **kw) -> tk.Frame:
    d = dict(bg=C["card"], relief="flat", bd=0,
             highlightthickness=1, highlightbackground=C["border"])
    d.update(kw)
    return tk.Frame(parent, **d)


def _label(parent, text, size=10, bold=False, color=None, **kw) -> tk.Label:
    return tk.Label(parent, text=text, bg=parent["bg"],
                    fg=color or C["text"],
                    font=("Segoe UI", size, "bold" if bold else "normal"), **kw)


def _section_header(parent, title: str) -> tk.Frame:
    f = tk.Frame(parent, bg=C["bg"])
    tk.Label(f, text=title, bg=C["bg"], fg=C["primary"],
             font=("Segoe UI", 10, "bold")).pack(side="left")
    tk.Frame(f, bg=C["border"], height=1).pack(
        side="left", fill="x", expand=True, padx=(8, 0))
    return f


class Sidebar(tk.Frame):
    PAGES = [
        ("📤", "Upload Document"),
        ("📋", "Extracted Data"),
        ("📊", "History"),
    ]

    def __init__(self, master, on_select, **kw):
        super().__init__(master, bg=C["sidebar"], width=192, **kw)
        self.pack_propagate(False)
        self._on_select = on_select
        self._selected  = 0
        self._rows: list[tuple[tk.Frame, tk.Label]] = []

        # logo
        tk.Label(self, text="🫀", bg=C["sidebar"],
                 font=("Segoe UI", 26)).pack(pady=(20, 2))
        tk.Label(self, text="ECG Processor", bg=C["sidebar"],
                 fg="white", font=("Segoe UI", 11, "bold")).pack()
        tk.Label(self, text="MODULE 1 · OCR + NLP", bg=C["sidebar"],
                 fg="#8BA0C8", font=("Segoe UI", 7)).pack(pady=(0, 18))
        tk.Frame(self, bg="#2E4A7A", height=1).pack(fill="x", padx=16)

        for i, (icon, name) in enumerate(self.PAGES):
            row = tk.Frame(self, bg=C["sidebar"], cursor="hand2")
            row.pack(fill="x", pady=1)
            lbl = tk.Label(row, text=f"  {icon}  {name}",
                           bg=C["sidebar"], fg="white",
                           font=("Segoe UI", 10), anchor="w",
                           padx=8, pady=10)
            lbl.pack(fill="x")
            n = i
            for w in (row, lbl):
                w.bind("<Button-1>", lambda e, x=n: self._click(x))
                w.bind("<Enter>",    lambda e, r=row: r.config(bg=C["sidebar_sel"]))
                w.bind("<Leave>",    lambda e, r=row, x=n:
                       r.config(bg=C["sidebar_sel"]
                                if x == self._selected else C["sidebar"]))
            self._rows.append((row, lbl))

        self._highlight(0)

    def _click(self, idx):
        self._selected = idx
        self._highlight(idx)
        self._on_select(idx)

    def _highlight(self, idx):
        for i, (row, lbl) in enumerate(self._rows):
            bg = C["sidebar_sel"] if i == idx else C["sidebar"]
            row.config(bg=bg); lbl.config(bg=bg)


class UploadPage(tk.Frame):
    def __init__(self, master, db: DatabaseWrapper, on_done, **kw):
        super().__init__(master, bg=C["bg"], **kw)
        self._db       = db
        self._on_done  = on_done   
        self._file_var = tk.StringVar()
        self._vars: dict[str, tk.StringVar] = {}
        self._build()

    def _build(self):
        # title
        hdr = tk.Frame(self, bg=C["bg"])
        hdr.pack(fill="x", padx=PAD2, pady=(PAD2, PAD))
        _label(hdr, "Upload Document", size=18, bold=True,
               color=C["primary"]).pack(side="left")
        _label(hdr, "  ·  Scan & extract ECG / medical documents",
               size=10, color=C["label"]).pack(side="left", pady=(5, 0))

        canvas = tk.Canvas(self, bg=C["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        body = tk.Frame(canvas, bg=C["bg"])
        wid  = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>",
                  lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(wid, width=e.width))
        self._build_body(body)

    def _build_body(self, p):
        _section_header(p, "Document Metadata").pack(
            fill="x", padx=PAD2, pady=(16, 4))

        card = _card(p)
        card.pack(fill="x", padx=PAD2, pady=(0, 8))
        g = tk.Frame(card, bg=C["card"])
        g.pack(fill="x", padx=PAD, pady=PAD)

        text_fields = [
            ("Upload ID",        "upload_id",
             f"UP-{uuid.uuid4().hex[:8].upper()}"),
            ("Patient ID *",     "patient_id",       ""),
            ("Center ID *",      "center_id",        ""),
            ("Technician Name *","technician_name",  ""),
            ("Upload Date",      "upload_date",
             str(datetime.date.today())),
        ]
        for i, (lbl, key, default) in enumerate(text_fields):
            col = (i % 2) * 3
            row = (i // 2) * 2
            tk.Label(g, text=lbl, bg=C["card"], fg=C["label"],
                     font=("Segoe UI", 9)).grid(
                row=row, column=col, sticky="w", padx=(4, 2), pady=(8, 0))
            var = tk.StringVar(value=default)
            self._vars[key] = var
            ttk.Entry(g, textvariable=var, width=32).grid(
                row=row+1, column=col, sticky="ew",
                padx=(4, 20), pady=(2, 4))
            g.columnconfigure(col, weight=1)

        base_row = (len(text_fields) // 2) * 2
        for col_idx, (lbl, key, vals) in enumerate([
            ("File Type",     "file_type",     ["Image", "PDF"]),
            ("Document Type", "document_type", ["ECG", "Prescription", "Report"]),
        ]):
            col = col_idx * 3
            tk.Label(g, text=lbl, bg=C["card"], fg=C["label"],
                     font=("Segoe UI", 9)).grid(
                row=base_row, column=col, sticky="w",
                padx=(4, 2), pady=(8, 0))
            var = tk.StringVar(value=vals[0])
            self._vars[key] = var
            ttk.Combobox(g, textvariable=var, values=vals,
                         state="readonly", width=30).grid(
                row=base_row+1, column=col, sticky="ew",
                padx=(4, 20), pady=(2, 4))

        _section_header(p, "File").pack(fill="x", padx=PAD2, pady=(16, 4))
        fcard = _card(p)
        fcard.pack(fill="x", padx=PAD2, pady=(0, 8))
        fc = tk.Frame(fcard, bg=C["card"])
        fc.pack(fill="x", padx=PAD, pady=PAD)
        tk.Label(fc, text="Selected File", bg=C["card"], fg=C["label"],
                 font=("Segoe UI", 9)).pack(anchor="w")
        frow = tk.Frame(fc, bg=C["card"])
        frow.pack(fill="x", pady=(4, 0))
        ttk.Entry(frow, textvariable=self._file_var,
                  state="readonly", width=56).pack(side="left", fill="x",
                                                    expand=True)
        ttk.Button(frow, text="Browse…",
                   command=self._browse).pack(side="left", padx=(8, 0))

        self._status_var = tk.StringVar()
        self._status_lbl = tk.Label(p, textvariable=self._status_var,
                                    bg=C["bg"], fg=C["label"],
                                    font=("Segoe UI", 9))
        self._status_lbl.pack(anchor="w", padx=PAD2, pady=(4, 0))

        self._progress = ttk.Progressbar(p, mode="indeterminate")

        bf = tk.Frame(p, bg=C["bg"])
        bf.pack(fill="x", padx=PAD2, pady=(8, PAD2))
        self._btn = tk.Button(
            bf, text="🚀  Process Document",
            bg=C["accent"], fg="white", relief="flat",
            font=("Segoe UI", 11, "bold"),
            padx=24, pady=10, cursor="hand2",
            activebackground=C["primary"],
            activeforeground="white",
            command=self._submit)
        self._btn.pack(side="left")

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Select Document",
            filetypes=[("Supported", "*.jpg *.jpeg *.png *.pdf"),
                       ("Images", "*.jpg *.jpeg *.png"),
                       ("PDF", "*.pdf")])
        if path:
            self._file_var.set(path)

    def _submit(self):
        errs = []
        if not self._vars["patient_id"].get().strip():
            errs.append("Patient ID is required.")
        if not self._vars["center_id"].get().strip():
            errs.append("Center ID is required.")
        if not self._vars["technician_name"].get().strip():
            errs.append("Technician Name is required.")
        if not self._file_var.get().strip():
            errs.append("Please select a file.")
        if errs:
            messagebox.showerror("Validation", "\n".join(errs))
            return

        meta = UploadMeta(
            upload_id       = self._vars["upload_id"].get().strip(),
            patient_id      = self._vars["patient_id"].get().strip(),
            file_type       = self._vars["file_type"].get(),
            document_type   = self._vars["document_type"].get(),
            upload_date     = self._vars["upload_date"].get().strip(),
            center_id       = self._vars["center_id"].get().strip(),
            technician_name = self._vars["technician_name"].get().strip(),
            file_path       = self._file_var.get().strip(),
        )
        self._btn.config(state="disabled")
        self._progress.pack(fill="x", padx=PAD2, pady=(4, 0))
        self._progress.start(12)
        self._set_status("⏳ Running OCR + NLP pipeline…", C["warning"])
        threading.Thread(target=self._run, args=(meta,), daemon=True).start()

    def _run(self, meta):
        try:
            extracted = run_pipeline(meta)
            self._db.save_upload(meta)
            self._db.save_extracted(meta.upload_id, extracted)
            shared_report_id = None
            shared_error = None
            try:
                shared_report_id = save_ocr_report(meta, extracted)
            except Exception as exc:
                shared_error = str(exc)
            self.after(
                0,
                self._done,
                meta.upload_id,
                extracted.confidence_score,
                shared_report_id,
                shared_error,
            )
        except Exception as exc:
            self.after(0, self._fail, str(exc))

    def _done(self, uid, conf, shared_report_id=None, shared_error=None):
        self._progress.stop(); self._progress.pack_forget()
        self._btn.config(state="normal")
        col = C["success"] if conf >= 80 else C["warning"] if conf >= 50 else C["error"]
        if shared_error:
            self._set_status(
                f"Done locally. Shared DB sync failed: {shared_error}",
                C["warning"],
            )
        else:
            suffix = f"  |  Shared report: {shared_report_id}" if shared_report_id else ""
            self._set_status(f"Done!  Confidence: {conf:.1f}%{suffix}", col)
        self._on_done(uid)

    def _fail(self, msg):
        self._progress.stop(); self._progress.pack_forget()
        self._btn.config(state="normal")
        self._set_status(f"❌ Error: {msg}", C["error"])
        messagebox.showerror("Pipeline Error", msg)

    def _set_status(self, msg, color=C["label"]):
        self._status_var.set(msg)
        self._status_lbl.config(fg=color)


class ExtractedPage(tk.Frame):
    def __init__(self, master, db: DatabaseWrapper, **kw):
        super().__init__(master, bg=C["bg"], **kw)
        self._db = db
        self._upload_map: dict[str, str] = {}
        self._build()

    def _build(self):
        _label(self, "Extracted Data View", size=18, bold=True,
               color=C["primary"]).pack(anchor="w", padx=PAD2,
                                        pady=(PAD2, PAD))
        # selector
        sc = _card(self)
        sc.pack(fill="x", padx=PAD2, pady=(0, PAD))
        sf = tk.Frame(sc, bg=C["card"])
        sf.pack(fill="x", padx=PAD, pady=8)
        tk.Label(sf, text="Select Upload:", bg=C["card"], fg=C["label"],
                 font=("Segoe UI", 9)).pack(side="left")
        self._sel_var = tk.StringVar()
        self._combo = ttk.Combobox(sf, textvariable=self._sel_var,
                                   state="readonly", width=58)
        self._combo.pack(side="left", padx=8)
        self._combo.bind("<<ComboboxSelected>>", lambda e: self._load())
        ttk.Button(sf, text="↻ Refresh", command=self.refresh).pack(side="left")

        canvas = tk.Canvas(self, bg=C["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        self._body = tk.Frame(canvas, bg=C["bg"])
        wid = canvas.create_window((0, 0), window=self._body, anchor="nw")
        self._body.bind("<Configure>",
                        lambda e: canvas.configure(
                            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(wid, width=e.width))

        _label(self._body, "Select an upload above to view results.",
               color=C["label"]).pack(pady=40)


    def refresh(self, preselect_id: str | None = None):
        uploads = self._db.list_uploads(limit=200)
        labels  = [
            f"{u['upload_id']}  |  Patient: {u['patient_id']}  |  {u['upload_date']}"
            for u in uploads
        ]
        self._upload_map = {lbl: u["upload_id"]
                            for lbl, u in zip(labels, uploads)}
        self._combo["values"] = labels
        if not labels:
            return
        target = labels[0]
        if preselect_id:
            for lbl, uid in self._upload_map.items():
                if uid == preselect_id:
                    target = lbl
                    break
        self._sel_var.set(target)
        self._load()

    def _load(self):
        lbl = self._sel_var.get()
        if not lbl or lbl not in self._upload_map:
            return
        uid  = self._upload_map[lbl]
        data = self._db.get_extracted(uid)
        self._render(data)

    def _render(self, data: dict | None):
        for w in self._body.winfo_children():
            w.destroy()
        if not data:
            _label(self._body, "No extracted data found.",
                   color=C["label"]).pack(pady=40)
            return

        p = self._body

        conf  = data.get("confidence_score", 0)
        ccol  = (C["success"] if conf >= 80
                 else C["warning"] if conf >= 50 else C["error"])
        cf = tk.Frame(p, bg=C["bg"])
        cf.pack(fill="x", padx=PAD2, pady=(8, 4))
        tk.Label(cf, text="Confidence Score:", bg=C["bg"], fg=C["label"],
                 font=("Segoe UI", 10)).pack(side="left")
        tk.Label(cf, text=f"  {conf:.1f}%", bg=C["bg"], fg=ccol,
                 font=("Segoe UI", 13, "bold")).pack(side="left")

        _section_header(p, "👤  Patient Demographics").pack(
            fill="x", padx=PAD2, pady=(12, 4))
        self._kpi_row(p, [
            ("Patient Name", data.get("patient_name")),
            ("Age",          data.get("age")),
            ("Gender",       data.get("gender")),
            ("ECG Date",     data.get("ecg_date")),
        ], val_color=C["value"])


        _section_header(p, "💓  ECG Measurements").pack(
            fill="x", padx=PAD2, pady=(12, 4))
        self._kpi_row(p, [
            ("Heart Rate",   self._u(data.get("heart_rate"),  "bpm")),
            ("PR Interval",  self._u(data.get("pr_interval"), "ms")),
            ("QRS Duration", self._u(data.get("qrs_duration"),"ms")),
            ("QT Interval",  self._u(data.get("qt_interval"), "ms")),
        ], val_color=C["accent"])

        _section_header(p, "🩺  Clinical Text").pack(
            fill="x", padx=PAD2, pady=(12, 4))
        ct_card = _card(p)
        ct_card.pack(fill="x", padx=PAD2, pady=(0, 8))
        ct = tk.Frame(ct_card, bg=C["card"])
        ct.pack(fill="x", padx=PAD, pady=PAD)

        for title, key in [("Diagnosis Text", "diagnosis_text"),
                            ("Doctor Notes",   "doctor_notes")]:
            tk.Label(ct, text=title, bg=C["card"], fg=C["label"],
                     font=("Segoe UI", 9, "bold")).pack(anchor="w",
                                                         pady=(4, 0))
            box = tk.Text(ct, height=3, wrap="word", relief="flat", bd=0,
                          bg="#F5F7FB", fg=C["text"],
                          font=("Segoe UI", 9))
            box.insert("1.0", data.get(key) or "Not detected")
            box.config(state="disabled")
            box.pack(fill="x", pady=(2, 8))


        raw = data.get("raw_lines", [])
        if raw:
            _section_header(p, "🔍  Raw OCR Lines").pack(
                fill="x", padx=PAD2, pady=(12, 4))
            rc = _card(p)
            rc.pack(fill="x", padx=PAD2, pady=(0, PAD2))
            tv = ttk.Treeview(rc, columns=("Text", "Confidence"),
                               show="headings", height=min(10, len(raw)))
            tv.heading("Text",       text="Detected Text")
            tv.heading("Confidence", text="Confidence")
            tv.column("Text",        stretch=True, minwidth=300)
            tv.column("Confidence",  width=110, anchor="center")
            for item in raw:
                tv.insert("", "end", values=(
                    item.get("text", ""),
                    f"{item.get('confidence', 0):.2%}"))
            vsb2 = ttk.Scrollbar(rc, orient="vertical", command=tv.yview)
            tv.configure(yscrollcommand=vsb2.set)
            vsb2.pack(side="right", fill="y")
            tv.pack(fill="x", padx=PAD, pady=PAD)

    def _kpi_row(self, parent, items, val_color=C["value"]):
        card = _card(parent)
        card.pack(fill="x", padx=PAD2, pady=(0, 8))
        g = tk.Frame(card, bg=C["card"])
        g.pack(fill="x", padx=PAD, pady=PAD)
        for i, (lbl, val) in enumerate(items):
            cell = tk.Frame(g, bg=C["card"])
            cell.grid(row=0, column=i, padx=16, pady=8, sticky="nsew")
            g.columnconfigure(i, weight=1)
            tk.Label(cell, text=lbl, bg=C["card"], fg=C["label"],
                     font=("Segoe UI", 8)).pack(anchor="w")
            tk.Label(cell, text=val or "—", bg=C["card"], fg=val_color,
                     font=("Segoe UI", 13, "bold")).pack(anchor="w")

    @staticmethod
    def _u(val, unit):
        return f"{val} {unit}" if val else "—"


class HistoryPage(tk.Frame):
    def __init__(self, master, db: DatabaseWrapper, **kw):
        super().__init__(master, bg=C["bg"], **kw)
        self._db = db
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=C["bg"])
        hdr.pack(fill="x", padx=PAD2, pady=(PAD2, PAD))
        _label(hdr, "Processing History", size=18, bold=True,
               color=C["primary"]).pack(side="left")
        ttk.Button(hdr, text="↻ Refresh",
                   command=self.refresh).pack(side="right")

        # stats row
        self._stats = tk.Frame(self, bg=C["bg"])
        self._stats.pack(fill="x", padx=PAD2, pady=(0, PAD))

        # table
        tc = _card(self)
        tc.pack(fill="both", expand=True, padx=PAD2, pady=(0, PAD2))
        cols = ("Upload ID", "Patient ID", "Doc Type",
                "Date", "Center", "Technician")
        self._tree = ttk.Treeview(tc, columns=cols,
                                   show="headings", selectmode="browse")
        for c in cols:
            w = 160 if c == "Upload ID" else 120
            self._tree.heading(c, text=c)
            self._tree.column(c, width=w, minwidth=80)
        xsb = ttk.Scrollbar(tc, orient="horizontal", command=self._tree.xview)
        ysb = ttk.Scrollbar(tc, orient="vertical",   command=self._tree.yview)
        self._tree.configure(xscrollcommand=xsb.set, yscrollcommand=ysb.set)
        xsb.pack(side="bottom", fill="x")
        ysb.pack(side="right",  fill="y")
        self._tree.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        self.refresh()

    def refresh(self):
        for w in self._stats.winfo_children():
            w.destroy()
        stats = self._db.get_stats()
        for lbl, val in [
            ("Total Uploads",   str(stats.get("total_uploads",  0))),
            ("Unique Patients", str(stats.get("unique_patients", 0))),
            ("Unique Centers",  str(stats.get("unique_centers",  0))),
            ("Avg Confidence",  f"{stats.get('avg_confidence') or 0:.1f}%"),
        ]:
            c = _card(self._stats, padx=16, pady=10)
            c.pack(side="left", padx=(0, 8))
            tk.Label(c, text=lbl,  bg=C["card"], fg=C["label"],
                     font=("Segoe UI", 8)).pack(anchor="w")
            tk.Label(c, text=val,  bg=C["card"], fg=C["primary"],
                     font=("Segoe UI", 15, "bold")).pack(anchor="w")

        for row in self._tree.get_children():
            self._tree.delete(row)
        for u in self._db.list_uploads(limit=200):
            self._tree.insert("", "end", values=(
                u.get("upload_id", ""),
                u.get("patient_id", ""),
                u.get("document_type", ""),
                u.get("upload_date", ""),
                u.get("center_id", ""),
                u.get("technician_name", ""),
            ))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ECG Document Processor — MODULE 1")
        self.geometry("1100x700")
        self.minsize(900, 580)
        self.configure(bg=C["bg"])
        self._apply_styles()
        self._db = DatabaseWrapper()
        self._build()

    def _apply_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TEntry",    padding=6, relief="flat",
                    fieldbackground="white", bordercolor=C["border"])
        s.configure("TCombobox", padding=6, relief="flat")
        s.configure("TButton",   padding=(10, 6))
        s.configure("Treeview",  rowheight=28, font=("Segoe UI", 9),
                    background="white", fieldbackground="white")
        s.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"),
                    background=C["primary"], foreground="white", relief="flat")
        s.map("Treeview", background=[("selected", C["accent"])])
        s.configure("Horizontal.TProgressbar",
                    troughcolor=C["bg"], background=C["accent"])

    def _build(self):
        root = tk.Frame(self, bg=C["bg"])
        root.pack(fill="both", expand=True)

        Sidebar(root, on_select=self._show).pack(side="left", fill="y")

        self._area = tk.Frame(root, bg=C["bg"])
        self._area.pack(side="left", fill="both", expand=True)

        def on_done(uid):
            self._show(1)
            self._pages[1].refresh(preselect_id=uid)

        self._pages = {
            0: UploadPage(self._area,  self._db, on_done=on_done),
            1: ExtractedPage(self._area, self._db),
            2: HistoryPage(self._area,  self._db),
        }
        self._show(0)

    def _show(self, idx: int):
        for page in self._pages.values():
            page.pack_forget()
        self._pages[idx].pack(fill="both", expand=True)
        if idx == 1:
            self._pages[1].refresh()
        elif idx == 2:
            self._pages[2].refresh()



def launch(parent):
    """Called by the main launcher to open Module 1 as a Toplevel window."""
    window = tk.Toplevel(parent)
    window.title("ECG Document Processor — MODULE 1")
    window.geometry("1100x700")
    window.minsize(900, 580)
    window.configure(bg=C["bg"])

    try:
        db = DatabaseWrapper()
    except Exception as e:
        messagebox.showwarning("DB Warning", f"Database issue: {e}")
        return window

    area = tk.Frame(window, bg=C["bg"])
    pages = {}

    def show(idx):
        for page in pages.values():
            page.pack_forget()
        pages[idx].pack(fill="both", expand=True)
        if idx == 1:
            pages[1].refresh()
        elif idx == 2:
            pages[2].refresh()

    def on_done(uid):
        show(1)
        pages[1].refresh(preselect_id=uid)

    Sidebar(window, on_select=show).pack(side="left", fill="y")
    area.pack(side="left", fill="both", expand=True)

    pages[0] = UploadPage(area, db, on_done=on_done)
    pages[1] = ExtractedPage(area, db)
    pages[2] = HistoryPage(area, db)
    show(0)

    return window


def run_ui():
    App().mainloop()


if __name__ == "__main__":
    run_ui()
