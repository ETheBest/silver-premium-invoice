"""
Invoice History and Tax (VAT) Analytics View
Features:
- Multi-parameter filtering: Company/Profile, Year, Month, and Search Query.
- Real-time VAT, Taxable Subtotal, and Grand Total KPI metric cards.
- Dual-tab interface:
    1. Invoices List with explicit Subtotal, VAT, and Grand Total columns.
    2. Company VAT Breakdown showing total taxes paid per profile.
- 1-Click drill-down: double-click a company in the summary to filter their invoices.
- CSV export for both raw invoices and aggregated Company VAT Tax reports.
"""
import os
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable

from core.records_manager import (
    load_all_records,
    get_invoices_dir,
    get_records_csv_path,
    open_pdf_file,
    open_invoices_folder,
    delete_invoice_record,
    get_available_years,
    filter_records,
    calculate_vat_summary,
    get_company_vat_breakdown,
    export_vat_summary_csv
)
from core.customer_manager import load_customers
from gui.window_utils import center_window


MONTH_OPTIONS = [
    "All Months",
    "01 - Jan",
    "02 - Feb",
    "03 - Mar",
    "04 - Apr",
    "05 - May",
    "06 - Jun",
    "07 - Jul",
    "08 - Aug",
    "09 - Sep",
    "10 - Oct",
    "11 - Nov",
    "12 - Dec"
]


