"""
Settings Dialog
Configuration modal for Company, Bank, Terms & Conditions, and Invoice counter defaults.
Saves persistently to settings.json.
"""
import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Optional, Dict, Any

from core.settings_manager import load_settings, save_settings, DEFAULT_SETTINGS


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_save_callback: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.on_save_callback = on_save_callback
        self.title("Company & Payment Defaults Configuration")
        self.geometry("640x720")
        self.minsize(550, 600)
        self.transient(parent)
        self.grab_set()

        self.settings = load_settings()

        self._build_ui()
        self._load_data()

    def _build_ui(self):
        # Header
        hdr = ctk.CTkFrame(self, height=50, corner_radius=0, fg_color="#1E293B")
        hdr.pack(fill="x", side="top")

        lbl_hdr = ctk.CTkLabel(
            hdr,
            text="⚙️ Company & Invoice Configuration",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#F8FAFC"
        )
        lbl_hdr.pack(side="left", padx=16, pady=10)

        # Main scrollable form
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=16, pady=12)

        # 1. Company Information Card
        card_company = ctk.CTkFrame(scroll, corner_radius=8)
        card_company.pack(fill="x", pady=(0, 12), padx=4)

        ctk.CTkLabel(
            card_company, text="🏢 Company & Issuer Details",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#38BDF8"
        ).pack(anchor="w", padx=14, pady=(10, 6))

        ctk.CTkLabel(card_company, text="Issuer Name:", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=14)
        self.entry_company_name = ctk.CTkEntry(card_company, font=ctk.CTkFont(size=12))
        self.entry_company_name.pack(fill="x", padx=14, pady=(2, 8))

        ctk.CTkLabel(card_company, text="Issuer TRN:", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=14)
        self.entry_company_trn = ctk.CTkEntry(card_company, font=ctk.CTkFont(size=12))
        self.entry_company_trn.pack(fill="x", padx=14, pady=(2, 8))

        ctk.CTkLabel(card_company, text="Footer Location & Phone:", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=14)
        self.entry_footer = ctk.CTkEntry(card_company, font=ctk.CTkFont(size=12))
        self.entry_footer.pack(fill="x", padx=14, pady=(2, 12))

        # 2. Bank Details Card
        card_bank = ctk.CTkFrame(scroll, corner_radius=8)
        card_bank.pack(fill="x", pady=(0, 12), padx=4)

        ctk.CTkLabel(
            card_bank, text="🏦 Official Bank Details",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#38BDF8"
        ).pack(anchor="w", padx=14, pady=(10, 6))

        ctk.CTkLabel(card_bank, text="Bank Name:", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=14)
        self.entry_bank_name = ctk.CTkEntry(card_bank, font=ctk.CTkFont(size=12))
        self.entry_bank_name.pack(fill="x", padx=14, pady=(2, 8))

        ctk.CTkLabel(card_bank, text="Account Number:", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=14)
        self.entry_account_no = ctk.CTkEntry(card_bank, font=ctk.CTkFont(size=12))
        self.entry_account_no.pack(fill="x", padx=14, pady=(2, 8))

        ctk.CTkLabel(card_bank, text="Beneficiary Name:", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=14)
        self.entry_beneficiary = ctk.CTkEntry(card_bank, font=ctk.CTkFont(size=12))
        self.entry_beneficiary.pack(fill="x", padx=14, pady=(2, 8))

        ctk.CTkLabel(card_bank, text="IBAN Number:", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=14)
        self.entry_iban = ctk.CTkEntry(card_bank, font=ctk.CTkFont(size=12))
        self.entry_iban.pack(fill="x", padx=14, pady=(2, 12))

        # 3. Terms & Conditions Card
        card_terms = ctk.CTkFrame(scroll, corner_radius=8)
        card_terms.pack(fill="x", pady=(0, 12), padx=4)

        ctk.CTkLabel(
            card_terms, text="📋 Terms & Conditions (One per line)",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#38BDF8"
        ).pack(anchor="w", padx=14, pady=(10, 6))

        self.txt_terms = ctk.CTkTextbox(card_terms, height=90, font=ctk.CTkFont(size=12))
        self.txt_terms.pack(fill="x", padx=14, pady=(2, 12))

        # 4. Invoice Sequence Counter
        card_inv = ctk.CTkFrame(scroll, corner_radius=8)
        card_inv.pack(fill="x", pady=(0, 12), padx=4)

        ctk.CTkLabel(
            card_inv, text="🔢 Next Invoice Sequence Number",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#38BDF8"
        ).pack(anchor="w", padx=14, pady=(10, 6))

        self.entry_next_inv = ctk.CTkEntry(card_inv, width=160, font=ctk.CTkFont(size=12))
        self.entry_next_inv.pack(anchor="w", padx=14, pady=(2, 12))

        # Bottom Actions Bar
        bottom_bar = ctk.CTkFrame(self, height=55, corner_radius=0, fg_color="#1E293B")
        bottom_bar.pack(fill="x", side="bottom")

        btn_cancel = ctk.CTkButton(
            bottom_bar, text="Cancel", width=90, height=34,
            fg_color="#475569", hover_color="#334155",
            command=self.destroy
        )
        btn_cancel.pack(side="right", padx=(6, 16), pady=10)

        btn_save = ctk.CTkButton(
            bottom_bar, text="💾 Save Changes", width=120, height=34,
            fg_color="#10B981", hover_color="#059669", font=ctk.CTkFont(weight="bold"),
            command=self._on_save
        )
        btn_save.pack(side="right", padx=6, pady=10)

        btn_restore = ctk.CTkButton(
            bottom_bar, text="🔄 Restore Defaults", width=130, height=34,
            fg_color="#E11D48", hover_color="#BE123C",
            command=self._on_restore_defaults
        )
        btn_restore.pack(side="left", padx=16, pady=10)

    def _load_data(self):
        c = self.settings.get("company", {})
        self.entry_company_name.delete(0, "end")
        self.entry_company_name.insert(0, c.get("name", ""))

        self.entry_company_trn.delete(0, "end")
        self.entry_company_trn.insert(0, c.get("trn", ""))

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

        inv_num = self.settings.get("invoice", {}).get("next_number", 102630)
        self.entry_next_inv.delete(0, "end")
        self.entry_next_inv.insert(0, str(inv_num))

    def _on_save(self):
        try:
            next_num = int(self.entry_next_inv.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Next Invoice Number must be a valid integer.")
            return

        terms_lines = [l.strip() for l in self.txt_terms.get("1.0", "end").splitlines() if l.strip()]

        new_settings = {
            "company": {
                "name": self.entry_company_name.get().strip(),
                "trn": self.entry_company_trn.get().strip(),
                "footer_text": self.entry_footer.get().strip()
            },
            "bank": {
                "bank_name": self.entry_bank_name.get().strip(),
                "account_no": self.entry_account_no.get().strip(),
                "beneficiary_name": self.entry_beneficiary.get().strip(),
                "iban": self.entry_iban.get().strip()
            },
            "terms": terms_lines,
            "invoice": {
                "next_number": next_num,
                "prefix": self.settings.get("invoice", {}).get("prefix", ""),
                "suffix": self.settings.get("invoice", {}).get("suffix", "")
            },
            "defaults": self.settings.get("defaults", {})
        }

        save_settings(new_settings)
        messagebox.showinfo("Saved", "Company defaults updated successfully!")
        if self.on_save_callback:
            self.on_save_callback()
        self.destroy()

    def _on_restore_defaults(self):
        if messagebox.askyesno("Confirm", "Reset all company & bank details to Silver Premium defaults?"):
            self.settings = DEFAULT_SETTINGS
            self._load_data()
