"""
Silver Premium Tax Invoice Generator - Native Fast Edition
High-performance, lightweight native desktop interface built with Python tkinter & ttk.
Fully responsive:
- Sticky Top Toolbar (never clipped)
- Sticky Bottom Action Bar (always visible on any screen size)
- Scrollable middle workspace with smooth mousewheel support
- Clean +1 sequential numbering & 1-click Invoices folder archiving
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from typing import List, Dict, Any, Optional

from core.settings_manager import load_settings, save_settings
from core.records_manager import (
    get_invoices_dir,
    get_next_sequential_number,
    record_new_invoice,
    get_standard_pdf_filename,
    open_invoices_folder,
    open_pdf_file
)
from core.num_to_words_helper import amount_to_aed_words
from core.pdf_engine import generate_invoice_pdf, get_asset_path
from core.customer_manager import (
    load_customers,
    save_or_update_customer,
    get_customer_by_name,
    get_customer_by_id
)
from gui.history_view import HistoryDialog
from gui.settings_native import NativeSettingsDialog
from gui.customers_dialog import CustomerProfilesDialog
from gui.updater_dialog import UpdaterDialog
from gui.window_utils import center_window
from core.migration_manager import (
    APP_VERSION,
    check_and_run_startup_migration,
    get_master_vault_dir
)


def get_formatted_today() -> str:
    """Returns formatted date matching UAE invoice style: e.g. 04th Sep 2026."""
    now = datetime.now()
    d = now.day
    if 11 <= (d % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(d % 10, "th")
    return f"{d:02d}{suffix} {now.strftime('%b %Y')}"


class NativeItemRow:
    """Represents an interactive table row using native Tkinter widgets."""
    def __init__(self, parent_frame, row_index: int, on_change_callback, on_delete_callback, on_move_callback):
        self.parent = parent_frame
        self.index = row_index
        self.on_change = on_change_callback
        self.on_delete = on_delete_callback
        self.on_move = on_move_callback

        # S# Label
        self.lbl_sno = ttk.Label(parent_frame, text=f"{self.index}.", font=("Segoe UI", 9, "bold"), width=3)

        # Description Entry
        self.var_desc = tk.StringVar(value="")
        self.entry_desc = ttk.Entry(parent_frame, textvariable=self.var_desc, font=("Segoe UI", 9))

        # Quantity Entry
        self.var_qty = tk.StringVar(value="1")
        self.var_qty.trace_add("write", lambda *args: self.recalculate())
        self.entry_qty = ttk.Entry(parent_frame, textvariable=self.var_qty, width=6, justify="center", font=("Segoe UI", 9))

        # Unit Rate Entry
        self.var_unit = tk.StringVar(value="0.00")
        self.var_unit.trace_add("write", lambda *args: self.recalculate())
        self.entry_unit = ttk.Entry(parent_frame, textvariable=self.var_unit, width=11, justify="right", font=("Segoe UI", 9))
        self.entry_unit.bind("<FocusOut>", self._format_unit_on_blur)

        # VAT Checkbox ("5% VAT")
        self.var_vat = tk.BooleanVar(value=False)
        self.chk_vat = ttk.Checkbutton(parent_frame, text="5% VAT", variable=self.var_vat, command=self.recalculate)

        # VAT Amount Label
        self.lbl_vat_amt = ttk.Label(parent_frame, text="0.00", width=9, anchor="e", font=("Segoe UI", 9))

        # Line Total Label
        self.lbl_line_total = ttk.Label(parent_frame, text="0.00", width=11, anchor="e", font=("Segoe UI", 9, "bold"))

        # Action Buttons frame
        self.btn_frame = ttk.Frame(parent_frame)
        self.btn_up = ttk.Button(self.btn_frame, text="▲", width=3, command=lambda: self.on_move(self, -1))
        self.btn_up.pack(side="left", padx=1)
        self.btn_down = ttk.Button(self.btn_frame, text="▼", width=3, command=lambda: self.on_move(self, 1))
        self.btn_down.pack(side="left", padx=1)
        self.btn_del = ttk.Button(self.btn_frame, text="✕", width=3, command=lambda: self.on_delete(self))
        self.btn_del.pack(side="left", padx=1)

    def grid(self, row_num: int):
        self.lbl_sno.grid(row=row_num, column=0, padx=3, pady=2, sticky="w")
        self.entry_desc.grid(row=row_num, column=1, padx=3, pady=2, sticky="ew")
        self.entry_qty.grid(row=row_num, column=2, padx=3, pady=2)
        self.entry_unit.grid(row=row_num, column=3, padx=3, pady=2)
        self.chk_vat.grid(row=row_num, column=4, padx=6, pady=2)
        self.lbl_vat_amt.grid(row=row_num, column=5, padx=3, pady=2, sticky="e")
        self.lbl_line_total.grid(row=row_num, column=6, padx=3, pady=2, sticky="e")
        self.btn_frame.grid(row=row_num, column=7, padx=3, pady=2)

    def destroy(self):
        self.lbl_sno.destroy()
        self.entry_desc.destroy()
        self.entry_qty.destroy()
        self.entry_unit.destroy()
        self.chk_vat.destroy()
        self.lbl_vat_amt.destroy()
        self.lbl_line_total.destroy()
        self.btn_frame.destroy()

    def set_index(self, idx: int):
        self.index = idx
        self.lbl_sno.configure(text=f"{self.index}.")

    def _format_unit_on_blur(self, event=None):
        amt = self.get_unit_amount()
        self.var_unit.set(f"{amt:,.2f}")

    def set_values(self, desc: str, qty: str, unit: str, vat: bool):
        self.var_desc.set(desc)
        self.var_qty.set(qty)
        try:
            val = float(str(unit).replace(",", "").strip() or 0)
            self.var_unit.set(f"{val:,.2f}")
        except ValueError:
            self.var_unit.set(str(unit))
        self.var_vat.set(vat)
        self.recalculate()

    def get_quantity(self) -> float:
        try:
            return float(self.var_qty.get().strip() or 0)
        except ValueError:
            return 0.0

    def get_unit_amount(self) -> float:
        try:
            return float(self.var_unit.get().strip().replace(",", "") or 0)
        except ValueError:
            return 0.0

    def get_vat_amount(self) -> float:
        if self.var_vat.get():
            return round(self.get_quantity() * self.get_unit_amount() * 0.05, 2)
        return 0.00

    def get_line_total(self) -> float:
        sub = self.get_quantity() * self.get_unit_amount()
        return round(sub + self.get_vat_amount(), 2)

    def recalculate(self):
        vat = self.get_vat_amount()
        tot = self.get_line_total()
        self.lbl_vat_amt.configure(text=f"{vat:,.2f}")
        self.lbl_line_total.configure(text=f"{tot:,.2f}")
        self.on_change()

    def to_dict(self) -> Dict[str, Any]:
        qty = self.get_quantity()
        return {
            "description": self.var_desc.get().strip(),
            "quantity": int(qty) if qty.is_integer() else qty,
            "unit_amount": self.get_unit_amount(),
            "vat_applicable": self.var_vat.get(),
            "vat_amount": self.get_vat_amount(),
            "line_total": self.get_line_total()
        }


class NativeInvoiceApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(f"Silver Premium - Official Tax Invoice Generator v{APP_VERSION}")
        self.geometry("1040x680")
        self.minsize(880, 480)

        # Set Window Icon
        ico_path = get_asset_path("app_icon.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass

        # Native style
        self.style = ttk.Style(self)
        try:
            available = self.style.theme_names()
            if "vista" in available:
                self.style.theme_use("vista")
            elif "clam" in available:
                self.style.theme_use("clam")
        except Exception:
            pass

        # Refined style padding for smoother visual touch
        try:
            self.style.configure("TButton", font=("Segoe UI", 9), padding=(6, 3))
            self.style.configure("Primary.TButton", font=("Segoe UI", 9, "bold"), padding=(8, 4))
            self.style.configure("TLabelframe.Label", font=("Segoe UI", 9, "bold"))
            self.style.configure("Treeview", font=("Segoe UI", 9), rowheight=28)
            self.style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), padding=(4, 4))
        except Exception:
            pass

        self._words_timer = None
        self.settings = load_settings()
        self.item_rows: List[NativeItemRow] = []

        self._build_ui()
        # Auto-discover and migrate records from previous versions / locations
        migrated, total_rec = check_and_run_startup_migration()
        self._load_next_sequence_and_defaults()
        self._recalculate_all()
        if total_rec > 0:
            self.lbl_status.configure(
                text=f"✓ Silver Premium v{APP_VERSION} ready. {total_rec} invoices synchronized.",
                foreground="#047857"
            )
        center_window(self, width=1040, height=680)

    def _build_ui(self):
        # =========================================================================
        # 1. PINNED TOP TOOLBAR (Always at top, never scrolled away)
        # =========================================================================
        top_bar = ttk.Frame(self, padding=(12, 10))
        top_bar.pack(fill="x", side="top")

        # Brand / Identity (Left side: 2-line clean layout)
        brand_frame = ttk.Frame(top_bar)
        brand_frame.pack(side="left", fill="y")

        lbl_app = ttk.Label(
            brand_frame,
            text="SILVER PREMIUM TAX INVOICE",
            font=("Segoe UI", 12, "bold"),
            foreground="#1E3A8A"
        )
        lbl_app.pack(anchor="w")

        lbl_trn = ttk.Label(
            brand_frame,
            text="TRN: 104171277700003",
            font=("Segoe UI", 8, "bold"),
            foreground="#64748B"
        )
        lbl_trn.pack(anchor="w", pady=(1, 0))

        # Action Toolbar (Right side: natural order with auto-sizing)
        tool_frame = ttk.Frame(top_bar)
        tool_frame.pack(side="right")

        btn_new = ttk.Button(tool_frame, text="New Invoice", command=self._on_new_invoice)
        btn_new.pack(side="left", padx=(0, 4))

        btn_customers = ttk.Button(tool_frame, text="Customers", command=self._open_customers)
        btn_customers.pack(side="left", padx=4)

        btn_history = ttk.Button(tool_frame, text="📋 History & VAT", command=self._open_history)
        btn_history.pack(side="left", padx=4)

        btn_company_vat = ttk.Button(tool_frame, text="📊 Company VAT", command=self._open_company_vat)
        btn_company_vat.pack(side="left", padx=4)

        btn_folder = ttk.Button(tool_frame, text="Invoices Folder", command=open_invoices_folder)
        btn_folder.pack(side="left", padx=4)

        btn_updates = ttk.Button(tool_frame, text="🔄 Updates & Data", command=self._open_updater)
        btn_updates.pack(side="left", padx=4)

        btn_settings = ttk.Button(tool_frame, text="Settings", command=self._open_settings)
        btn_settings.pack(side="left", padx=(4, 0))

        # Top separator
        ttk.Separator(self, orient="horizontal").pack(fill="x", side="top")

        # =========================================================================
        # 2. PINNED BOTTOM ACTION BAR (Packed side='bottom' FIRST so it is NEVER lost)
        # =========================================================================
        bottom_bar = ttk.Frame(self, padding=(10, 8))
        bottom_bar.pack(fill="x", side="bottom")

        # Bottom separator
        ttk.Separator(self, orient="horizontal").pack(fill="x", side="bottom")

        # Right Action Buttons
        btn_generate = ttk.Button(
            bottom_bar,
            text="Generate Invoice",
            command=self._on_generate_invoice,
            style="Primary.TButton"
        )
        btn_generate.pack(side="right", padx=(6, 0))

        btn_preview = ttk.Button(
            bottom_bar,
            text="Preview PDF",
            command=self._on_preview_pdf
        )
        btn_preview.pack(side="right", padx=(4, 0))

        btn_save_copy = ttk.Button(
            bottom_bar,
            text="Save Copy As...",
            command=self._on_save_copy_as
        )
        btn_save_copy.pack(side="right", padx=(4, 0))

        # Left status text
        self.lbl_status = ttk.Label(
            bottom_bar,
            text="Ready. Press 'Generate Invoice' to save into Invoices folder.",
            font=("Segoe UI", 9),
            foreground="#475569"
        )
        self.lbl_status.pack(side="left", fill="x", expand=True)

        # =========================================================================
        # 3. SCROLLABLE MIDDLE WORKSPACE
        # =========================================================================
        main_container = ttk.Frame(self)
        main_container.pack(fill="both", expand=True)

        self.main_canvas = tk.Canvas(main_container, highlightthickness=0)
        self.main_vscroll = ttk.Scrollbar(main_container, orient="vertical", command=self.main_canvas.yview)
        self.scroll_content = ttk.Frame(self.main_canvas, padding=(10, 8))

        self.scroll_content.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )
        self.canvas_window = self.main_canvas.create_window((0, 0), window=self.scroll_content, anchor="nw")
        self.main_canvas.bind(
            "<Configure>",
            lambda e: self.main_canvas.itemconfig(self.canvas_window, width=e.width)
        )
        self.main_canvas.configure(yscrollcommand=self.main_vscroll.set)

        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.main_vscroll.pack(side="right", fill="y")

        # Smooth Global Mousewheel binding
        self.bind_all("<MouseWheel>", self._on_mousewheel)

        # -----------------------------------------------------------------
        # Inside Scrollable Content:
        # -----------------------------------------------------------------

        # Section A: Customer & Invoice Metadata Cards
        meta_frame = ttk.Frame(self.scroll_content)
        meta_frame.pack(fill="x", pady=(0, 8))
        meta_frame.grid_columnconfigure(0, weight=1)
        meta_frame.grid_columnconfigure(1, weight=1)

        # Left Box: Customer Info
        box_cust = ttk.LabelFrame(meta_frame, text=" Customer Information ", padding=8)
        box_cust.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        # Row 0: Quick Profile Selection Dropdown & Controls
        ttk.Label(box_cust, text="Saved Profile:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=2)
        cust_sel_frame = ttk.Frame(box_cust)
        cust_sel_frame.grid(row=0, column=1, sticky="ew", pady=2, padx=(6, 0))

        self.var_cust_dropdown = tk.StringVar()
        self.combo_cust = ttk.Combobox(
            cust_sel_frame,
            textvariable=self.var_cust_dropdown,
            state="readonly",
            font=("Segoe UI", 9)
        )
        self.combo_cust.pack(side="left", fill="x", expand=True)
        self.combo_cust.bind("<<ComboboxSelected>>", self._on_customer_selected)

        btn_quick_save = ttk.Button(
            cust_sel_frame,
            text="Save Profile",
            command=self._on_save_customer_profile
        )
        btn_quick_save.pack(side="left", padx=(4, 0))

        btn_manage = ttk.Button(
            cust_sel_frame,
            text="Profiles...",
            command=self._open_customers
        )
        btn_manage.pack(side="left", padx=(3, 0))

        btn_profile_vat = ttk.Button(
            cust_sel_frame,
            text="📊 Profile VAT",
            command=self._on_view_active_customer_vat
        )
        btn_profile_vat.pack(side="left", padx=(3, 0))

        ttk.Label(box_cust, text="Company Name:").grid(row=1, column=0, sticky="w", pady=2)
        self.entry_cust_company = ttk.Entry(box_cust, font=("Segoe UI", 9))
        self.entry_cust_company.grid(row=1, column=1, sticky="ew", pady=2, padx=(6, 0))

        ttk.Label(box_cust, text="Address / City:").grid(row=2, column=0, sticky="w", pady=2)
        self.entry_cust_address = ttk.Entry(box_cust, font=("Segoe UI", 9))
        self.entry_cust_address.grid(row=2, column=1, sticky="ew", pady=2, padx=(6, 0))

        ttk.Label(box_cust, text="Customer TRN:").grid(row=3, column=0, sticky="w", pady=2)
        self.entry_cust_trn = ttk.Entry(box_cust, font=("Segoe UI", 9))
        self.entry_cust_trn.grid(row=3, column=1, sticky="ew", pady=2, padx=(6, 0))

        box_cust.grid_columnconfigure(1, weight=1)

        # Right Box: Invoice Details
        box_inv = ttk.LabelFrame(meta_frame, text=" Invoice Details & Client ", padding=8)
        box_inv.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        ttk.Label(box_inv, text="Invoice Number:").grid(row=0, column=0, sticky="w", pady=2)
        inv_row = ttk.Frame(box_inv)
        inv_row.grid(row=0, column=1, sticky="ew", pady=2, padx=(6, 0))

        self.var_invoice_no = tk.StringVar()
        self.entry_inv_no = ttk.Entry(inv_row, textvariable=self.var_invoice_no, font=("Segoe UI", 9, "bold"), width=14)
        self.entry_inv_no.pack(side="left")

        lbl_seq_hint = ttk.Label(inv_row, text="(Auto +1)", font=("Segoe UI", 8), foreground="#64748B")
        lbl_seq_hint.pack(side="left", padx=(6, 0))

        ttk.Label(box_inv, text="Invoice Date:").grid(row=1, column=0, sticky="w", pady=2)
        date_row = ttk.Frame(box_inv)
        date_row.grid(row=1, column=1, sticky="ew", pady=2, padx=(6, 0))

        self.var_date = tk.StringVar(value=get_formatted_today())
        self.entry_date = ttk.Entry(date_row, textvariable=self.var_date, font=("Segoe UI", 9), width=15)
        self.entry_date.pack(side="left")

        btn_today = ttk.Button(date_row, text="Today", width=5, command=lambda: self.var_date.set(get_formatted_today()))
        btn_today.pack(side="left", padx=(4, 0))

        ttk.Label(box_inv, text="Client Reference:").grid(row=2, column=0, sticky="w", pady=2)
        self.entry_client_name = ttk.Entry(box_inv, font=("Segoe UI", 9))
        self.entry_client_name.grid(row=2, column=1, sticky="ew", pady=2, padx=(6, 0))

        lbl_profile_tip = ttk.Label(
            box_inv,
            text="Tip: Pick repeat customers from the profile list.",
            font=("Segoe UI", 8),
            foreground="#64748B"
        )
        lbl_profile_tip.grid(row=3, column=1, sticky="w", pady=2, padx=(6, 0))

        box_inv.grid_columnconfigure(1, weight=1)

        # Section B: Line Items Table Frame
        items_frame = ttk.LabelFrame(self.scroll_content, text=" Itemized Table ", padding=6)
        items_frame.pack(fill="x", pady=(0, 6))

        # Table Control Buttons
        items_ctl_bar = ttk.Frame(items_frame)
        items_ctl_bar.pack(fill="x", pady=(0, 4))

        btn_add = ttk.Button(items_ctl_bar, text="+ Add Line Item", command=self.add_empty_row)
        btn_add.pack(side="left")

        btn_sample = ttk.Button(items_ctl_bar, text="Load Sample Items", command=self.load_reference_sample)
        btn_sample.pack(side="left", padx=(6, 0))

        btn_clear = ttk.Button(items_ctl_bar, text="Clear Items", command=self._clear_rows)
        btn_clear.pack(side="right")

        # Table Column Headers Bar
        tbl_hdr = ttk.Frame(items_frame, padding=(2, 2))
        tbl_hdr.pack(fill="x")
        tbl_hdr.grid_columnconfigure(1, weight=1)

        h_font = ("Segoe UI", 9, "bold")
        ttk.Label(tbl_hdr, text="S#", width=3, font=h_font).grid(row=0, column=0, padx=3, sticky="w")
        ttk.Label(tbl_hdr, text="Description", font=h_font).grid(row=0, column=1, padx=3, sticky="w")
        ttk.Label(tbl_hdr, text="Quantity", width=6, font=h_font, anchor="center").grid(row=0, column=2, padx=3)
        ttk.Label(tbl_hdr, text="Unit (AED)", width=10, font=h_font, anchor="e").grid(row=0, column=3, padx=3)
        ttk.Label(tbl_hdr, text="VAT", width=8, font=h_font, anchor="center").grid(row=0, column=4, padx=6)
        ttk.Label(tbl_hdr, text="VAT Amt", width=9, font=h_font, anchor="e").grid(row=0, column=5, padx=3)
        ttk.Label(tbl_hdr, text="Total (AED)", width=11, font=h_font, anchor="e").grid(row=0, column=6, padx=3)
        ttk.Label(tbl_hdr, text="Actions", width=10, font=h_font, anchor="center").grid(row=0, column=7, padx=3)

        ttk.Separator(items_frame, orient="horizontal").pack(fill="x", pady=2)

        # Dynamic Rows Grid Frame
        self.rows_inner = ttk.Frame(items_frame)
        self.rows_inner.pack(fill="x", pady=(2, 4))
        self.rows_inner.grid_columnconfigure(1, weight=1)

        # Section C: Totals & Currency in Words
        totals_frame = ttk.LabelFrame(self.scroll_content, text=" Financial Totals & Summary ", padding=6)
        totals_frame.pack(fill="x", pady=(0, 6))

        # Words Banner
        words_box = ttk.Frame(totals_frame, padding=4)
        words_box.pack(fill="x", pady=(0, 2))

        ttk.Label(words_box, text="AMOUNT IN WORDS (AED):", font=("Segoe UI", 8, "bold"), foreground="#475569").pack(anchor="w")
        self.lbl_words = ttk.Label(
            words_box,
            text="AED ZERO & ZERO FILS ONLY",
            font=("Segoe UI", 10, "bold"),
            foreground="#1E3A8A",
            wraplength=850
        )
        self.lbl_words.pack(anchor="w", pady=(1, 0))

        # Summary line
        sum_row = ttk.Frame(totals_frame, padding=2)
        sum_row.pack(fill="x")

        b = self.settings.get("bank", {})
        self.lbl_bank_summary = ttk.Label(
            sum_row,
            text=f"Bank: {b.get('bank_name', 'WIO BUSINESS')} | A/C: {b.get('account_no', '9895248605')} | IBAN: {b.get('iban', '')}",
            font=("Segoe UI", 8),
            foreground="#64748B"
        )
        self.lbl_bank_summary.pack(side="left")

        self.lbl_grand_total = ttk.Label(sum_row, text="Grand Total: AED 0.00", font=("Segoe UI", 12, "bold"), foreground="#047857")
        self.lbl_grand_total.pack(side="right", padx=(14, 0))

        self.lbl_vat_total = ttk.Label(sum_row, text="VAT 5%: AED 0.00", font=("Segoe UI", 10, "bold"), foreground="#B45309")
        self.lbl_vat_total.pack(side="right", padx=(14, 0))

        self.lbl_subtotal = ttk.Label(sum_row, text="Subtotal: AED 0.00", font=("Segoe UI", 10, "bold"))
        self.lbl_subtotal.pack(side="right")

    def _on_mousewheel(self, event):
        try:
            if hasattr(self, "main_canvas") and self.main_canvas.winfo_exists():
                self.main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    # -----------------------------------------------------------------
    # Logic & Handlers
    # -----------------------------------------------------------------
    def _load_next_sequence_and_defaults(self):
        next_seq = get_next_sequential_number(102630)
        self.var_invoice_no.set(str(next_seq))

        defs = self.settings.get("defaults", {})
        self.entry_client_name.delete(0, "end")
        self.entry_client_name.insert(0, defs.get("client_name", ""))

        self.entry_cust_company.delete(0, "end")
        self.entry_cust_company.insert(0, defs.get("customer_company", "Customer Company Name"))

        self.entry_cust_address.delete(0, "end")
        self.entry_cust_address.insert(0, defs.get("customer_address", "Dubai, United Arab Emirates"))

        self.entry_cust_trn.delete(0, "end")
        self.entry_cust_trn.insert(0, defs.get("customer_trn", ""))

        self._refresh_customer_dropdown()
        self.load_reference_sample()

    def add_empty_row(self) -> NativeItemRow:
        idx = len(self.item_rows) + 1
        row = NativeItemRow(
            parent_frame=self.rows_inner,
            row_index=idx,
            on_change_callback=self._recalculate_all,
            on_delete_callback=self._delete_row,
            on_move_callback=self._move_row
        )
        row.grid(row_num=idx)
        self.item_rows.append(row)
        self._recalculate_all()
        return row

    def load_reference_sample(self):
        self._clear_rows(confirm=False)
        r1 = self.add_empty_row()
        r1.set_values("Professional Document Clearing Services", "1", "5,500.00", False)

        r2 = self.add_empty_row()
        r2.set_values("Urgency / Government Processing Fees", "1", "200.00", True)

        r3 = self.add_empty_row()
        r3.set_values("Attestation & Delivery Charges", "1", "25.00", True)

    def _delete_row(self, row: NativeItemRow):
        if len(self.item_rows) <= 1:
            messagebox.showwarning("Notice", "An invoice must have at least one line item row.")
            return
        row.destroy()
        self.item_rows.remove(row)
        self._regrid_rows()
        self._recalculate_all()

    def _move_row(self, row: NativeItemRow, direction: int):
        idx = self.item_rows.index(row)
        target = idx + direction
        if 0 <= target < len(self.item_rows):
            self.item_rows[idx], self.item_rows[target] = self.item_rows[target], self.item_rows[idx]
            self._regrid_rows()
            self._recalculate_all()

    def _regrid_rows(self):
        for idx, r in enumerate(self.item_rows, start=1):
            r.set_index(idx)
            r.grid(row_num=idx)

    def _clear_rows(self, confirm: bool = True):
        if confirm and not messagebox.askyesno("Confirm", "Clear all item rows?"):
            return
        for r in self.item_rows:
            r.destroy()
        self.item_rows.clear()
        if confirm:
            self.add_empty_row()

    def _recalculate_all(self):
        subtotal = sum(r.get_quantity() * r.get_unit_amount() for r in self.item_rows)
        vat_total = sum(r.get_vat_amount() for r in self.item_rows)
        subtotal = round(subtotal, 2)
        vat_total = round(vat_total, 2)
        grand_total = round(subtotal + vat_total, 2)

        self.lbl_subtotal.configure(text=f"Subtotal: AED {subtotal:,.2f}")
        self.lbl_vat_total.configure(text=f"VAT 5%: AED {vat_total:,.2f}")
        self.lbl_grand_total.configure(text=f"Grand Total: AED {grand_total:,.2f}")

        # Debounce the words calculation slightly so numeric typing is completely fluid and lag-free
        if hasattr(self, "_words_timer") and self._words_timer:
            self.after_cancel(self._words_timer)
        self._words_timer = self.after(80, lambda: self._update_words(grand_total))

    def _update_words(self, grand_total: float):
        try:
            words = amount_to_aed_words(grand_total)
            if hasattr(self, "lbl_words") and self.lbl_words.winfo_exists():
                self.lbl_words.configure(text=words)
        except Exception:
            pass

    def _get_invoice_data(self) -> Dict[str, Any]:
        subtotal = round(sum(r.get_quantity() * r.get_unit_amount() for r in self.item_rows), 2)
        vat_total = round(sum(r.get_vat_amount() for r in self.item_rows), 2)
        grand_total = round(subtotal + vat_total, 2)
        words = amount_to_aed_words(grand_total)

        return {
            "invoice_no": self.var_invoice_no.get().strip() or "102630",
            "date": self.var_date.get().strip() or get_formatted_today(),
            "client_name": self.entry_client_name.get().strip(),
            "company": self.settings.get("company", {}),
            "customer": {
                "company_name": self.entry_cust_company.get().strip(),
                "address": self.entry_cust_address.get().strip(),
                "trn": self.entry_cust_trn.get().strip()
            },
            "bank": self.settings.get("bank", {}),
            "items": [r.to_dict() for r in self.item_rows],
            "subtotal": subtotal,
            "vat_total": vat_total,
            "grand_total": grand_total,
            "amount_in_words": words,
            "terms": self.settings.get("terms", [])
        }

    def _on_generate_invoice(self):
        data = self._get_invoice_data()
        inv_no = data["invoice_no"]
        client = data["client_name"]

        filename = get_standard_pdf_filename(inv_no, client)
        target_path = os.path.join(get_invoices_dir(), filename)

        try:
            generate_invoice_pdf(data, target_path)

            record_new_invoice(
                invoice_no=inv_no,
                date_str=data["date"],
                client_name=client,
                customer_company=data["customer"]["company_name"],
                subtotal=data["subtotal"],
                vat_total=data["vat_total"],
                grand_total=data["grand_total"],
                pdf_filename=filename
            )

            next_seq = get_next_sequential_number(102630)
            self.var_invoice_no.set(str(next_seq))

            # Auto-save or update customer profile if company name is entered
            cust_comp = data["customer"]["company_name"]
            if cust_comp:
                save_or_update_customer({
                    "company_name": cust_comp,
                    "client_name": client,
                    "address": data["customer"]["address"],
                    "trn": data["customer"]["trn"]
                })
                self._refresh_customer_dropdown(select_name=cust_comp)

            open_pdf_file(target_path)

            self.lbl_status.configure(
                text=f"✓ Saved '{filename}' to Invoices folder. Next invoice is #{next_seq}.",
                foreground="#047857"
            )

        except Exception as e:
            messagebox.showerror("Generation Error", f"Failed to create invoice:\n{e}")

    def _refresh_customer_dropdown(self, select_name: Optional[str] = None):
        customers = load_customers()
        names = [c.get("company_name", "").strip() for c in customers if c.get("company_name")]
        self.combo_cust["values"] = names

        current = select_name or self.var_cust_dropdown.get().strip()
        if current in names:
            self.var_cust_dropdown.set(current)
        elif names and not current:
            self.var_cust_dropdown.set(names[0])

    def _on_customer_selected(self, event=None):
        selected_name = self.var_cust_dropdown.get().strip()
        if not selected_name:
            return
        cust = get_customer_by_name(selected_name)
        if cust:
            self._apply_customer_data(cust)

    def _apply_customer_data(self, cust: Dict[str, Any]):
        comp = cust.get("company_name", "").strip()
        self.entry_cust_company.delete(0, "end")
        self.entry_cust_company.insert(0, comp)

        self.entry_cust_address.delete(0, "end")
        self.entry_cust_address.insert(0, cust.get("address", ""))

        self.entry_cust_trn.delete(0, "end")
        self.entry_cust_trn.insert(0, cust.get("trn", ""))

        client = cust.get("client_name", "").strip()
        if client:
            self.entry_client_name.delete(0, "end")
            self.entry_client_name.insert(0, client)

        # Sync dropdown
        self._refresh_customer_dropdown(select_name=comp)

        self.lbl_status.configure(
            text=f"✓ Loaded customer profile: {comp}",
            foreground="#047857"
        )

    def _on_save_customer_profile(self):
        comp = self.entry_cust_company.get().strip()
        if not comp:
            messagebox.showwarning("Notice", "Please enter a Company Name to save as a customer profile.")
            self.entry_cust_company.focus_set()
            return

        cust_data = {
            "company_name": comp,
            "client_name": self.entry_client_name.get().strip(),
            "address": self.entry_cust_address.get().strip(),
            "trn": self.entry_cust_trn.get().strip()
        }

        save_or_update_customer(cust_data)
        self._refresh_customer_dropdown(select_name=comp)
        self.lbl_status.configure(
            text=f"✓ Customer profile '{comp}' saved and ready for selection.",
            foreground="#047857"
        )
        messagebox.showinfo("Profile Saved", f"Customer profile for:\n\n{comp}\n\nhas been saved successfully!")

    def _open_customers(self):
        prefill = {
            "company_name": self.entry_cust_company.get().strip(),
            "client_name": self.entry_client_name.get().strip(),
            "address": self.entry_cust_address.get().strip(),
            "trn": self.entry_cust_trn.get().strip()
        }
        CustomerProfilesDialog(
            self,
            on_select_customer=self._apply_customer_data,
            on_data_changed=self._refresh_customer_dropdown,
            prefill_data=prefill if prefill["company_name"] else None
        )

    def _on_preview_pdf(self):
        data = self._get_invoice_data()
        temp_path = os.path.join(get_invoices_dir(), f"_preview_{data['invoice_no']}.pdf")
        try:
            generate_invoice_pdf(data, temp_path)
            open_pdf_file(temp_path)
        except Exception as e:
            messagebox.showerror("Preview Error", f"Could not generate preview:\n{e}")

    def _on_save_copy_as(self):
        data = self._get_invoice_data()
        init_file = get_standard_pdf_filename(data["invoice_no"], data["client_name"])
        target = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".pdf",
            filetypes=[("PDF Documents", "*.pdf")],
            initialfile=init_file,
            title="Save Copy of Invoice"
        )
        if target:
            try:
                generate_invoice_pdf(data, target)
                messagebox.showinfo("Saved", f"Invoice copy saved to:\n{target}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save copy:\n{e}")

    def _on_new_invoice(self):
        next_seq = get_next_sequential_number(102630)
        self.var_invoice_no.set(str(next_seq))
        self.var_date.set(get_formatted_today())
        self.entry_client_name.delete(0, "end")
        self.load_reference_sample()
        self.lbl_status.configure(
            text=f"Ready for new invoice #{next_seq}.",
            foreground="#475569"
        )

    def _open_history(self, initial_company: str = "", initial_tab: int = 0):
        HistoryDialog(
            self,
            on_records_changed=self._on_history_records_deleted,
            initial_company=initial_company,
            initial_tab=initial_tab
        )

    def _open_company_vat(self):
        HistoryDialog(
            self,
            on_records_changed=self._on_history_records_deleted,
            initial_tab=1
        )

    def _on_view_active_customer_vat(self):
        comp = self.entry_cust_company.get().strip()
        if not comp and hasattr(self, 'var_cust_dropdown'):
            comp = self.var_cust_dropdown.get().strip()
        HistoryDialog(
            self,
            on_records_changed=self._on_history_records_deleted,
            initial_company=comp,
            initial_tab=0 if comp else 1
        )

    def _on_history_records_deleted(self, deleted_invoice_no: str):
        next_seq = get_next_sequential_number(102630)
        self.var_invoice_no.set(str(next_seq))
        self.lbl_status.configure(
            text=f"✓ Invoice #{deleted_invoice_no} deleted from history. Active invoice # set to {next_seq}.",
            foreground="#047857"
        )

    def _open_updater(self):
        UpdaterDialog(self, on_data_updated=self._on_data_updated_from_migration)

    def _on_data_updated_from_migration(self):
        self._refresh_customer_dropdown()
        self._load_next_sequence_and_defaults()
        self.lbl_status.configure(
            text="✓ Invoices & Customer database updated from migration.",
            foreground="#047857"
        )

    def _open_settings(self):
        NativeSettingsDialog(self, on_save_callback=self._on_settings_saved)

    def _on_settings_saved(self):
        self.settings = load_settings()
        b = self.settings.get("bank", {})
        self.lbl_bank_summary.configure(
            text=f"Bank: {b.get('bank_name', 'WIO BUSINESS')} | A/C: {b.get('account_no', '9895248605')} | IBAN: {b.get('iban', '')}"
        )


if __name__ == "__main__":
    app = NativeInvoiceApp()
    app.mainloop()
