import tkinter as tk
from tkinter import ttk, messagebox
import threading

from database import (
    fetch_all_records,
    count_by_status,
    save_offline_record,
    delete_record,
    init_db,
)
from main import (
    run_sync_cycle,
    start_scheduler,
    stop_scheduler,
    scheduler_is_running,
    on_sync_done,
    is_main_db_accessible,
    MAIN_DB_PATH,
)

BG_DARK    = "#1A1D2E"
BG_CARD    = "#252840"
BG_INPUT   = "#2E3250"
ACCENT     = "#4A90D9"
SUCCESS    = "#27AE60"
WARNING    = "#F39C12"
DANGER     = "#E74C3C"
TEXT_WHITE = "#ECEFF4"
TEXT_MUTED = "#8A95B0"
BORDER     = "#3A3F5C"

STATUS_COLORS = {
    "SYNCED":  SUCCESS,
    "PENDING": WARNING,
    "FAILED":  DANGER,
}

DEVICE_ID = "DEV-MANGALURU-01"    



class SyncDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        init_db()

        self.title("Module 8 — Offline Data Capture & Sync  |  CAD Foundation")
        self.geometry("1100x680")
        self.minsize(900, 580)
        self.configure(bg=BG_DARK)

        on_sync_done(self._on_sync_complete)

        self._build_ui()
        self._refresh_table()
        self._refresh_stats()
        self._update_scheduler_btn()
        self._poll_online_status()


    def _build_ui(self):
        top = tk.Frame(self, bg=BG_DARK, pady=10)
        top.pack(fill="x", padx=20)

        tk.Label(
            top, text="🫀 CAD — Module 8: Offline Sync Dashboard",
            bg=BG_DARK, fg=TEXT_WHITE,
            font=("Segoe UI", 15, "bold"),
        ).pack(side="left")

        self._db_var = tk.StringVar(value="● Checking DB…")
        self._db_lbl = tk.Label(
            top, textvariable=self._db_var,
            bg=BG_DARK, fg=TEXT_MUTED,
            font=("Segoe UI", 10, "bold"),
        )
        self._db_lbl.pack(side="right", padx=(0, 10))

        tk.Label(
            top, text=f"Target DB: {MAIN_DB_PATH}",
            bg=BG_DARK, fg=TEXT_MUTED,
            font=("Segoe UI", 9),
        ).pack(side="right", padx=20)

        stats_frame = tk.Frame(self, bg=BG_DARK)
        stats_frame.pack(fill="x", padx=20, pady=(0, 12))

        self._stat_vars = {}
        for label, key, color in [
            ("PENDING",  "PENDING", WARNING),
            ("SYNCED",   "SYNCED",  SUCCESS),
            ("FAILED",   "FAILED",  DANGER),
        ]:
            card = tk.Frame(stats_frame, bg=BG_CARD, bd=0, relief="flat",
                            padx=20, pady=12)
            card.pack(side="left", padx=(0, 12), ipadx=10)
            var = tk.StringVar(value="0")
            self._stat_vars[key] = var
            tk.Label(card, textvariable=var, bg=BG_CARD, fg=color,
                     font=("Segoe UI", 22, "bold")).pack()
            tk.Label(card, text=label, bg=BG_CARD, fg=TEXT_MUTED,
                     font=("Segoe UI", 9)).pack()

        btn_frame = tk.Frame(self, bg=BG_DARK)
        btn_frame.pack(fill="x", padx=20, pady=(0, 10))

        self._sync_btn = self._btn(
            btn_frame, "⟳  Sync Now", self._manual_sync, ACCENT)
        self._sync_btn.pack(side="left", padx=(0, 8))

        self._scheduler_btn = self._btn(
            btn_frame, "▶  Start Auto-Sync", self._toggle_scheduler, SUCCESS)
        self._scheduler_btn.pack(side="left", padx=(0, 8))

        self._btn(btn_frame, "+ Add Test Record", self._open_add_dialog,
                  BG_INPUT).pack(side="left", padx=(0, 8))

        self._btn(btn_frame, "🗑  Delete Selected", self._delete_selected,
                  DANGER).pack(side="left")

        self._btn(btn_frame, "↺  Refresh", self._refresh_all,
                  BG_CARD).pack(side="right")

        tbl_frame = tk.Frame(self, bg=BG_DARK, padx=20, pady=0)
        tbl_frame.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        cols = ("local_record_id", "module_name", "sync_status",
                "device_id", "last_sync_time")
        col_widths = (200, 120, 100, 180, 180)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("CAD.Treeview",
                        background=BG_CARD,
                        foreground=TEXT_WHITE,
                        fieldbackground=BG_CARD,
                        rowheight=32,
                        font=("Segoe UI", 10))
        style.configure("CAD.Treeview.Heading",
                        background=BG_INPUT,
                        foreground=TEXT_WHITE,
                        font=("Segoe UI", 10, "bold"),
                        relief="flat")
        style.map("CAD.Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", TEXT_WHITE)])

        self._tree = ttk.Treeview(
            tbl_frame, columns=cols, show="headings",
            style="CAD.Treeview", selectmode="browse",
        )
        headers = ("Local Record ID", "Module", "Status",
                   "Device ID", "Last Sync Time")
        for col, header, width in zip(cols, headers, col_widths):
            self._tree.heading(col, text=header,
                               command=lambda c=col: self._sort_by(c))
            self._tree.column(col, width=width, anchor="w", minwidth=80)

        for status, color in STATUS_COLORS.items():
            self._tree.tag_configure(status, foreground=color)

        vsb = ttk.Scrollbar(tbl_frame, orient="vertical",
                            command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)

        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # ── Status bar ───────────────────────
        self._status_var = tk.StringVar(value="Ready.")
        tk.Label(
            self, textvariable=self._status_var,
            bg=BG_DARK, fg=TEXT_MUTED,
            font=("Segoe UI", 9), anchor="w", padx=20,
        ).pack(fill="x", pady=(0, 6))

  
    def _refresh_table(self):
        self._tree.delete(*self._tree.get_children())
        for rec in fetch_all_records():
            status = rec.get("sync_status", "")
            self._tree.insert(
                "", "end",
                values=(
                    rec["local_record_id"],
                    rec["module_name"],
                    status,
                    rec.get("device_id", "—"),
                    rec.get("last_sync_time", "—"),
                ),
                tags=(status,),
            )

    def _refresh_stats(self):
        counts = count_by_status()
        for key, var in self._stat_vars.items():
            var.set(str(counts.get(key, 0)))

    def _refresh_all(self):
        self._refresh_table()
        self._refresh_stats()
        self._status_var.set("Table refreshed.")

    def _sort_by(self, col):
        """Sort treeview by column (ascending toggle)."""
        rows = [(self._tree.set(iid, col), iid)
                for iid in self._tree.get_children()]
        rows.sort()
        for idx, (_, iid) in enumerate(rows):
            self._tree.move(iid, "", idx)

    def _manual_sync(self):
        self._status_var.set("Syncing…")
        self._sync_btn.config(state="disabled")

        def _worker():
            stats = run_sync_cycle(device_id=DEVICE_ID)
            self.after(0, lambda: self._post_manual_sync(stats))

        threading.Thread(target=_worker, daemon=True).start()

    def _post_manual_sync(self, stats: dict):
        self._sync_btn.config(state="normal")
        if stats["attempted"] == 0:
            msg = "No pending records — or device is offline."
        else:
            msg = (f"Sync complete: "
                   f"{stats['synced']} synced, {stats['failed']} failed.")
        self._status_var.set(msg)
        self._refresh_all()

    def _on_sync_complete(self, stats: dict):
        """Called by the background scheduler after each cycle."""
        self.after(0, self._refresh_all)

    def _toggle_scheduler(self):
        if scheduler_is_running():
            stop_scheduler()
        else:
            start_scheduler(device_id=DEVICE_ID)
        self.after(500, self._update_scheduler_btn)

    def _update_scheduler_btn(self):
        if scheduler_is_running():
            self._scheduler_btn.config(text="⏹  Stop Auto-Sync", bg=DANGER)
        else:
            self._scheduler_btn.config(text="▶  Start Auto-Sync", bg=SUCCESS)
        self.after(2000, self._update_scheduler_btn)

  
    def _open_add_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Add Offline Record")
        dlg.geometry("380x220")
        dlg.configure(bg=BG_DARK)
        dlg.grab_set()

        def lbl(text, row):
            tk.Label(dlg, text=text, bg=BG_DARK, fg=TEXT_WHITE,
                     font=("Segoe UI", 10)).grid(
                row=row, column=0, sticky="w", padx=20, pady=8)

        lbl("Module Name:", 0)
        module_var = tk.StringVar(value="MODULE_1")
        module_menu = ttk.Combobox(
            dlg, textvariable=module_var, width=22,
            values=["MODULE_1", "MODULE_2", "MODULE_3",
                    "MODULE_4", "MODULE_5", "MODULE_6", "MODULE_7"],
            state="readonly",
        )
        module_menu.grid(row=0, column=1, padx=10, pady=8)

        lbl("Device ID:", 1)
        device_entry = tk.Entry(dlg, width=25, bg=BG_INPUT, fg=TEXT_WHITE,
                                insertbackground=TEXT_WHITE,
                                font=("Segoe UI", 10))
        device_entry.insert(0, DEVICE_ID)
        device_entry.grid(row=1, column=1, padx=10, pady=8)

        def _save():
            mod = module_var.get().strip()
            dev = device_entry.get().strip()
            if not mod or not dev:
                messagebox.showwarning("Missing Fields",
                                       "Module and Device ID are required.",
                                       parent=dlg)
                return
            rid = save_offline_record(mod, dev)
            self._status_var.set(f"Record saved: {rid}")
            self._refresh_all()
            dlg.destroy()

        self._btn(dlg, "Save Record", _save, SUCCESS).grid(
            row=2, column=0, columnspan=2, pady=16, ipadx=10)

    def _delete_selected(self):
        selected = self._tree.selection()
        if not selected:
            messagebox.showinfo("Nothing selected",
                                "Click a row first, then press Delete.")
            return
        values = self._tree.item(selected[0], "values")
        rid = values[0]
        if messagebox.askyesno("Confirm Delete",
                               f"Delete record {rid}?"):
            delete_record(rid)
            self._refresh_all()
            self._status_var.set(f"Deleted: {rid}")


    def _poll_online_status(self):
        def _check():
            accessible = is_main_db_accessible()
            self.after(0, lambda: self._set_db_indicator(accessible))

        threading.Thread(target=_check, daemon=True).start()
        self.after(15_000, self._poll_online_status)   # recheck every 15s

    def _set_db_indicator(self, accessible: bool):
        if accessible:
            self._db_var.set("● DB Connected")
            self._db_lbl.config(fg=SUCCESS)
        else:
            self._db_var.set("● DB Not Found")
            self._db_lbl.config(fg=DANGER)


    @staticmethod
    def _btn(parent, text, command, bg) -> tk.Button:
        return tk.Button(
            parent, text=text, command=command,
            bg=bg, fg=TEXT_WHITE, activebackground=bg,
            font=("Segoe UI", 10, "bold"),
            relief="flat", padx=14, pady=6, cursor="hand2",
        )

