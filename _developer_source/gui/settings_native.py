"""
Native Settings Dialog
Fast, lightweight configuration window for Company, Bank, and Sequence defaults.
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, Optional

from core.settings_manager import (
    load_settings,
    save_settings,
    DEFAULT_SETTINGS
)
from gui.window_utils import center_window


class NativeSettingsDialog(tk.Toplevel):
    def __init__(self, parent, on_save_callback: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.on_save_callback = on_save_callback
        self.title("Company & Payment Defaults")
        self.geometry("640x560")
        self.minsize(560, 420)
        self.transient(parent)
        self.grab_set()

        self.settings = load_settings()

        self._build_ui()
        self._load_data()
        center_window(self, parent, 640, 560)

    def _build_ui(self):
        # 1. Pinned Bottom Actions Bar (Packed FIRST so it is NEVER hidden)
        btn_bar = ttk.Frame(self, padding=(16, 10))
        btn_bar.pack(fill="x", side="bottom")

        self.btn_cancel = ttk.Button(btn_bar, text="Cancel", command=self.destroy, width=11)
        self.btn_cancel.pack(side="right", padx=(6, 0))

        self.btn_save = ttk.Button(btn_bar, text="Save Changes", command=self._on_save, width=14)
        self.btn_save.pack(side="right", padx=(6, 0))

        self.btn_restore = ttk.Button(btn_bar, text="Reset Defaults", command=self._on_restore, width=14)
        self.btn_restore.pack(side="left")

        ttk.Separator(self, orient="horizontal").pack(fill="x", side="bottom")

        # 2. Main Scrollable Container (guarantees all sections fit on any screen resolution)
        main_container = ttk.Frame(self)
        main_container.pack(fill="both", expand=True, side="top")

        canvas = tk.Canvas(main_container, highlightthickness=0)
        vscroll = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scroll_content = ttk.Frame(canvas, padding=(16, 12))

        scroll_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=scroll_content, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(canvas_window, width=e.width)
        )
        canvas.configure(yscrollcommand=vscroll.set)

        canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y")

        def _on_mousewheel(event):
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.bind("<MouseWheel>", _on_mousewheel)

        # Company Section
        lbl_sec1 = ttk.Label(scroll_content, text="Company & Issuer Details", font=("Segoe UI", 10, "bold"))
        lbl_sec1.pack(anchor="w", pady=(0, 4))

        f_comp = ttk.LabelFrame(scroll_content, padding=10)
        f_comp.pack(fill="x", pady=(0, 10))

        ttk.Label(f_comp, text="Issuer Name:").grid(row=0, column=0, sticky="w", pady=2)
        self.entry_comp_name = ttk.Entry(f_comp, width=50)
        self.entry_comp_name.grid(row=0, column=1, sticky="ew", pady=2, padx=(6, 0))

        ttk.Label(f_comp, text="Issuer TRN:").grid(row=1, column=0, sticky="w", pady=2)
        self.entry_comp_trn = ttk.Entry(f_comp, width=50)
        self.entry_comp_trn.grid(row=1, column=1, sticky="ew", pady=2, padx=(6, 0))

        ttk.Label(f_comp, text="Footer Location/Tel:").grid(row=2, column=0, sticky="w", pady=2)
        self.entry_footer = ttk.Entry(f_comp, width=50)
        self.entry_footer.grid(row=2, column=1, sticky="ew", pady=2, padx=(6, 0))

        f_comp.grid_columnconfigure(1, weight=1)

        # Bank Details Section
        lbl_sec2 = ttk.Label(scroll_content, text="Bank Settlement Details", font=("Segoe UI", 10, "bold"))
        lbl_sec2.pack(anchor="w", pady=(0, 4))

        f_bank = ttk.LabelFrame(scroll_content, padding=10)
        f_bank.pack(fill="x", pady=(0, 10))

        ttk.Label(f_bank, text="Bank Name:").grid(row=0, column=0, sticky="w", pady=2)
        self.entry_bank_name = ttk.Entry(f_bank, width=50)
        self.entry_bank_name.grid(row=0, column=1, sticky="ew", pady=2, padx=(6, 0))

        ttk.Label(f_bank, text="Account Number:").grid(row=1, column=0, sticky="w", pady=2)
        self.entry_account_no = ttk.Entry(f_bank, width=50)
        self.entry_account_no.grid(row=1, column=1, sticky="ew", pady=2, padx=(6, 0))

        ttk.Label(f_bank, text="Beneficiary Name:").grid(row=2, column=0, sticky="w", pady=2)
        self.entry_beneficiary = ttk.Entry(f_bank, width=50)
        self.entry_beneficiary.grid(row=2, column=1, sticky="ew", pady=2, padx=(6, 0))

        ttk.Label(f_bank, text="IBAN Number:").grid(row=3, column=0, sticky="w", pady=2)
        self.entry_iban = ttk.Entry(f_bank, width=50)
        self.entry_iban.grid(row=3, column=1, sticky="ew", pady=2, padx=(6, 0))

        f_bank.grid_columnconfigure(1, weight=1)

        # Terms & Conditions Section
        lbl_sec3 = ttk.Label(scroll_content, text="Terms & Conditions (One item per line)", font=("Segoe UI", 10, "bold"))
        lbl_sec3.pack(anchor="w", pady=(0, 4))

        f_terms = ttk.LabelFrame(scroll_content, padding=8)
        f_terms.pack(fill="both", expand=True, pady=(0, 4))

        self.txt_terms = tk.Text(f_terms, height=4, font=("Segoe UI", 9), wrap="word")
        self.txt_terms.pack(fill="both", expand=True)

        # Data Vault & Migration Assistant Section
        f_mig = ttk.LabelFrame(scroll_content, text=" Data Vault & Multi-Version Migration ", padding=8)
        f_mig.pack(fill="x", pady=(8, 0))

        lbl_mig_desc = ttk.Label(
            f_mig,
            text="Auto-merge invoices from previous app versions, create full .ZIP backup, or import from external drive.",
            font=("Segoe UI", 8),
            foreground="#475569"
        )
        lbl_mig_desc.pack(side="left", fill="x", expand=True)

        btn_open_mig = ttk.Button(
            f_mig,
            text="🔄 Updates & Migration",
            command=self._open_migration_assistant
        )
        btn_open_mig.pack(side="right", padx=(6, 0))

    def _open_migration_assistant(self):
        from gui.updater_dialog import UpdaterDialog
        UpdaterDialog(self, on_data_updated=self.on_save_callback)

    def _load_data(self):
        c = self.settings.get("company", {})
        self.entry_comp_name.delete(0, "end")
        self.entry_comp_name.insert(0, c.get("name", ""))

        self.entry_comp_trn.delete(0, "end")
        self.entry_comp_trn.insert(0, c.get("trn", ""))

        self.entry_footer.delete(0, "end")
        self.entry_footer.insert(0, c.get("footer_text", ""))

        b = self.settings.get("bank", {})
        self.entry_bank_name.delete(0, "end")
        self.entry_bank_name.insert(0, b.get("bank_name", ""))

        self.entry_account_no.delete(0, "end")
        self.entry_account_no.insert(0, b.get("account_no", ""))

        self.entry_beneficiary.delete(0, "end")
        self.entry_beneficiary.insert(0, b.get("beneficiary_name", ""))

        self.entry_iban.delete(0, "end")
        self.entry_iban.insert(0, b.get("iban", ""))

        terms = self.settings.get("terms", [])
        self.txt_terms.delete("1.0", "end")
        self.txt_terms.insert("1.0", "\n".join(terms))

    def _on_save(self):
        terms_lines = [l.strip() for l in self.txt_terms.get("1.0", "end").splitlines() if l.strip()]

        new_settings = {
            "company": {
                "name": self.entry_comp_name.get().strip(),
                "trn": self.entry_comp_trn.get().strip(),
                "footer_text": self.entry_footer.get().strip()
            },
            "bank": {
                "bank_name": self.entry_bank_name.get().strip(),
                "account_no": self.entry_account_no.get().strip(),
                "beneficiary_name": self.entry_beneficiary.get().strip(),
                "iban": self.entry_iban.get().strip()
            },
            "terms": terms_lines,
            "invoice": self.settings.get("invoice", {}),
            "defaults": self.settings.get("defaults", {}),
            "stamp": {"enabled": False}
        }

        save_settings(new_settings)
        messagebox.showinfo("Saved", "Defaults saved successfully!")
        if self.on_save_callback:
            self.on_save_callback()
        self.destroy()

    def _on_restore(self):
        if messagebox.askyesno("Confirm", "Reset all settings to original Silver Premium defaults?"):
            self.settings = DEFAULT_SETTINGS
            self._load_data()
