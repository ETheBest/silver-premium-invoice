"""
Main Application Window
Silver Premium Tax Invoice Generator
Built with CustomTkinter.
"""
import os
import sys
from datetime import datetime
from PIL import Image
import customtkinter as ctk
from tkinter import filedialog, messagebox
from typing import List, Dict, Any

from core.settings_manager import (
    load_settings,
    save_settings,
    get_next_invoice_number,
    increment_invoice_number
)
from core.num_to_words_helper import amount_to_aed_words
from core.pdf_engine import generate_invoice_pdf, get_asset_path
from gui.item_row import ItemRow
from gui.preview_dialog import PreviewDialog
from gui.settings_dialog import SettingsDialog


def get_formatted_today_date() -> str:
    """Returns today's date formatted as 04th Sep 2026."""
    now = datetime.now()
    day = now.day
    if 11 <= (day % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day:02d}{suffix} {now.strftime('%b %Y')}"


class InvoiceApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Appearance & Theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Silver Premium - Official Tax Invoice Generator")
        self.geometry("1120x860")
        self.minsize(980, 720)

        # Set App Icon if available
        ico_path = get_asset_path("app_icon.ico")
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(ico_path)
            except Exception:
                pass

        self.settings = load_settings()
        self.item_rows: List[ItemRow] = []

        self._build_ui()
        self._load_initial_defaults()
        self.recalculate_totals()

    def _build_ui(self):
        # 1. Top Application Bar
        top_bar = ctk.CTkFrame(self, height=65, corner_radius=0, fg_color="#0F172A")
        top_bar.pack(fill="x", side="top")

        # Logo / Branding
        logo_path = get_asset_path("logo.png")
        if os.path.exists(logo_path):
            try:
                raw_logo = Image.open(logo_path)
                ratio = raw_logo.width / raw_logo.height
                logo_h = 38
                logo_w = int(logo_h * ratio)
                ctk_logo = ctk.CTkImage(light_image=raw_logo, dark_image=raw_logo, size=(logo_w, logo_h))
                lbl_logo = ctk.CTkLabel(top_bar, image=ctk_logo, text="")
                lbl_logo.pack(side="left", padx=(18, 10), pady=10)
            except Exception:
                pass

        # Title block
        title_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        title_frame.pack(side="left", padx=4, pady=8)

        lbl_title = ctk.CTkLabel(
            title_frame,
            text="SILVER PREMIUM TAX INVOICE GENERATOR",
            font=ctk.CTkFont(family="Arial", size=15, weight="bold"),
            text_color="#F8FAFC"
        )
        lbl_title.pack(anchor="w")

        lbl_subtitle = ctk.CTkLabel(
            title_frame,
            text="TRN: 104171277700003 | Pixel-Perfect PDF Export",
            font=ctk.CTkFont(family="Arial", size=11),
            text_color="#94A3B8"
        )
        lbl_subtitle.pack(anchor="w")

        # Top Bar Right Controls
        btn_theme = ctk.CTkButton(
            top_bar,
            text="🌓 Theme",
            width=80,
            height=32,
            fg_color="#334155",
            hover_color="#475569",
            command=self._toggle_theme
        )
        btn_theme.pack(side="right", padx=16, pady=16)

        btn_settings = ctk.CTkButton(
            top_bar,
            text="⚙️ Defaults",
            width=95,
            height=32,
            fg_color="#334155",
            hover_color="#475569",
            command=self._open_settings
        )
        btn_settings.pack(side="right", padx=6, pady=16)

        btn_reset = ctk.CTkButton(
            top_bar,
            text="🔄 New Invoice",
            width=110,
            height=32,
            fg_color="#3B82F6",
            hover_color="#2563EB",
            font=ctk.CTkFont(weight="bold"),
            command=self._on_new_invoice
        )
        btn_reset.pack(side="right", padx=6, pady=16)

        # Main Scrollable Content Container
        self.main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_scroll.pack(fill="both", expand=True, padx=16, pady=(10, 5))

        # 2. Section 1: Customer & Invoice Metadata Card
        self._build_metadata_card()

        # 3. Section 2: Dynamic Line Items Card
        self._build_items_card()

        # 4. Section 3: Financial Summary & Amount in Words Card
        self._build_financial_summary_card()

        # 5. Bottom Sticky Action Bar
        self._build_bottom_action_bar()

    def _build_metadata_card(self):
        card = ctk.CTkFrame(self.main_scroll, corner_radius=8, fg_color="#1E293B")
        card.pack(fill="x", pady=(0, 10))

        # Card Title
        lbl_card = ctk.CTkLabel(
            card,
            text="👤 Customer & Invoice Header Details",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38BDF8"
        )
        lbl_card.pack(anchor="w", padx=14, pady=(10, 6))

        content_grid = ctk.CTkFrame(card, fg_color="transparent")
        content_grid.pack(fill="x", padx=14, pady=(0, 12))
        content_grid.grid_columnconfigure(0, weight=1)
        content_grid.grid_columnconfigure(1, weight=1)

        # Left Column: Customer Entity Details
        left_box = ctk.CTkFrame(content_grid, fg_color="#0F172A", corner_radius=6)
        left_box.grid(row=0, column=0, padx=(0, 8), sticky="nsew", pady=4)

        ctk.CTkLabel(left_box, text="Customer Company Name:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(8, 2))
        self.entry_cust_company = ctk.CTkEntry(left_box, placeholder_text="e.g. Petro Gulf Refined Oil Products Trading L.L.C")
        self.entry_cust_company.pack(fill="x", padx=10, pady=(0, 6))

        ctk.CTkLabel(left_box, text="Customer Address / Location:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(2, 2))
        self.entry_cust_address = ctk.CTkEntry(left_box, placeholder_text="e.g. Business Bay, Dubai")
        self.entry_cust_address.pack(fill="x", padx=10, pady=(0, 6))

        ctk.CTkLabel(left_box, text="Customer TRN:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(2, 2))
        self.entry_cust_trn = ctk.CTkEntry(left_box, placeholder_text="e.g. 100459434500003")
        self.entry_cust_trn.pack(fill="x", padx=10, pady=(0, 10))

        # Right Column: Invoice Metadata
        right_box = ctk.CTkFrame(content_grid, fg_color="#0F172A", corner_radius=6)
        right_box.grid(row=0, column=1, padx=(8, 0), sticky="nsew", pady=4)

        # Row 1: Invoice # and Date
        r1 = ctk.CTkFrame(right_box, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=(8, 6))
        r1.grid_columnconfigure(0, weight=1)
        r1.grid_columnconfigure(1, weight=1)

        # Invoice #
        inv_f = ctk.CTkFrame(r1, fg_color="transparent")
        inv_f.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ctk.CTkLabel(inv_f, text="Invoice #:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self.entry_invoice_no = ctk.CTkEntry(inv_f, placeholder_text="102630", font=ctk.CTkFont(weight="bold"))
        self.entry_invoice_no.pack(fill="x")

        # Invoice Date
        date_f = ctk.CTkFrame(r1, fg_color="transparent")
        date_f.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        ctk.CTkLabel(date_f, text="Invoice Date:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        
        date_input_row = ctk.CTkFrame(date_f, fg_color="transparent")
        date_input_row.pack(fill="x")
        self.entry_invoice_date = ctk.CTkEntry(date_input_row, placeholder_text="04th Sep 2026")
        self.entry_invoice_date.pack(side="left", fill="x", expand=True)

        btn_today = ctk.CTkButton(
            date_input_row, text="Today", width=46, height=28,
            fg_color="#334155", hover_color="#475569",
            command=lambda: self._set_today_date()
        )
        btn_today.pack(side="right", padx=(4, 0))

        # Client Reference
        ctk.CTkLabel(right_box, text="Client Name / Subject Reference:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))
        self.entry_client_name = ctk.CTkEntry(right_box, placeholder_text="e.g. Ms. Rochelle Visa Renewal")
        self.entry_client_name.pack(fill="x", padx=10, pady=(0, 10))

    def _build_items_card(self):
        card = ctk.CTkFrame(self.main_scroll, corner_radius=8, fg_color="#1E293B")
        card.pack(fill="x", pady=(0, 10))

        # Card Title Bar with Add/Clear Buttons
        title_bar = ctk.CTkFrame(card, fg_color="transparent")
        title_bar.pack(fill="x", padx=14, pady=(10, 6))

        lbl_card = ctk.CTkLabel(
            title_bar,
            text="📋 Itemized Table (Line Items)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38BDF8"
        )
        lbl_card.pack(side="left")

        btn_clear = ctk.CTkButton(
            title_bar, text="🗑️ Clear All", width=90, height=28,
            fg_color="#475569", hover_color="#334155",
            command=self._clear_all_items
        )
        btn_clear.pack(side="right", padx=(6, 0))

        btn_sample = ctk.CTkButton(
            title_bar, text="📑 Load Reference Sample", width=160, height=28,
            fg_color="#334155", hover_color="#475569",
            command=self._load_reference_sample_items
        )
        btn_sample.pack(side="right", padx=(6, 0))

        btn_add = ctk.CTkButton(
            title_bar, text="➕ Add Row", width=95, height=28,
            fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(weight="bold"),
            command=lambda: self.add_item_row()
        )
        btn_add.pack(side="right", padx=(6, 0))

        # Table Column Headers Bar
        hdr_bar = ctk.CTkFrame(card, height=32, corner_radius=4, fg_color="#0F172A")
        hdr_bar.pack(fill="x", padx=14, pady=(2, 4))
        hdr_bar.grid_columnconfigure(0, weight=0, minsize=35)
        hdr_bar.grid_columnconfigure(1, weight=3, minsize=180)
        hdr_bar.grid_columnconfigure(2, weight=0, minsize=65)
        hdr_bar.grid_columnconfigure(3, weight=1, minsize=95)
        hdr_bar.grid_columnconfigure(4, weight=0, minsize=75)
        hdr_bar.grid_columnconfigure(5, weight=1, minsize=80)
        hdr_bar.grid_columnconfigure(6, weight=1, minsize=90)
        hdr_bar.grid_columnconfigure(7, weight=0, minsize=85)

        h_font = ctk.CTkFont(size=11, weight="bold")
        ctk.CTkLabel(hdr_bar, text="S#", font=h_font, width=30).grid(row=0, column=0, padx=(6, 2), pady=6, sticky="w")
        ctk.CTkLabel(hdr_bar, text="Description", font=h_font).grid(row=0, column=1, padx=4, pady=6, sticky="w")
        ctk.CTkLabel(hdr_bar, text="Quantity", font=h_font, width=60).grid(row=0, column=2, padx=4, pady=6)
        ctk.CTkLabel(hdr_bar, text="Unit (AED)", font=h_font, width=90).grid(row=0, column=3, padx=4, pady=6, sticky="e")
        ctk.CTkLabel(hdr_bar, text="VAT (5%)", font=h_font, width=70).grid(row=0, column=4, padx=4, pady=6)
        ctk.CTkLabel(hdr_bar, text="VAT Amt", font=h_font, width=75).grid(row=0, column=5, padx=4, pady=6, sticky="e")
        ctk.CTkLabel(hdr_bar, text="Total (AED)", font=h_font, width=85).grid(row=0, column=6, padx=4, pady=6, sticky="e")
        ctk.CTkLabel(hdr_bar, text="Actions", font=h_font, width=80).grid(row=0, column=7, padx=4, pady=6)

        # Dynamic Rows Container
        self.rows_container = ctk.CTkFrame(card, fg_color="transparent")
        self.rows_container.pack(fill="x", padx=14, pady=(2, 10))

    def _build_financial_summary_card(self):
        card = ctk.CTkFrame(self.main_scroll, corner_radius=8, fg_color="#1E293B")
        card.pack(fill="x", pady=(0, 10))

        # Amount in Words Banner (Highlighted full width)
        words_frame = ctk.CTkFrame(card, fg_color="#0F172A", corner_radius=6)
        words_frame.pack(fill="x", padx=14, pady=(12, 10))

        ctk.CTkLabel(
            words_frame,
            text="CURRENCY IN WORDS (AED):",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#94A3B8"
        ).pack(anchor="w", padx=12, pady=(8, 1))

        self.lbl_amount_in_words = ctk.CTkLabel(
            words_frame,
            text="AED ZERO & ZERO FILS ONLY",
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            text_color="#38BDF8",
            wraplength=850
        )
        self.lbl_amount_in_words.pack(anchor="w", padx=12, pady=(0, 10))

        # Split lower section: Bank Summary (Left) and Financial Totals (Right)
        split_frame = ctk.CTkFrame(card, fg_color="transparent")
        split_frame.pack(fill="x", padx=14, pady=(0, 12))
        split_frame.grid_columnconfigure(0, weight=1)
        split_frame.grid_columnconfigure(1, weight=1)

        # Left: Bank Details Readout
        bank_box = ctk.CTkFrame(split_frame, fg_color="#0F172A", corner_radius=6)
        bank_box.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctk.CTkLabel(
            bank_box, text="🏦 Bank Settlement Details",
            font=ctk.CTkFont(size=11, weight="bold"), text_color="#F8FAFC"
        ).pack(anchor="w", padx=12, pady=(8, 4))

        self.lbl_bank_info = ctk.CTkLabel(
            bank_box,
            text="WIO BUSINESS\nA/C: 9895248605\nIBAN: AE620860000009895248605",
            font=ctk.CTkFont(size=11),
            text_color="#CBD5E1",
            justify="left"
        )
        self.lbl_bank_info.pack(anchor="w", padx=12, pady=(0, 8))

        # Right: Financial Totals Cards
        totals_box = ctk.CTkFrame(split_frame, fg_color="#0F172A", corner_radius=6)
        totals_box.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        totals_grid = ctk.CTkFrame(totals_box, fg_color="transparent")
        totals_grid.pack(fill="x", padx=14, pady=10)
        totals_grid.grid_columnconfigure(0, weight=1)
        totals_grid.grid_columnconfigure(1, weight=1)

        # Row 1: Subtotal
        ctk.CTkLabel(totals_grid, text="Subtotal (Amount):", font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w", pady=3)
        self.lbl_subtotal = ctk.CTkLabel(totals_grid, text="AED 0.00", font=ctk.CTkFont(size=12, weight="bold"), anchor="e")
        self.lbl_subtotal.grid(row=0, column=1, sticky="e", pady=3)

        # Row 2: VAT Total (5%)
        ctk.CTkLabel(totals_grid, text="VAT Total (5%):", font=ctk.CTkFont(size=12)).grid(row=1, column=0, sticky="w", pady=3)
        self.lbl_vat_total = ctk.CTkLabel(totals_grid, text="AED 0.00", font=ctk.CTkFont(size=12, weight="bold"), text_color="#F59E0B", anchor="e")
        self.lbl_vat_total.grid(row=1, column=1, sticky="e", pady=3)

        # Row 3: Grand Total
        ctk.CTkLabel(totals_grid, text="Grand Total:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38BDF8").grid(row=2, column=0, sticky="w", pady=(6, 2))
        self.lbl_grand_total = ctk.CTkLabel(totals_grid, text="AED 0.00", font=ctk.CTkFont(size=16, weight="bold"), text_color="#10B981", anchor="e")
        self.lbl_grand_total.grid(row=2, column=1, sticky="e", pady=(6, 2))

    def _build_bottom_action_bar(self):
        bottom_bar = ctk.CTkFrame(self, height=65, corner_radius=0, fg_color="#0F172A")
        bottom_bar.pack(fill="x", side="bottom")

        # Left Info
        lbl_hint = ctk.CTkLabel(
            bottom_bar,
            text="✨ PDF output replicates reference visual layout, typography, and borders.",
            font=ctk.CTkFont(size=11),
            text_color="#64748B"
        )
        lbl_hint.pack(side="left", padx=20, pady=16)

        # Right Action Buttons
        btn_save = ctk.CTkButton(
            bottom_bar,
            text="💾 Generate & Save PDF",
            width=180,
            height=38,
            fg_color="#10B981",
            hover_color="#059669",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_generate_save_pdf
        )
        btn_save.pack(side="right", padx=(6, 20), pady=12)

        btn_preview = ctk.CTkButton(
            bottom_bar,
            text="👁 Preview Invoice",
            width=150,
            height=38,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_preview_invoice
        )
        btn_preview.pack(side="right", padx=6, pady=12)

    # -------------------------------------------------------------
    # State & Event Handlers
    # -------------------------------------------------------------
    def _set_today_date(self):
        self.entry_invoice_date.delete(0, "end")
        self.entry_invoice_date.insert(0, get_formatted_today_date())

    def _load_initial_defaults(self):
        """Loads default customer info and invoice number from settings."""
        self._set_today_date()

        inv_num = get_next_invoice_number()
        self.entry_invoice_no.delete(0, "end")
        self.entry_invoice_no.insert(0, str(inv_num))

        defs = self.settings.get("defaults", {})
        self.entry_client_name.delete(0, "end")
        self.entry_client_name.insert(0, defs.get("client_name", "Ms. Rochelle Visa Renewal"))

        self.entry_cust_company.delete(0, "end")
        self.entry_cust_company.insert(0, defs.get("customer_company", "Petro Gulf Refined Oil Products Trading L.L.C"))

        self.entry_cust_address.delete(0, "end")
        self.entry_cust_address.insert(0, defs.get("customer_address", "Business Bay, Dubai"))

        self.entry_cust_trn.delete(0, "end")
        self.entry_cust_trn.insert(0, defs.get("customer_trn", "100459434500003"))

        self._refresh_bank_info_label()

        # Load reference sample items by default
        self._load_reference_sample_items()

    def _refresh_bank_info_label(self):
        b = self.settings.get("bank", {})
        b_name = b.get("bank_name", "WIO BUSINESS")
        acc_no = b.get("account_no", "9895248605")
        iban = b.get("iban", "AE620860000009895248605")
        bene = b.get("beneficiary_name", "Silver Premium Documents Clearing Co LLC")
        self.lbl_bank_info.configure(
            text=f"Bank: {b_name}\nA/C: {acc_no} | IBAN: {iban}\nBeneficiary: {bene}"
        )

    def add_item_row(
        self,
        description: str = "",
        quantity: str = "1",
        unit_amount: str = "0.00",
        vat_toggle: str = "No"
    ) -> ItemRow:
        idx = len(self.item_rows) + 1
        row = ItemRow(
            self.rows_container,
            index=idx,
            description=description,
            quantity=quantity,
            unit_amount=unit_amount,
            vat_toggle=vat_toggle,
            on_change_callback=self.recalculate_totals,
            on_move_up=self._move_row_up,
            on_move_down=self._move_row_down,
            on_delete=self._delete_row,
            fg_color="#0F172A"
        )
        row.pack(fill="x", pady=2)
        self.item_rows.append(row)
        self.recalculate_totals()
        return row

    def _move_row_up(self, row: ItemRow):
        idx = self.item_rows.index(row)
        if idx > 0:
            self.item_rows[idx], self.item_rows[idx - 1] = self.item_rows[idx - 1], self.item_rows[idx]
            self._repack_all_rows()
            self.recalculate_totals()

    def _move_row_down(self, row: ItemRow):
        idx = self.item_rows.index(row)
        if idx < len(self.item_rows) - 1:
            self.item_rows[idx], self.item_rows[idx + 1] = self.item_rows[idx + 1], self.item_rows[idx]
            self._repack_all_rows()
            self.recalculate_totals()

    def _delete_row(self, row: ItemRow):
        if len(self.item_rows) <= 1:
            messagebox.showwarning("Notice", "An invoice must have at least one line item row.")
            return
        row.destroy()
        self.item_rows.remove(row)
        self._reindex_rows()
        self.recalculate_totals()

    def _clear_all_items(self):
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear all line items?"):
            for r in self.item_rows:
                r.destroy()
            self.item_rows.clear()
            self.add_item_row()

    def _repack_all_rows(self):
        for r in self.item_rows:
            r.pack_forget()
        for idx, r in enumerate(self.item_rows, start=1):
            r.set_index(idx)
            r.pack(fill="x", pady=2)

    def _reindex_rows(self):
        for idx, r in enumerate(self.item_rows, start=1):
            r.set_index(idx)

    def _load_reference_sample_items(self):
        """Populates the table with reference invoice items."""
        for r in self.item_rows:
            r.destroy()
        self.item_rows.clear()

        self.add_item_row(
            description="Visa Renewal",
            quantity="1",
            unit_amount="6300.00",
            vat_toggle="No"
        )
        self.add_item_row(
            description="Service Charges",
            quantity="1",
            unit_amount="200.00",
            vat_toggle="Yes"
        )

    def recalculate_totals(self):
        """Calculates Subtotal, VAT Total, and Grand Total across all rows."""
        subtotal = 0.0
        vat_total = 0.0

        for r in self.item_rows:
            subtotal += r.get_quantity() * r.get_unit_amount()
            vat_total += r.get_vat_amount()

        subtotal = round(subtotal, 2)
        vat_total = round(vat_total, 2)
        grand_total = round(subtotal + vat_total, 2)

        self.lbl_subtotal.configure(text=f"AED {subtotal:,.2f}")
        self.lbl_vat_total.configure(text=f"AED {vat_total:,.2f}")
        self.lbl_grand_total.configure(text=f"AED {grand_total:,.2f}")

        # Live Currency in Words
        words = amount_to_aed_words(grand_total)
        self.lbl_amount_in_words.configure(text=words)

    def get_invoice_data_dict(self) -> Dict[str, Any]:
        """Constructs complete dictionary for PDF engine."""
        subtotal = 0.0
        vat_total = 0.0
        items_data = []

        for r in self.item_rows:
            item_dict = r.to_dict()
            items_data.append(item_dict)
            subtotal += item_dict["quantity"] * item_dict["unit_amount"]
            vat_total += item_dict["vat_amount"]

        subtotal = round(subtotal, 2)
        vat_total = round(vat_total, 2)
        grand_total = round(subtotal + vat_total, 2)
        words = amount_to_aed_words(grand_total)

        return {
            "invoice_no": self.entry_invoice_no.get().strip() or "102630",
            "date": self.entry_invoice_date.get().strip() or get_formatted_today_date(),
            "client_name": self.entry_client_name.get().strip(),
            "company": self.settings.get("company", {}),
            "customer": {
                "company_name": self.entry_cust_company.get().strip(),
                "address": self.entry_cust_address.get().strip(),
                "trn": self.entry_cust_trn.get().strip()
            },
            "bank": self.settings.get("bank", {}),
            "items": items_data,
            "subtotal": subtotal,
            "vat_total": vat_total,
            "grand_total": grand_total,
            "amount_in_words": words,
            "terms": self.settings.get("terms", [])
        }

    def _on_preview_invoice(self):
        data = self.get_invoice_data_dict()
        PreviewDialog(self, data, on_saved_callback=self._on_invoice_saved_success)

    def _on_generate_save_pdf(self):
        data = self.get_invoice_data_dict()
        inv_no = data.get("invoice_no", "102630")
        client_clean = "".join(c for c in data.get("client_name", "Invoice") if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
        init_file = f"Invoice_{inv_no}_{client_clean}.pdf"

        save_path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".pdf",
            filetypes=[("PDF Document", "*.pdf")],
            initialfile=init_file,
            title="Generate & Save Tax Invoice PDF"
        )
        if not save_path:
            return

        try:
            generate_invoice_pdf(data, save_path)
            self._on_invoice_saved_success(save_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate invoice PDF:\n{e}")

    def _on_invoice_saved_success(self, pdf_path: str):
        # Auto-increment invoice sequence
        new_inv_num = increment_invoice_number()
        self.entry_invoice_no.delete(0, "end")
        self.entry_invoice_no.insert(0, str(new_inv_num))

        # Show success prompt with action options
        resp = messagebox.askyesno(
            "Invoice Generated Successfully",
            f"Tax Invoice saved successfully to:\n{pdf_path}\n\nNext Invoice Number incremented to #{new_inv_num}.\n\nWould you like to open the PDF now?"
        )
        if resp:
            try:
                os.startfile(pdf_path)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to launch PDF viewer: {e}")

    def _on_new_invoice(self):
        if messagebox.askyesno("New Invoice", "Prepare a new invoice? This will reset client inputs while keeping your next invoice sequence number."):
            self._set_today_date()
            inv_num = get_next_invoice_number()
            self.entry_invoice_no.delete(0, "end")
            self.entry_invoice_no.insert(0, str(inv_num))
            self.entry_client_name.delete(0, "end")
            self._load_reference_sample_items()

    def _open_settings(self):
        SettingsDialog(self, on_save_callback=self._on_settings_updated)

    def _on_settings_updated(self):
        self.settings = load_settings()
        self._refresh_bank_info_label()

    def _toggle_theme(self):
        current = ctk.get_appearance_mode()
        new_mode = "Light" if current == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
