"""
Customer Profiles Management Dialog
Provides full management of customer profiles:
- Live search and filtering
- Add, edit, and delete customer profiles
- Auto-fill active invoice directly from dialog ("Use in Invoice")
- Import existing customers from past invoice records
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Any, Optional, Callable

from core.customer_manager import (
    load_customers,
    save_or_update_customer,
    delete_customer,
    import_from_invoices,
    get_customer_by_id
)
from gui.window_utils import center_window


class CustomerProfilesDialog(tk.Toplevel):
    def __init__(
        self,
        parent,
        on_select_customer: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_data_changed: Optional[Callable[[], None]] = None,
        prefill_data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(parent)
        self.on_select_customer = on_select_customer
        self.on_data_changed = on_data_changed
        self.prefill_data = prefill_data

        self.title("Customer Profiles & Accounts")
        self.geometry("1020x570")
        self.minsize(880, 440)
        self.transient(parent)
        self.grab_set()

        self.current_selected_id: Optional[str] = None
        self.all_customers: List[Dict[str, Any]] = []

        # Style Treeview with adequate rowheight to prevent text from being sliced/truncated
        self.style = ttk.Style(self)
        try:
            self.style.configure("Treeview", font=("Segoe UI", 9), rowheight=28)
            self.style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), padding=(4, 4))
        except Exception:
            pass

        self._build_ui()
        self._load_customers_list()

        # If prefill data provided (e.g. from current invoice form), populate form
        if self.prefill_data:
            self._apply_prefill_data(self.prefill_data)

        center_window(self, parent, 1020, 570)

    def _build_ui(self):
        # 1. Top Search & Controls Bar
        top_bar = ttk.Frame(self, padding=(12, 10))
        top_bar.pack(fill="x", side="top")

        ttk.Label(top_bar, text="Search Profiles:", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 6))

        self.var_search = tk.StringVar()
        self.var_search.trace_add("write", lambda *args: self._filter_customers())
        self.entry_search = ttk.Entry(top_bar, textvariable=self.var_search, width=28, font=("Segoe UI", 10))
        self.entry_search.pack(side="left", padx=(0, 10))

        btn_import = ttk.Button(top_bar, text="Import from Invoices", command=self._on_import_invoices)
        btn_import.pack(side="right", padx=(6, 0))

        btn_new = ttk.Button(top_bar, text="+ Add Customer", command=self._clear_form)
        btn_new.pack(side="right", padx=(6, 0))

        ttk.Separator(self, orient="horizontal").pack(fill="x", side="top")

        # 2. PINNED BOTTOM ACTION BAR (Packed FIRST so it is NEVER hidden)
        bot_bar = ttk.Frame(self, padding=(12, 10))
        bot_bar.pack(fill="x", side="bottom")

        btn_close = ttk.Button(bot_bar, text="Close", command=self.destroy, width=10)
        btn_close.pack(side="right", padx=(6, 0))

        self.btn_use = ttk.Button(
            bot_bar,
            text="Use in Active Invoice",
            command=self._on_use_in_invoice
        )
        self.btn_use.pack(side="right", padx=(6, 0))

        btn_vat = ttk.Button(
            bot_bar,
            text="📊 Profile Tax History",
            command=self._on_view_vat_history
        )
        btn_vat.pack(side="right", padx=(6, 0))

        self.lbl_status = ttk.Label(bot_bar, text="Select a customer profile or add a new one.", font=("Segoe UI", 9))
        self.lbl_status.pack(side="left")

        ttk.Separator(self, orient="horizontal").pack(fill="x", side="bottom")

        # 3. Main Split Area: Left Treeview, Right Edit Panel
        main_split = ttk.PanedWindow(self, orient="horizontal")
        main_split.pack(fill="both", expand=True, padx=12, pady=10)

        # Left: Profiles Table
        left_frame = ttk.Frame(main_split)
        main_split.add(left_frame, weight=1)

        cols = ("company", "client", "trn", "phone")
        self.tree = ttk.Treeview(left_frame, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("company", text="Company Name")
        self.tree.heading("client", text="Contact / Reference")
        self.tree.heading("trn", text="TRN")
        self.tree.heading("phone", text="Phone")

        self.tree.column("company", width=220, anchor="w")
        self.tree.column("client", width=160, anchor="w")
        self.tree.column("trn", width=130, anchor="center")
        self.tree.column("phone", width=110, anchor="center")

        vsb = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(left_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        left_frame.grid_rowconfigure(0, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", lambda e: self._on_use_in_invoice())

        # Count label at bottom of left frame
        self.lbl_count = ttk.Label(left_frame, text="0 profiles saved", font=("Segoe UI", 9), foreground="#64748B")
        self.lbl_count.grid(row=2, column=0, sticky="w", pady=(6, 0))

        # Right: Customer Details Editor
        right_frame = ttk.LabelFrame(main_split, text=" Customer Profile Details ", padding=12)
        main_split.add(right_frame, weight=1)

        r = 0
        ttk.Label(right_frame, text="Company Name *:", font=("Segoe UI", 9, "bold")).grid(row=r, column=0, sticky="w", pady=4)
        self.entry_company = ttk.Entry(right_frame, font=("Segoe UI", 9))
        self.entry_company.grid(row=r, column=1, sticky="ew", pady=4, padx=(6, 0))

        r += 1
        ttk.Label(right_frame, text="Contact / Reference:").grid(row=r, column=0, sticky="w", pady=4)
        self.entry_client = ttk.Entry(right_frame, font=("Segoe UI", 9))
        self.entry_client.grid(row=r, column=1, sticky="ew", pady=4, padx=(6, 0))

        r += 1
        ttk.Label(right_frame, text="Address / City:").grid(row=r, column=0, sticky="w", pady=4)
        self.entry_address = ttk.Entry(right_frame, font=("Segoe UI", 9))
        self.entry_address.grid(row=r, column=1, sticky="ew", pady=4, padx=(6, 0))

        r += 1
        ttk.Label(right_frame, text="Customer TRN:").grid(row=r, column=0, sticky="w", pady=4)
        self.entry_trn = ttk.Entry(right_frame, font=("Segoe UI", 9))
        self.entry_trn.grid(row=r, column=1, sticky="ew", pady=4, padx=(6, 0))

        r += 1
        ttk.Label(right_frame, text="Phone Number:").grid(row=r, column=0, sticky="w", pady=4)
        self.entry_phone = ttk.Entry(right_frame, font=("Segoe UI", 9))
        self.entry_phone.grid(row=r, column=1, sticky="ew", pady=4, padx=(6, 0))

        r += 1
        ttk.Label(right_frame, text="Email Address:").grid(row=r, column=0, sticky="w", pady=4)
        self.entry_email = ttk.Entry(right_frame, font=("Segoe UI", 9))
        self.entry_email.grid(row=r, column=1, sticky="ew", pady=4, padx=(6, 0))

        r += 1
        ttk.Label(right_frame, text="Notes:").grid(row=r, column=0, sticky="w", pady=4)
        self.entry_notes = ttk.Entry(right_frame, font=("Segoe UI", 9))
        self.entry_notes.grid(row=r, column=1, sticky="ew", pady=4, padx=(6, 0))

        right_frame.grid_columnconfigure(1, weight=1)

        # Action buttons inside right panel
        r += 1
        btn_panel = ttk.Frame(right_frame)
        btn_panel.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        btn_panel.grid_columnconfigure(0, weight=1)
        btn_panel.grid_columnconfigure(1, weight=1)

        self.btn_save = ttk.Button(btn_panel, text="Save Profile", command=self._on_save_profile)
        self.btn_save.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=2)

        btn_clear = ttk.Button(btn_panel, text="Clear Form", command=self._clear_form)
        btn_clear.grid(row=0, column=1, sticky="ew", padx=(4, 0), pady=2)

        self.btn_delete = ttk.Button(btn_panel, text="Delete Profile", command=self._on_delete_profile)
        self.btn_delete.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        self.btn_view_vat = ttk.Button(btn_panel, text="📊 View VAT / Tax History", command=self._on_view_vat_history)
        self.btn_view_vat.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))

    def _on_view_vat_history(self):
        comp = self.entry_company.get().strip()
        if not comp and self.current_selected_id:
            cust = get_customer_by_id(self.current_selected_id)
            if cust:
                comp = cust.get("company_name", "")
        if not comp:
            messagebox.showinfo("Select Profile", "Please select or search a customer profile to view their VAT history.")
            return
        from gui.history_view import HistoryDialog
        HistoryDialog(self, initial_company=comp)

    def _load_customers_list(self):
        self.all_customers = load_customers()
        self._filter_customers()

    def _filter_customers(self):
        query = self.var_search.get().strip().lower()
        self.tree.delete(*self.tree.get_children())

        matched_count = 0
        for c in self.all_customers:
            comp = c.get("company_name", "")
            client = c.get("client_name", "")
            trn = c.get("trn", "")
            phone = c.get("phone", "")
            addr = c.get("address", "")

            combined = f"{comp} {client} {trn} {phone} {addr}".lower()
            if not query or query in combined:
                item_id = str(c.get("id") or f"cust_{matched_count}")
                if self.tree.exists(item_id):
                    item_id = f"{item_id}_{matched_count}"
                    c["id"] = item_id
                self.tree.insert(
                    "",
                    "end",
                    iid=item_id,
                    values=(comp, client, trn, phone)
                )
                matched_count += 1

        self.lbl_count.configure(text=f"{matched_count} of {len(self.all_customers)} profiles shown")

        # If previously selected item is still visible, reselect it
        if self.current_selected_id and self.tree.exists(self.current_selected_id):
            self.tree.selection_set(self.current_selected_id)
            self.tree.see(self.current_selected_id)

    def _on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        cust_id = selected[0]
        cust = get_customer_by_id(cust_id)
        if cust:
            self.current_selected_id = cust.get("id")
            self._fill_form(cust)
            self.lbl_status.configure(text=f"Selected profile: {cust.get('company_name')}")

    def _fill_form(self, cust: Dict[str, Any]):
        self.entry_company.delete(0, "end")
        self.entry_company.insert(0, cust.get("company_name", ""))

        self.entry_client.delete(0, "end")
        self.entry_client.insert(0, cust.get("client_name", ""))

        self.entry_address.delete(0, "end")
        self.entry_address.insert(0, cust.get("address", ""))

        self.entry_trn.delete(0, "end")
        self.entry_trn.insert(0, cust.get("trn", ""))

        self.entry_phone.delete(0, "end")
        self.entry_phone.insert(0, cust.get("phone", ""))

        self.entry_email.delete(0, "end")
        self.entry_email.insert(0, cust.get("email", ""))

        self.entry_notes.delete(0, "end")
        self.entry_notes.insert(0, cust.get("notes", ""))

    def _apply_prefill_data(self, data: Dict[str, Any]):
        """Prefills the form when opened with unsaved data from main invoice."""
        self._clear_form()
        self.entry_company.insert(0, data.get("company_name", ""))
        self.entry_client.insert(0, data.get("client_name", ""))
        self.entry_address.insert(0, data.get("address", ""))
        self.entry_trn.insert(0, data.get("trn", ""))

    def _clear_form(self):
        self.current_selected_id = None
        self.tree.selection_remove(self.tree.selection())
        for e in (self.entry_company, self.entry_client, self.entry_address,
                  self.entry_trn, self.entry_phone, self.entry_email, self.entry_notes):
            e.delete(0, "end")
        self.entry_company.focus_set()
        self.lbl_status.configure(text="Creating new customer profile. Fill fields and click Save.")

    def _on_save_profile(self):
        comp = self.entry_company.get().strip()
        if not comp:
            messagebox.showwarning("Validation Error", "Company Name is required to save a customer profile.")
            self.entry_company.focus_set()
            return

        cust_data = {
            "id": self.current_selected_id,
            "company_name": comp,
            "client_name": self.entry_client.get().strip(),
            "address": self.entry_address.get().strip(),
            "trn": self.entry_trn.get().strip(),
            "phone": self.entry_phone.get().strip(),
            "email": self.entry_email.get().strip(),
            "notes": self.entry_notes.get().strip(),
        }

        saved = save_or_update_customer(cust_data)
        self.current_selected_id = saved.get("id")

        self._load_customers_list()
        if self.current_selected_id and self.tree.exists(self.current_selected_id):
            self.tree.selection_set(self.current_selected_id)
            self.tree.see(self.current_selected_id)

        self.lbl_status.configure(text=f"✓ Profile '{comp}' saved successfully.")

        if self.on_data_changed:
            self.on_data_changed()

    def _on_delete_profile(self):
        if not self.current_selected_id:
            messagebox.showinfo("Notice", "Please select a customer profile from the list to delete.")
            return

        cust = get_customer_by_id(self.current_selected_id)
        name = cust.get("company_name", "this customer") if cust else "this customer"

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete profile:\n\n{name}?"):
            delete_customer(self.current_selected_id)
            self._clear_form()
            self._load_customers_list()
            self.lbl_status.configure(text=f"Profile '{name}' deleted.")

            if self.on_data_changed:
                self.on_data_changed()

    def _on_use_in_invoice(self):
        # If user selected an item or filled company name in form
        comp = self.entry_company.get().strip()
        if not comp:
            selected = self.tree.selection()
            if selected:
                cust = get_customer_by_id(selected[0])
                if cust:
                    comp = cust.get("company_name", "")

        if not comp:
            messagebox.showwarning("Notice", "Please select or enter a customer to use in invoice.")
            return

        cust_data = {
            "id": self.current_selected_id,
            "company_name": self.entry_company.get().strip(),
            "client_name": self.entry_client.get().strip(),
            "address": self.entry_address.get().strip(),
            "trn": self.entry_trn.get().strip(),
            "phone": self.entry_phone.get().strip(),
            "email": self.entry_email.get().strip(),
            "notes": self.entry_notes.get().strip()
        }

        if self.on_select_customer:
            self.on_select_customer(cust_data)

        self.destroy()

    def _on_import_invoices(self):
        imported = import_from_invoices()
        self._load_customers_list()
        if imported > 0:
            messagebox.showinfo("Import Complete", f"Successfully imported {imported} new customer(s) from past invoice records.")
            self.lbl_status.configure(text=f"✓ Imported {imported} customer(s).")
            if self.on_data_changed:
                self.on_data_changed()
        else:
            messagebox.showinfo("Import Complete", "No new unique customers found in invoice records.")
