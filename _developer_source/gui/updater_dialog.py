"""
Updates & Data Migration Assistant Dialog
Provides:
1. Version status & Master Vault inspection.
2. 1-click automatic discovery & merge of past invoices and customers from previous versions.
3. Custom folder import (e.g., from old backup, USB, or another computer).
4. 1-click complete data backup (.zip export).
5. Version upgrade instructions.
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from typing import Optional, Callable

from core.migration_manager import (
    APP_VERSION,
    get_master_vault_dir,
    get_active_invoices_dir,
    scan_and_merge_previous_versions,
    import_from_custom_directory,
    create_full_backup_zip,
    load_version_ledger
)
from core.records_manager import load_all_records
from core.customer_manager import load_customers
from gui.window_utils import center_window
from core.cloud_updater import (
    check_for_updates,
    download_cloud_file,
    run_installer_safely,
    find_local_installer,
    get_cloud_config,
    save_cloud_config,
    DEFAULT_MANIFEST_URL
)


class UpdaterDialog(tk.Toplevel):
    def __init__(self, parent, on_data_updated: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.on_data_updated = on_data_updated
        self.title("Updates & Data Migration Assistant")
        self.geometry("760x560")
        self.minsize(640, 420)
        self.transient(parent)
        self.grab_set()

        self.style = ttk.Style(self)
        try:
            self.style.configure("Treeview", font=("Segoe UI", 9), rowheight=28)
            self.style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), padding=(4, 4))
        except Exception:
            pass

        self._build_ui()
        self._refresh_stats()
        center_window(self, parent, 760, 560)

    def _build_ui(self):
        # 1. Pinned Bottom Actions Bar
        bot_bar = ttk.Frame(self, padding=(14, 10))
        bot_bar.pack(fill="x", side="bottom")

        self.lbl_status = ttk.Label(bot_bar, text="Ready. All previous versions can be scanned and merged.", font=("Segoe UI", 9))
        self.lbl_status.pack(side="left")

        btn_close = ttk.Button(bot_bar, text="Close", command=self.destroy, width=10)
        btn_close.pack(side="right", padx=(6, 0))

        ttk.Separator(self, orient="horizontal").pack(fill="x", side="bottom")

        # 2. Main Scrollable Container (guarantees all cards fit on any screen resolution)
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

        # Header Card: Version & Vault Status
        hdr_frame = ttk.LabelFrame(scroll_content, text="  Current Version & Master Vault Status  ", padding=12)
        hdr_frame.pack(fill="x", pady=(0, 10))

        hdr_row1 = ttk.Frame(hdr_frame)
        hdr_row1.pack(fill="x")

        ttk.Label(
            hdr_row1,
            text=f"Silver Premium Invoice Generator  v{APP_VERSION}",
            font=("Segoe UI", 12, "bold"),
            foreground="#1E3A8A"
        ).pack(side="left")

        self.lbl_version_badge = ttk.Label(
            hdr_row1,
            text=" ✓ Active & Up to Date ",
            font=("Segoe UI", 9, "bold"),
            foreground="#047857"
        )
        self.lbl_version_badge.pack(side="right")

        # Metrics Summary
        self.lbl_vault_info = ttk.Label(
            hdr_frame,
            text=f"• Master Vault: {get_master_vault_dir()}\n• Local Invoices Folder: {get_active_invoices_dir()}",
            font=("Segoe UI", 8),
            foreground="#475569"
        )
        self.lbl_vault_info.pack(anchor="w", pady=(6, 4))

        self.lbl_stats_summary = ttk.Label(
            hdr_frame,
            text="Loading records statistics...",
            font=("Segoe UI", 9, "bold"),
            foreground="#0f172a"
        )
        self.lbl_stats_summary.pack(anchor="w", pady=(2, 0))

        # Migration & Discovery Actions
        mig_frame = ttk.LabelFrame(scroll_content, text="  Previous Version Discovery & Auto-Merge  ", padding=12)
        mig_frame.pack(fill="x", pady=(0, 10))

        lbl_mig_desc = ttk.Label(
            mig_frame,
            text="If you previously used other folders (e.g. desktop portables, older versions, or another location),\n"
                 "the scanner automatically discovers past invoices, customers, and PDFs and links them into this version.",
            font=("Segoe UI", 9)
        )
        lbl_mig_desc.pack(anchor="w", pady=(0, 8))

        btn_row1 = ttk.Frame(mig_frame)
        btn_row1.pack(fill="x")

        btn_auto_scan = ttk.Button(
            btn_row1,
            text="🔍 Scan & Merge Previous Versions",
            command=self._on_auto_scan,
            width=32
        )
        btn_auto_scan.pack(side="left", padx=(0, 8))

        btn_custom_import = ttk.Button(
            btn_row1,
            text="📂 Import From Custom Folder...",
            command=self._on_custom_import,
            width=30
        )
        btn_custom_import.pack(side="left")

        # Backup & Export Card
        bak_frame = ttk.LabelFrame(scroll_content, text="  Data Backup & Disaster Recovery  ", padding=12)
        bak_frame.pack(fill="x", pady=(0, 10))

        lbl_bak_desc = ttk.Label(
            bak_frame,
            text="Export your entire invoice history, customer database, settings, and all PDF files\n"
                 "into a single consolidated ZIP archive for safekeeping or moving to a new computer.",
            font=("Segoe UI", 9)
        )
        lbl_bak_desc.pack(anchor="w", pady=(0, 8))

        btn_backup = ttk.Button(
            bak_frame,
            text="💾 Create Full Backup (.zip)",
            command=self._on_create_backup,
            width=28
        )
        btn_backup.pack(anchor="w")

        # Cloud & Online Updates Card
        cloud_frame = ttk.LabelFrame(scroll_content, text="  ☁️ Online Cloud & Automatic Updates  ", padding=12)
        cloud_frame.pack(fill="x", pady=(0, 10))

        lbl_cloud_desc = ttk.Label(
            cloud_frame,
            text="Check online cloud repositories (GitHub, web server, or custom cloud link) for the latest release.\n"
                 "Downloads and installs updates automatically with real-time progress.",
            font=("Segoe UI", 9)
        )
        lbl_cloud_desc.pack(anchor="w", pady=(0, 8))

        row_c_url = ttk.Frame(cloud_frame)
        row_c_url.pack(fill="x", pady=(0, 6))

        ttk.Label(row_c_url, text="Cloud Manifest URL:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
        self.var_cloud_url = tk.StringVar(value=get_cloud_config().get("manifest_url", DEFAULT_MANIFEST_URL))
        self.entry_cloud_url = ttk.Entry(row_c_url, textvariable=self.var_cloud_url, font=("Segoe UI", 9))
        self.entry_cloud_url.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_check_online = ttk.Button(row_c_url, text="🔍 Check Cloud", command=self._on_check_cloud)
        self.btn_check_online.pack(side="right")

        self.lbl_cloud_status = ttk.Label(
            cloud_frame,
            text=f"Current version v{APP_VERSION}. Click 'Check Cloud' to query online servers.",
            font=("Segoe UI", 8),
            foreground="#475569"
        )
        self.lbl_cloud_status.pack(anchor="w", pady=(0, 6))

        self.cloud_prog = ttk.Progressbar(cloud_frame, mode="determinate")
        self.cloud_prog.pack(fill="x", pady=(0, 6))
        self.cloud_prog["value"] = 0

        row_c_btns = ttk.Frame(cloud_frame)
        row_c_btns.pack(fill="x")

        self.btn_cloud_download = ttk.Button(
            row_c_btns,
            text="☁️ Download Cloud Update",
            command=self._on_download_cloud,
            state="disabled",
            width=28
        )
        self.btn_cloud_download.pack(side="left", padx=(0, 8))

        self.btn_open_standalone = ttk.Button(
            row_c_btns,
            text="⚡ Open Dedicated Updater Tool",
            command=self._open_standalone_updater,
            width=28
        )
        self.btn_open_standalone.pack(side="left")

        # Installed Application Upgrade Section
        inst_frame = ttk.LabelFrame(scroll_content, text="  Installed Application Upgrade & Sync  ", padding=12)
        inst_frame.pack(fill="x", pady=(0, 10))

        self.lbl_installed_info = ttk.Label(
            inst_frame,
            text="Checking for installed version on this PC...",
            font=("Segoe UI", 9)
        )
        self.lbl_installed_info.pack(anchor="w", pady=(0, 8))

        btn_row_inst = ttk.Frame(inst_frame)
        btn_row_inst.pack(fill="x")

        self.btn_update_installed = ttk.Button(
            btn_row_inst,
            text="🚀 Update Installed App on PC",
            command=self._on_update_installed_app,
            width=32
        )
        self.btn_update_installed.pack(side="left", padx=(0, 8))

        self.btn_launch_installed = ttk.Button(
            btn_row_inst,
            text="▶ Launch Installed App",
            command=self._on_launch_installed_app,
            width=24
        )
        self.btn_launch_installed.pack(side="left")

        # Upgrade Information Guide
        guide_frame = ttk.LabelFrame(scroll_content, text="  How Future Updates Work  ", padding=12)
        guide_frame.pack(fill="both", expand=True)

        txt_guide = (
            "• Zero Data Loss Guarantee: Your invoices, customers, and settings are mirrored to the permanent\n"
            "  Windows Master Vault. Even if you delete or replace an old portable folder, your data remains safe.\n"
            "• Portable Updates: To upgrade, simply place the newly compiled .exe into your desired folder.\n"
            "  The app automatically migrates and preserves all previous records upon startup.\n"
            "• Setup Installer & Updater: Use 'Update Installed App' or run the Setup installer to sync everything."
        )
        ttk.Label(guide_frame, text=txt_guide, font=("Segoe UI", 8), foreground="#334155", justify="left").pack(anchor="w")

    def _refresh_stats(self):
        records = load_all_records()
        customers = load_customers()
        invoices_dir = get_active_invoices_dir()

        pdf_count = 0
        if os.path.exists(invoices_dir):
            try:
                pdf_count = len([f for f in os.listdir(invoices_dir) if f.lower().endswith(".pdf")])
            except Exception:
                pass

        self.lbl_stats_summary.configure(
            text=f"📊 Status: {len(records)} Invoices Recorded | {len(customers)} Customer Accounts | {pdf_count} PDF Documents Archived"
        )

        # Detect installed application
        from core.installed_updater import find_installed_app_directory
        inst = find_installed_app_directory()
        if inst:
            self.lbl_installed_info.configure(
                text=f"• Installed App Path: {inst}\n• Click below to update the installed app to v{APP_VERSION} and sync all data.",
                foreground="#047857"
            )
            self.btn_update_installed.configure(state="normal")
            self.btn_launch_installed.configure(state="normal")
        else:
            self.lbl_installed_info.configure(
                text="• No installed application detected in Program Files or Local AppData.",
                foreground="#64748B"
            )
            self.btn_update_installed.configure(state="disabled")
            self.btn_launch_installed.configure(state="disabled")

    def _on_auto_scan(self):
        self.lbl_status.configure(text="Scanning system for previous versions and unindexed invoices...")
        self.update_idletasks()

        res = scan_and_merge_previous_versions()
        self._refresh_stats()

        if self.on_data_updated:
            self.on_data_updated()

        tot = res.get("total_invoices", 0)
        scanned = res.get("locations_scanned_count", 0)
        pdfs = res.get("total_pdfs", 0)
        recovered = res.get("recovered_from_pdf", 0)

        msg = (
            f"✓ Scan & Consolidation Complete!\n\n"
            f"• Scanned Locations: {scanned} directories\n"
            f"• Total Unified Invoices: {tot}\n"
            f"• Total PDF Documents Preserved: {pdfs}\n"
        )
        if recovered > 0:
            msg += f"• Orphaned Invoices Recovered from PDFs: {recovered}\n"

        msg += "\nAll previous records are now synchronized and visible in History."
        messagebox.showinfo("Migration Complete", msg)
        self.lbl_status.configure(text=f"✓ Merged {tot} invoices from {scanned} locations.")

    def _on_custom_import(self):
        folder = filedialog.askdirectory(
            parent=self,
            title="Select Folder Containing Previous Invoices or PDF Archive"
        )
        if not folder:
            return

        self.lbl_status.configure(text=f"Importing from {folder}...")
        self.update_idletasks()

        res = import_from_custom_directory(folder)
        self._refresh_stats()

        if self.on_data_updated:
            self.on_data_updated()

        tot = res.get("total_invoices", 0)
        messagebox.showinfo(
            "Import Successful",
            f"Successfully imported records from:\n{folder}\n\nTotal Invoices now recorded: {tot}"
        )
        self.lbl_status.configure(text=f"✓ Imported from {os.path.basename(folder)}. Total: {tot} invoices.")

    def _on_create_backup(self):
        default_name = f"SilverPremium_Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        dest = filedialog.asksaveasfilename(
            parent=self,
            title="Save Full Invoices & Data Backup",
            initialfile=default_name,
            defaultextension=".zip",
            filetypes=[("ZIP Archive", "*.zip"), ("All Files", "*.*")]
        )
        if not dest:
            return

        self.lbl_status.configure(text="Creating consolidated ZIP backup...")
        self.update_idletasks()

        success = create_full_backup_zip(dest)
        if success and os.path.exists(dest):
            size_mb = os.path.getsize(dest) / (1024 * 1024)
            open_folder = messagebox.askyesno(
                "Backup Created",
                f"Full backup successfully created ({size_mb:.2f} MB):\n{dest}\n\nWould you like to open the backup folder?"
            )
            if open_folder:
                try:
                    os.startfile(os.path.dirname(dest))
                except Exception:
                    pass
            self.lbl_status.configure(text=f"✓ Backup saved: {os.path.basename(dest)}")
        else:
            messagebox.showerror("Backup Failed", "Could not create backup archive. Please check permissions.")
            self.lbl_status.configure(text="Error creating backup.")

    def _on_check_cloud(self):
        url = self.var_cloud_url.get().strip()
        save_cloud_config({"enabled": True, "manifest_url": url})

        self.lbl_cloud_status.configure(text="Connecting to cloud update repository...", foreground="#1E3A8A")
        self.btn_check_online.configure(state="disabled")

        import threading
        def worker():
            res = check_for_updates(url)
            self.after(0, lambda: self._on_cloud_check_done(res))
        threading.Thread(target=worker, daemon=True).start()

    def _on_cloud_check_done(self, res: dict):
        self.btn_check_online.configure(state="normal")
        self.cloud_info = res
        if res.get("available"):
            remote_v = res.get("remote_version")
            self.lbl_cloud_status.configure(
                text=f"★ New version v{remote_v} available online! Click 'Download Cloud Update'.",
                foreground="#047857"
            )
            self.btn_cloud_download.configure(state="normal")
        elif res.get("success"):
            self.lbl_cloud_status.configure(
                text=f"✓ App is up to date! (v{APP_VERSION} matches cloud version).",
                foreground="#047857"
            )
        else:
            msg = res.get("message", "Cloud check failed.")
            self.lbl_cloud_status.configure(text=msg, foreground="#B45309")

    def _on_download_cloud(self):
        dl_url = getattr(self, "cloud_info", {}).get("installer_url") or getattr(self, "cloud_info", {}).get("portable_url")
        if not dl_url:
            messagebox.showinfo("No Download URL", "No download package URL was specified in the cloud manifest.")
            return

        self.btn_cloud_download.configure(state="disabled")
        self.lbl_cloud_status.configure(text="Downloading update package from cloud...", foreground="#1E3A8A")

        import threading
        def progress(dl, total, pct):
            self.after(0, lambda: self.cloud_prog.configure(value=pct))

        def worker():
            path = download_cloud_file(dl_url, progress_callback=progress)
            self.after(0, lambda: self._on_cloud_download_done(path))
        threading.Thread(target=worker, daemon=True).start()

    def _on_cloud_download_done(self, path: Optional[str]):
        if path and os.path.exists(path):
            self.cloud_prog["value"] = 100
            self.lbl_cloud_status.configure(
                text=f"✓ Download complete: {os.path.basename(path)} ready to install.",
                foreground="#047857"
            )
            if messagebox.askyesno(
                "Download Complete",
                f"Cloud update downloaded successfully:\n\n{os.path.basename(path)}\n\n"
                "Would you like to run the installer now to upgrade?"
            ):
                run_installer_safely(path)
                self.destroy()
        else:
            self.lbl_cloud_status.configure(text="Download failed. Please check internet connection.", foreground="#DC2626")
            self.btn_cloud_download.configure(state="normal")

    def _open_standalone_updater(self):
        import subprocess
        up_script = os.path.join(os.path.dirname(__file__), "updater_standalone.py")
        if os.path.exists(up_script):
            subprocess.Popen([sys.executable, up_script])
        else:
            home = os.path.expanduser("~")
            up_exe = os.path.join(home, "OneDrive", "Desktop", "Silver Premium Updater.exe")
            if os.path.exists(up_exe):
                os.startfile(up_exe)

    def _on_update_installed_app(self):
        installer = find_local_installer()
        if installer and os.path.exists(installer):
            if messagebox.askyesno(
                "Upgrade Installed Application",
                f"This will launch the Windows Setup Installer:\n\n{os.path.basename(installer)}\n\n"
                f"It will upgrade 'C:\\Program Files (x86)\\Silver Premium Invoice Generator' to v{APP_VERSION} "
                "with standard Windows Administrator elevation.\n\nAll customer accounts, defaults, and invoices are 100% preserved.\n\nProceed?"
            ):
                self.lbl_status.configure(text=f"Launching setup installer: {os.path.basename(installer)}...")
                success = run_installer_safely(installer)
                if success:
                    self.destroy()
                else:
                    messagebox.showerror("Error", "Could not start Windows Setup installer.")
            return

        from core.installed_updater import find_installed_app_directory, update_installed_version
        inst_dir = find_installed_app_directory()
        if not inst_dir:
            messagebox.showinfo("Not Found", "No installed application directory was detected on this PC.")
            return

        res = update_installed_version(inst_dir)
        if res.get("status") == "success":
            messagebox.showinfo("Update Complete", res.get("message", "Application updated successfully!"))
            self.lbl_status.configure(text=f"✓ Installed application updated to v{APP_VERSION}.")
            self._refresh_stats()
            if self.on_data_updated:
                self.on_data_updated()
        else:
            messagebox.showwarning("Notice", res.get("message", "Could not update files directly."))

    def _on_launch_installed_app(self):
        from core.installed_updater import find_installed_app_directory
        inst_dir = find_installed_app_directory()
        if not inst_dir:
            messagebox.showwarning("Notice", "Installed application folder not found.")
            return

        exe = os.path.join(inst_dir, "Silver Premium Invoice Generator.exe")
        if os.path.exists(exe):
            try:
                os.startfile(exe)
                self.lbl_status.configure(text=f"✓ Launched: {exe}")
            except Exception as e:
                messagebox.showerror("Launch Error", f"Could not launch application:\n{e}")
        else:
            messagebox.showerror("Not Found", f"Executable not found at:\n{exe}")