class HistoryDialog(tk.Toplevel):
    def __init__(
        self,
        parent,
        on_records_changed: Optional[Callable[[str], None]] = None,
        initial_company: str = "",
        initial_tab: int = 0
    ):
        super().__init__(parent)
        self.on_records_changed = on_records_changed
        self.title("Invoice History & VAT Tax Analytics")
        self.geometry("1060x580")
        self.minsize(880, 460)
        self.transient(parent)
        self.grab_set()

        self.records: List[Dict[str, Any]] = []
        self.filtered_records: List[Dict[str, Any]] = []
        self.company_breakdown: List[Dict[str, Any]] = []
        self.initial_company = initial_company
        self.initial_tab = initial_tab

        # Style Treeview with adequate rowheight to prevent text from being sliced/truncated
        self.style = ttk.Style(self)
        try:
            self.style.configure("Treeview", font=("Segoe UI", 9), rowheight=28)
            self.style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), padding=(4, 4))
        except Exception:
            pass

        self._build_ui()
        self._load_records()

        if self.initial_company:
            self._select_company(self.initial_company)

        if self.initial_tab in (0, 1):
            self.notebook.select(self.initial_tab)

        center_window(self, parent, 1060, 580)

    def _build_ui(self):
        # 1. Pinned Bottom Actions Bar (packed first to guarantee visibility)
        bot_frame = ttk.Frame(self, padding=(14, 10))
        bot_frame.pack(fill="x", side="bottom")

        self.lbl_status = ttk.Label(
            bot_frame,
            text="Loading records...",
            font=("Segoe UI", 9)
        )
        self.lbl_status.pack(side="left")

        btn_close = ttk.Button(bot_frame, text="Close", command=self.destroy, width=10)
        btn_close.pack(side="right", padx=(8, 0))

        self.btn_open_pdf = ttk.Button(
            bot_frame,
            text="Open Selected PDF",
            command=self._open_selected_pdf
        )
        self.btn_open_pdf.pack(side="right", padx=(8, 0))

        self.btn_delete = ttk.Button(
            bot_frame,
            text="Delete Invoice",
            command=self._on_delete_invoice
        )
        self.btn_delete.pack(side="right", padx=(8, 0))

        ttk.Separator(self, orient="horizontal").pack(fill="x", side="bottom")

        # 2. Filter Toolbar (Top: 2-Row Responsive Layout)
        filter_card = ttk.LabelFrame(self, text="  Filters & Period Selection  ", padding=(12, 6))
        filter_card.pack(fill="x", side="top", padx=12, pady=(8, 4))

        # Row 1: Search & Filter Inputs
        row_filters = ttk.Frame(filter_card)
        row_filters.pack(fill="x", expand=True, pady=(0, 4))

        # Search Query
        ttk.Label(row_filters, text="Search:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        self.var_search = tk.StringVar()
        self.var_search.trace_add("write", lambda *args: self._apply_filters())
        self.entry_search = ttk.Entry(row_filters, textvariable=self.var_search, width=16, font=("Segoe UI", 9))
        self.entry_search.pack(side="left", padx=(0, 10))

        # Company / Profile Filter
        ttk.Label(row_filters, text="Company / Profile:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        self.var_company = tk.StringVar(value="All Companies")
        self.cb_company = ttk.Combobox(
            row_filters,
            textvariable=self.var_company,
            state="readonly",
            width=20,
            font=("Segoe UI", 9)
        )
        self.cb_company.pack(side="left", padx=(0, 10))
        self.cb_company.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

        # Year Filter
        ttk.Label(row_filters, text="Year:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        self.var_year = tk.StringVar(value="All Years")
        self.cb_year = ttk.Combobox(
            row_filters,
            textvariable=self.var_year,
            state="readonly",
            width=9,
            font=("Segoe UI", 9)
        )
        self.cb_year.pack(side="left", padx=(0, 10))
        self.cb_year.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

        # Month Filter
        ttk.Label(row_filters, text="Month:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        self.var_month = tk.StringVar(value="All Months")
        self.cb_month = ttk.Combobox(
            row_filters,
            textvariable=self.var_month,
            values=MONTH_OPTIONS,
            state="readonly",
            width=11,
            font=("Segoe UI", 9)
        )
        self.cb_month.pack(side="left", padx=(0, 8))
        self.cb_month.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

        # Reset Button
        btn_reset = ttk.Button(row_filters, text="↺ Reset", width=8, command=self._reset_filters)
        btn_reset.pack(side="left")

        # Row 2: Action Buttons Bar
        row_actions = ttk.Frame(filter_card)
        row_actions.pack(fill="x", expand=True, pady=(2, 0))

        ttk.Label(
            row_actions,
            text="Export & Reporting Tools:",
            font=("Segoe UI", 8),
            foreground="#64748B"
        ).pack(side="left")

        btn_folder = ttk.Button(row_actions, text="📂 Open Invoices Folder", command=open_invoices_folder)
        btn_folder.pack(side="right", padx=(4, 0))

        btn_excel = ttk.Button(row_actions, text="📄 All Records (CSV)", command=self._open_in_excel)
        btn_excel.pack(side="right", padx=(4, 0))

        btn_export_vat = ttk.Button(row_actions, text="📊 Export VAT Report", command=self._export_vat_report)
        btn_export_vat.pack(side="right", padx=(4, 0))

        # 3. KPI Metrics Summary Cards Banner
        self._build_kpi_banner()

        # 4. Notebook for Invoices List vs Company VAT Breakdown
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(4, 8))

        # Tab 1: Invoices List
        tab_invoices = ttk.Frame(self.notebook, padding=(6, 6))
        self.notebook.add(tab_invoices, text="  📋 Invoices Records  ")
        self._build_invoices_table(tab_invoices)

        # Tab 2: Company VAT Breakdown
        tab_breakdown = ttk.Frame(self.notebook, padding=(6, 6))
        self.notebook.add(tab_breakdown, text="  🏢 Company VAT Breakdown  ")
        self._build_company_breakdown_table(tab_breakdown)

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _build_kpi_banner(self):
        kpi_frame = ttk.Frame(self, padding=(12, 4))
        kpi_frame.pack(fill="x", padx=12, pady=(0, 4))

        # Configure 4 columns
        for c in range(4):
            kpi_frame.columnconfigure(c, weight=1, uniform="kpi")

        # Tile 1: Total Invoices
        t1 = ttk.LabelFrame(kpi_frame, text=" Total Invoices ", padding=(8, 4))
        t1.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.lbl_kpi_count = ttk.Label(t1, text="0", font=("Segoe UI", 12, "bold"), foreground="#1e293b")
        self.lbl_kpi_count.pack(anchor="center")

        # Tile 2: Taxable Subtotal
        t2 = ttk.LabelFrame(kpi_frame, text=" Taxable Subtotal ", padding=(8, 4))
        t2.grid(row=0, column=1, sticky="ew", padx=4)
        self.lbl_kpi_subtotal = ttk.Label(t2, text="AED 0.00", font=("Segoe UI", 12, "bold"), foreground="#334155")
        self.lbl_kpi_subtotal.pack(anchor="center")

        # Tile 3: Total VAT (Highlighted)
        t3 = ttk.LabelFrame(kpi_frame, text=" ★ Total VAT 5% Paid ", padding=(8, 4))
        t3.grid(row=0, column=2, sticky="ew", padx=4)
        self.lbl_kpi_vat = ttk.Label(t3, text="AED 0.00", font=("Segoe UI", 13, "bold"), foreground="#047857")
        self.lbl_kpi_vat.pack(anchor="center")

        # Tile 4: Grand Total
        t4 = ttk.LabelFrame(kpi_frame, text=" Grand Total Invoiced ", padding=(8, 4))
        t4.grid(row=0, column=3, sticky="ew", padx=(4, 0))
        self.lbl_kpi_grand = ttk.Label(t4, text="AED 0.00", font=("Segoe UI", 12, "bold"), foreground="#0f172a")
        self.lbl_kpi_grand.pack(anchor="center")

    def _build_invoices_table(self, parent):
        cols = ("invoice_no", "date", "client", "company", "subtotal", "vat", "total", "filename")
        self.tree_invoices = ttk.Treeview(parent, columns=cols, show="headings", selectmode="browse")

        self.tree_invoices.heading("invoice_no", text="Invoice #")
        self.tree_invoices.heading("date", text="Date")
        self.tree_invoices.heading("client", text="Client / Reference")
        self.tree_invoices.heading("company", text="Customer Company")
        self.tree_invoices.heading("subtotal", text="Subtotal (AED)")
        self.tree_invoices.heading("vat", text="VAT 5% (AED)")
        self.tree_invoices.heading("total", text="Grand Total (AED)")
        self.tree_invoices.heading("filename", text="Saved File")

        self.tree_invoices.column("invoice_no", width=85, anchor="center")
        self.tree_invoices.column("date", width=105, anchor="center")
        self.tree_invoices.column("client", width=180, anchor="w")
        self.tree_invoices.column("company", width=190, anchor="w")
        self.tree_invoices.column("subtotal", width=105, anchor="e")
        self.tree_invoices.column("vat", width=95, anchor="e")
        self.tree_invoices.column("total", width=110, anchor="e")
        self.tree_invoices.column("filename", width=180, anchor="w")

        # Scrollbars
        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.tree_invoices.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=self.tree_invoices.xview)
        self.tree_invoices.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree_invoices.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        # Double-click and keys
        self.tree_invoices.bind("<Double-1>", lambda e: self._open_selected_pdf())
        self.tree_invoices.bind("<Return>", lambda e: self._open_selected_pdf())
        self.tree_invoices.bind("<Delete>", lambda e: self._on_delete_invoice())
        self.tree_invoices.bind("<BackSpace>", lambda e: self._on_delete_invoice())

        # Context menu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="📄 Open PDF", command=self._open_selected_pdf)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Delete from History", command=self._on_delete_invoice)
        self.tree_invoices.bind("<Button-3>", self._show_context_menu)

    def _build_company_breakdown_table(self, parent):
        # Top toolbar in Tab 2
        top_bar = ttk.Frame(parent)
        top_bar.pack(fill="x", side="top", pady=(0, 6))

        ttk.Label(
            top_bar,
            text="Overview of VAT taxes and totals grouped per customer profile / company:",
            font=("Segoe UI", 9, "italic")
        ).pack(side="left")

        btn_view_invoices = ttk.Button(
            top_bar,
            text="🔍 View Company Invoices",
            command=self._drill_down_selected_company
        )
        btn_view_invoices.pack(side="right", padx=(4, 0))

        # Treeview container
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill="both", expand=True)

        cols = ("company", "count", "subtotal", "vat", "total", "latest")
        self.tree_breakdown = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")

        self.tree_breakdown.heading("company", text="Customer / Company Profile")
        self.tree_breakdown.heading("count", text="Invoices")
        self.tree_breakdown.heading("subtotal", text="Taxable Subtotal (AED)")
        self.tree_breakdown.heading("vat", text="Total VAT 5% (AED)")
        self.tree_breakdown.heading("total", text="Grand Total (AED)")
        self.tree_breakdown.heading("latest", text="Latest Invoice Date")

        self.tree_breakdown.column("company", width=290, anchor="w")
        self.tree_breakdown.column("count", width=85, anchor="center")
        self.tree_breakdown.column("subtotal", width=140, anchor="e")
        self.tree_breakdown.column("vat", width=140, anchor="e")
        self.tree_breakdown.column("total", width=140, anchor="e")
        self.tree_breakdown.column("latest", width=130, anchor="center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree_breakdown.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree_breakdown.xview)
        self.tree_breakdown.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree_breakdown.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Double-click company to filter invoices list
        self.tree_breakdown.bind("<Double-1>", lambda e: self._drill_down_selected_company())
        self.tree_breakdown.bind("<Return>", lambda e: self._drill_down_selected_company())

    def _show_context_menu(self, event):
        item = self.tree_invoices.identify_row(event.y)
        if item:
            self.tree_invoices.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def _load_records(self):
        """Loads records and populates filter options."""
        self.records = load_all_records()
        try:
            self.records.sort(key=lambda r: int(r.get("invoice_no", 0)), reverse=True)
        except Exception:
            pass

        # Populate Years
        years = get_available_years(self.records)
        year_options = ["All Years"] + years
        self.cb_year.configure(values=year_options)
        if self.var_year.get() not in year_options:
            self.var_year.set("All Years")

        # Populate Companies
        companies = set()
        for r in self.records:
            comp = str(r.get("customer_company", "")).strip()
            if comp:
                companies.add(comp)
        # Also include registered customers from customer manager
        try:
            for c in load_customers():
                comp = str(c.get("company_name", "")).strip()
                if comp:
                    companies.add(comp)
        except Exception:
            pass

        company_options = ["All Companies"] + sorted(list(companies), key=lambda s: s.lower())
        self.cb_company.configure(values=company_options)
        if self.var_company.get() not in company_options:
            self.var_company.set("All Companies")

        self._apply_filters()

    def _reset_filters(self):
        self.var_search.set("")
        self.var_company.set("All Companies")
        self.var_year.set("All Years")
        self.var_month.set("All Months")
        self._apply_filters()

    def _select_company(self, company_name: str):
        if not company_name:
            return
        vals = self.cb_company.cget("values")
        for v in vals:
            if v.lower() == company_name.lower():
                self.var_company.set(v)
                self._apply_filters()
                return
        # If not exact in list, set it anyway
        self.var_company.set(company_name)
        self._apply_filters()

    def _apply_filters(self):
        query = self.var_search.get().strip()
        comp = self.var_company.get().strip()
        year = self.var_year.get().strip()
        month_raw = self.var_month.get().strip()

        # Parse month number
        month = ""
        if month_raw and month_raw != "All Months":
            try:
                month = str(int(month_raw.split("-")[0].strip()))
            except Exception:
                month = ""

        # 1. Filter Records
        self.filtered_records = filter_records(
            self.records,
            query=query,
            company=comp,
            year=year,
            month=month
        )

        # 2. Update KPI Metrics
        summary = calculate_vat_summary(self.filtered_records)
        self.lbl_kpi_count.configure(text=f"{summary['invoice_count']} Invoices")
        self.lbl_kpi_subtotal.configure(text=f"AED {summary['total_subtotal']:,.2f}")
        self.lbl_kpi_vat.configure(text=f"AED {summary['total_vat']:,.2f}")
        self.lbl_kpi_grand.configure(text=f"AED {summary['total_grand']:,.2f}")

        # 3. Populate Invoices Table
        self.tree_invoices.delete(*self.tree_invoices.get_children())
        for rec in self.filtered_records:
            inv_no = str(rec.get("invoice_no", ""))
            date_str = str(rec.get("date", ""))
            client = str(rec.get("client_name", ""))
            company_str = str(rec.get("customer_company", ""))
            subtotal = float(rec.get("subtotal", 0.0) or 0.0)
            vat_val = float(rec.get("vat_total", 0.0) or 0.0)
            total_val = float(rec.get("grand_total", 0.0) or 0.0)
            fname = str(rec.get("filename", ""))

            self.tree_invoices.insert(
                "",
                "end",
                iid=f"inv_{inv_no}_{fname}",
                values=(
                    inv_no,
                    date_str,
                    client,
                    company_str,
                    f"{subtotal:,.2f}",
                    f"{vat_val:,.2f}",
                    f"{total_val:,.2f}",
                    fname
                )
            )

        # 4. Populate Company VAT Breakdown Table
        self.company_breakdown = get_company_vat_breakdown(self.filtered_records)
        self.tree_breakdown.delete(*self.tree_breakdown.get_children())
        for cdata in self.company_breakdown:
            c_name = cdata["company_name"]
            c_count = cdata["invoice_count"]
            c_sub = cdata["total_subtotal"]
            c_vat = cdata["total_vat"]
            c_grand = cdata["total_grand"]
            c_latest = cdata["latest_date"]

            self.tree_breakdown.insert(
                "",
                "end",
                iid=f"comp_{c_name}",
                values=(
                    c_name,
                    c_count,
                    f"{c_sub:,.2f}",
                    f"{c_vat:,.2f}",
                    f"{c_grand:,.2f}",
                    c_latest
                )
            )

        # 5. Status Label Update
        filter_desc = []
        if comp and comp != "All Companies":
            filter_desc.append(f"Company: {comp}")
        if year and year != "All Years":
            filter_desc.append(f"Year: {year}")
        if month_raw and month_raw != "All Months":
            filter_desc.append(f"Month: {month_raw}")
        if query:
            filter_desc.append(f"Search: '{query}'")

        active_filter_str = f" ({', '.join(filter_desc)})" if filter_desc else ""
        self.lbl_status.configure(
            text=f"Showing {summary['invoice_count']} of {len(self.records)} invoice(s){active_filter_str} | Total VAT: AED {summary['total_vat']:,.2f}"
        )

    def _on_tab_changed(self, event):
        tab_idx = self.notebook.index("current")
        # Disable/enable delete and open PDF buttons according to active tab
        if tab_idx == 0:
            self.btn_open_pdf.configure(state="normal")
            self.btn_delete.configure(state="normal")
        else:
            self.btn_open_pdf.configure(state="disabled")
            self.btn_delete.configure(state="disabled")

    def _drill_down_selected_company(self):
        selected = self.tree_breakdown.selection()
        if not selected:
            messagebox.showinfo("Select Company", "Please select a company from the breakdown table.")
            return

        values = self.tree_breakdown.item(selected[0], "values")
        if not values:
            return
        company_name = values[0]

        # Select this company in the filter and switch to Invoices tab
        self._select_company(company_name)
        self.notebook.select(0)

    def _open_selected_pdf(self):
        selected = self.tree_invoices.selection()
        if not selected:
            messagebox.showinfo("Select Invoice", "Please select an invoice from the list to view.")
            return

        values = self.tree_invoices.item(selected[0], "values")
        if not values:
            return

        filename = values[7]
        full_path = os.path.join(get_invoices_dir(), filename)
        if not os.path.exists(full_path):
            messagebox.showerror("File Not Found", f"Could not locate PDF:\n{full_path}")
            return

        open_pdf_file(full_path)

    def _on_delete_invoice(self):
        selected = self.tree_invoices.selection()
        if not selected:
            messagebox.showinfo("Select Invoice", "Please select an invoice from the list to delete.")
            return

        values = self.tree_invoices.item(selected[0], "values")
        if not values:
            return

        inv_no, date_str, client, company, sub_str, vat_str, total_str, fname = values

        confirm = messagebox.askyesno(
            "Confirm Delete Invoice",
            f"Are you sure you want to delete Invoice #{inv_no} from history?\n\n"
            f"• Client: {client}\n"
            f"• Company: {company}\n"
            f"• VAT 5%: AED {vat_str}\n"
            f"• Grand Total: AED {total_str}\n"
            f"• File: {fname}\n\n"
            f"This will remove it from the archive and delete the file so you can create a corrected invoice with #{inv_no}."
        )
        if not confirm:
            return

        delete_invoice_record(inv_no, delete_pdf=True)
        self._load_records()
        self.lbl_status.configure(text=f"✓ Invoice #{inv_no} deleted. You can now re-issue #{inv_no}.")

        if self.on_records_changed:
            self.on_records_changed(inv_no)

    def _open_in_excel(self):
        csv_path = get_records_csv_path()
        if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
            os.startfile(csv_path)
        else:
            messagebox.showinfo("No History Yet", "No invoices have been recorded yet. Generate an invoice to begin!")

    def _export_vat_report(self):
        if not self.company_breakdown:
            messagebox.showinfo("No Data", "No VAT records available for the selected filters.")
            return

        default_name = f"VAT_Tax_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        invoices_folder = get_invoices_dir()
        initial_file = os.path.join(invoices_folder, default_name)

        filepath = filedialog.asksaveasfilename(
            parent=self,
            title="Export Company VAT Tax Report",
            initialdir=invoices_folder,
            initialfile=default_name,
            defaultextension=".csv",
            filetypes=[("CSV Spreadsheet", "*.csv"), ("All Files", "*.*")]
        )
        if not filepath:
            return

        success = export_vat_summary_csv(self.company_breakdown, filepath)
        if success:
            open_now = messagebox.askyesno(
                "Export Successful",
                f"VAT Report successfully exported to:\n{filepath}\n\nWould you like to open it now in Excel?"
            )
            if open_now:
                try:
                    os.startfile(filepath)
                except Exception as e:
                    messagebox.showerror("Error", f"Could not open file: {e}")
        else:
            messagebox.showerror("Export Failed", "Could not export VAT report. Please check file permissions.")