def launch(parent):
    """Called by the main launcher to open Module 8 as a Toplevel window."""
    init_db()
    window = tk.Toplevel(parent)
    window.title("Module 8 — Offline Data Capture & Sync  |  CAD Foundation")
    window.geometry("1100x680")
    window.minsize(900, 580)
    window.configure(bg=BG_DARK)

    # Build a simplified version of SyncDashboard inside the Toplevel
    app = SyncDashboard.__new__(SyncDashboard)
    app.root = window
    # Monkey-patch the Tk methods to use the Toplevel
    app.title = window.title
    app.geometry = window.geometry
    app.minsize = window.minsize
    app.configure = window.configure
    app.after = window.after

    # Re-run the init logic on the toplevel
    on_sync_done(app._on_sync_complete)
    app._build_ui_on(window)
    app._refresh_table()
    app._refresh_stats()
    app._update_scheduler_btn()
    app._poll_online_status()

    return window


# Extend SyncDashboard with a method that builds UI on a given parent
def _build_ui_on(self, root):
    """Build the dashboard UI on a given root (Tk or Toplevel)."""
    self.root = root

    top = tk.Frame(root, bg=BG_DARK, pady=10)
    top.pack(fill="x", padx=20)

    tk.Label(
        top, text="🫀 CAD — Module 8: Offline Sync Dashboard",
        bg=BG_DARK, fg=TEXT_WHITE,
        font=("Segoe UI", 15, "bold"),
    ).pack(side="left")

    self._db_var = tk.StringVar(value="● Checking DB…")
    self._db_lbl = tk.Label(
        top, textvariable=self._db_var,
        bg=BG_DARK, fg=TEXT_MUTED,
        font=("Segoe UI", 10, "bold"),
    )
    self._db_lbl.pack(side="right", padx=(0, 10))

    tk.Label(
        top, text=f"Target DB: {MAIN_DB_PATH}",
        bg=BG_DARK, fg=TEXT_MUTED,
        font=("Segoe UI", 9),
    ).pack(side="right", padx=20)

    stats_frame = tk.Frame(root, bg=BG_DARK)
    stats_frame.pack(fill="x", padx=20, pady=(0, 12))

    self._stat_vars = {}
    for label, key, color in [
        ("PENDING",  "PENDING", WARNING),
        ("SYNCED",   "SYNCED",  SUCCESS),
        ("FAILED",   "FAILED",  DANGER),
    ]:
        card = tk.Frame(stats_frame, bg=BG_CARD, bd=0, relief="flat",
                        padx=20, pady=12)
        card.pack(side="left", padx=(0, 12), ipadx=10)
        var = tk.StringVar(value="0")
        self._stat_vars[key] = var
        tk.Label(card, textvariable=var, bg=BG_CARD, fg=color,
                 font=("Segoe UI", 22, "bold")).pack()
        tk.Label(card, text=label, bg=BG_CARD, fg=TEXT_MUTED,
                 font=("Segoe UI", 9)).pack()

    btn_frame = tk.Frame(root, bg=BG_DARK)
    btn_frame.pack(fill="x", padx=20, pady=(0, 10))

    self._sync_btn = self._btn(
        btn_frame, "⟳  Sync Now", self._manual_sync, ACCENT)
    self._sync_btn.pack(side="left", padx=(0, 8))

    self._scheduler_btn = self._btn(
        btn_frame, "▶  Start Auto-Sync", self._toggle_scheduler, SUCCESS)
    self._scheduler_btn.pack(side="left", padx=(0, 8))

    self._btn(btn_frame, "+ Add Test Record", self._open_add_dialog,
              BG_INPUT).pack(side="left", padx=(0, 8))

    self._btn(btn_frame, "🗑  Delete Selected", self._delete_selected,
              DANGER).pack(side="left")

    self._btn(btn_frame, "↺  Refresh", self._refresh_all,
              BG_CARD).pack(side="right")

    tbl_frame = tk.Frame(root, bg=BG_DARK, padx=20, pady=0)
    tbl_frame.pack(fill="both", expand=True, padx=20, pady=(0, 8))

    cols = ("local_record_id", "module_name", "sync_status",
            "device_id", "last_sync_time")
    col_widths = (200, 120, 100, 180, 180)

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("CAD.Treeview",
                    background=BG_CARD,
                    foreground=TEXT_WHITE,
                    fieldbackground=BG_CARD,
                    rowheight=32,
                    font=("Segoe UI", 10))
    style.configure("CAD.Treeview.Heading",
                    background=BG_INPUT,
                    foreground=TEXT_WHITE,
                    font=("Segoe UI", 10, "bold"),
                    relief="flat")
    style.map("CAD.Treeview",
              background=[("selected", ACCENT)],
              foreground=[("selected", TEXT_WHITE)])

    self._tree = ttk.Treeview(
        tbl_frame, columns=cols, show="headings",
        style="CAD.Treeview", selectmode="browse",
    )
    headers = ("Local Record ID", "Module", "Status",
               "Device ID", "Last Sync Time")
    for col, header, width in zip(cols, headers, col_widths):
        self._tree.heading(col, text=header,
                           command=lambda c=col: self._sort_by(c))
        self._tree.column(col, width=width, anchor="w", minwidth=80)

    for status, color in STATUS_COLORS.items():
        self._tree.tag_configure(status, foreground=color)

    vsb = ttk.Scrollbar(tbl_frame, orient="vertical",
                        command=self._tree.yview)
    self._tree.configure(yscrollcommand=vsb.set)

    self._tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    self._status_var = tk.StringVar(value="Ready.")
    tk.Label(
        root, textvariable=self._status_var,
        bg=BG_DARK, fg=TEXT_MUTED,
        font=("Segoe UI", 9), anchor="w", padx=20,
    ).pack(fill="x", pady=(0, 6))


SyncDashboard._build_ui_on = _build_ui_on


if __name__ == "__main__":
    app = SyncDashboard()
    app.mainloop()
