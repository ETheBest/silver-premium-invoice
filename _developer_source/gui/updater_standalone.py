"""
Silver Premium - Standalone Cloud & System Updater GUI
Provides a visual interface to:
1. Check for online cloud updates (GitHub, cloud servers, or custom URLs).
2. Download and verify online cloud update packages with a real-time progress bar.
3. 1-Click upgrade the installed application in Program Files with zero data loss.
4. Manage backups and Master Vault synchronization.
"""
from __future__ import annotations
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from typing import Dict, Any, Optional, Callable, List

# Add parent directory to sys.path so modules resolve whether run standalone or bundled
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from core.migration_manager import (
    APP_VERSION,
    get_master_vault_dir,
    get_active_invoices_dir,
    scan_and_merge_previous_versions,
    create_full_backup_zip
)
from core.cloud_updater import (
    check_for_updates,
    download_cloud_file,
    run_installer_safely,
    find_local_installer,
    get_cloud_config,
    save_cloud_config,
    DEFAULT_MANIFEST_URL
)
from gui.window_utils import center_window


class StandaloneUpdaterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Silver Premium - Cloud & System Updater v{APP_VERSION}")
        self.geometry("740x580")
        self.minsize(640, 460)

        self.cloud_info = {}
        self.downloaded_update_path = None

        self._configure_styles()
        self._build_ui()
        center_window(self, width=740, height=580)

        # Automatically check for updates on startup in background
        self.after(300, self._start_async_check)

    def _configure_styles(self):
        self.style = ttk.Style(self)
        try:
            available = self.style.theme_names()
            if "vista" in available:
                self.style.theme_use("vista")
            elif "clam" in available:
                self.style.theme_use("clam")
        except Exception:
            pass

        try:
            self.style.configure("Primary.TButton", font=("Segoe UI", 9, "bold"), padding=(8, 4))
            self.style.configure("TLabelframe.Label", font=("Segoe UI", 9, "bold"))
        except Exception:
            pass

    def _build_ui(self):
        # Header banner
        hdr = ttk.Frame(self, padding=(16, 12))
        hdr.pack(fill="x", side="top")

        ttk.Label(
            hdr,
            text="Silver Premium - Cloud & System Updater",
            font=("Segoe UI", 13, "bold"),
            foreground="#1E3A8A"
        ).pack(side="left")

        ttk.Label(
            hdr,
            text=f"Current Version: v{APP_VERSION}",
            font=("Segoe UI", 10, "bold"),
            foreground="#047857"
        ).pack(side="right")

        ttk.Separator(self, orient="horizontal").pack(fill="x")

        # Pinned Bottom Bar
        bot_bar = ttk.Frame(self, padding=(14, 10))
        bot_bar.pack(fill="x", side="bottom")

        btn_close = ttk.Button(bot_bar, text="Close", command=self.destroy, width=10)
        btn_close.pack(side="right", padx=(6, 0))

        btn_backup = ttk.Button(bot_bar, text="💾 Create Backup (.zip)", command=self._on_backup)
        btn_backup.pack(side="right", padx=(6, 0))

        btn_vault = ttk.Button(bot_bar, text="📂 Open Master Vault", command=self._open_vault)
        btn_vault.pack(side="left")

        ttk.Separator(self, orient="horizontal").pack(fill="x", side="bottom")

        # Scrollable middle area
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, highlightthickness=0)
        vscroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        content = ttk.Frame(canvas, padding=(16, 12))

        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_win = canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_win, width=e.width))
        canvas.configure(yscrollcommand=vscroll.set)

        canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y")

        def _on_mousewheel(event):
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.bind("<MouseWheel>", _on_mousewheel)

        # Card 1: Online Cloud Update
        cloud_card = ttk.LabelFrame(content, text=" ☁️ Online Cloud Updates ", padding=12)
        cloud_card.pack(fill="x", pady=(0, 10))

        row_url = ttk.Frame(cloud_card)
        row_url.pack(fill="x", pady=(0, 8))

        ttk.Label(row_url, text="Cloud Manifest URL:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
        self.var_url = tk.StringVar(value=get_cloud_config().get("manifest_url", DEFAULT_MANIFEST_URL))
        self.entry_url = ttk.Entry(row_url, textvariable=self.var_url, font=("Segoe UI", 9))
        self.entry_url.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_check_cloud = ttk.Button(row_url, text="🔍 Check Online", command=self._start_async_check)
        self.btn_check_cloud.pack(side="right")

        # Status & remote version badge
        self.lbl_cloud_status = ttk.Label(
            cloud_card,
            text="Press 'Check Online' to query the cloud update server.",
            font=("Segoe UI", 9),
            foreground="#334155"
        )
        self.lbl_cloud_status.pack(anchor="w", pady=(0, 6))

        # Progress bar
        self.prog_bar = ttk.Progressbar(cloud_card, mode="determinate")
        self.prog_bar.pack(fill="x", pady=(0, 6))
        self.prog_bar["value"] = 0

        # Action buttons for cloud download
        row_act = ttk.Frame(cloud_card)
        row_act.pack(fill="x")

        self.btn_download_cloud = ttk.Button(
            row_act,
            text="☁️ Download Cloud Update",
            command=self._start_async_download,
            state="disabled",
            style="Primary.TButton"
        )
        self.btn_download_cloud.pack(side="left", padx=(0, 8))

        self.btn_install_downloaded = ttk.Button(
            row_act,
            text="🚀 Install Downloaded Update",
            command=self._on_install_downloaded,
            state="disabled"
        )
        self.btn_install_downloaded.pack(side="left")

        # Card 2: 1-Click Upgrade Installed Version
        inst_card = ttk.LabelFrame(content, text=" 💻 Installed Application Direct Upgrade ", padding=12)
        inst_card.pack(fill="x", pady=(0, 10))

        lbl_inst_desc = ttk.Label(
            inst_card,
            text="Upgrades the permanent installation in 'C:\\Program Files (x86)\\Silver Premium Invoice Generator'\n"
                 "using the Windows Setup engine. Automatically elevates permissions via Windows UAC safely.",
            font=("Segoe UI", 9)
        )
        lbl_inst_desc.pack(anchor="w", pady=(0, 8))

        row_inst_btns = ttk.Frame(inst_card)
        row_inst_btns.pack(fill="x")

        self.btn_run_installer = ttk.Button(
            row_inst_btns,
            text="🚀 1-Click Upgrade Installed App on PC",
            command=self._on_upgrade_installed_direct,
            style="Primary.TButton"
        )
        self.btn_run_installer.pack(side="left", padx=(0, 8))

        self.btn_custom_setup = ttk.Button(
            row_inst_btns,
            text="📂 Select Setup.exe Manually...",
            command=self._on_select_custom_setup
        )
        self.btn_custom_setup.pack(side="left")

        # Card 3: Activity & Diagnostics Log
        log_card = ttk.LabelFrame(content, text=" 📋 Update Activity Log ", padding=8)
        log_card.pack(fill="both", expand=True)

        self.txt_log = tk.Text(log_card, height=7, font=("Consolas", 9), wrap="word", background="#F8FAFC")
        self.txt_log.pack(fill="both", expand=True)
        self._log(f"Updater initialized. Current version: v{APP_VERSION}")

    def _log(self, msg: str):
        self.txt_log.insert("end", f"• {msg}\n")
        self.txt_log.see("end")

    def _start_async_check(self):
        url = self.var_url.get().strip()
        save_cloud_config({"enabled": True, "manifest_url": url})

        self.lbl_cloud_status.configure(text="Connecting to cloud update repository...", foreground="#1E3A8A")
        self.btn_check_cloud.configure(state="disabled")
        self._log(f"Checking cloud manifest at: {url}")

        def worker():
            res = check_for_updates(url)
            self.after(0, lambda: self._on_check_completed(res))

        threading.Thread(target=worker, daemon=True).start()

    def _on_check_completed(self, res: Dict[str, Any]):
        self.btn_check_cloud.configure(state="normal")
        self.cloud_info = res

        if res.get("available"):
            remote_v = res.get("remote_version")
            self.lbl_cloud_status.configure(
                text=f"★ New version v{remote_v} is available online! Ready to download.",
                foreground="#047857"
            )
            self.btn_download_cloud.configure(state="normal")
            self._log(f"Cloud Update Available: v{remote_v} (Current: v{APP_VERSION})")
            if res.get("changelog"):
                self._log(f"Changelog:\n{res.get('changelog')}")
        elif res.get("success"):
            self.lbl_cloud_status.configure(
                text=f"✓ App is up to date! (v{APP_VERSION} matches cloud version).",
                foreground="#047857"
            )
            self._log(f"Cloud check confirmed: App is at latest version v{APP_VERSION}.")
        else:
            msg = res.get("message", "Could not connect to cloud.")
            self.lbl_cloud_status.configure(text=msg, foreground="#B45309")
            self._log(f"Note: {msg}")

        # Check local installer
        local_inst = find_local_installer()
        if local_inst:
            self._log(f"Local Setup Installer ready: {local_inst}")

    def _start_async_download(self):
        dl_url = self.cloud_info.get("installer_url") or self.cloud_info.get("portable_url")
        if not dl_url:
            messagebox.showinfo("No URL", "No download URL was provided in the cloud manifest.")
            return

        self.btn_download_cloud.configure(state="disabled")
        self.lbl_cloud_status.configure(text="Downloading update package from cloud...", foreground="#1E3A8A")
        self._log(f"Downloading from: {dl_url}")

        def progress(dl, total, pct):
            self.after(0, lambda: self._update_progress(dl, total, pct))

        def worker():
            path = download_cloud_file(dl_url, progress_callback=progress)
            self.after(0, lambda: self._on_download_completed(path))

        threading.Thread(target=worker, daemon=True).start()

    def _update_progress(self, dl, total, pct):
        self.prog_bar["value"] = pct
        mb_dl = dl / (1024 * 1024)
        mb_tot = total / (1024 * 1024)
        self.lbl_cloud_status.configure(
            text=f"Downloading: {mb_dl:.1f} MB / {mb_tot:.1f} MB ({pct:.0f}%)"
        )

    def _on_download_completed(self, path: Optional[str]):
        if path and os.path.exists(path):
            self.downloaded_update_path = path
            self.prog_bar["value"] = 100
            self.lbl_cloud_status.configure(
                text=f"✓ Download complete: {os.path.basename(path)} ready to install.",
                foreground="#047857"
            )
            self.btn_install_downloaded.configure(state="normal")
            self._log(f"Downloaded update saved to: {path}")

            if messagebox.askyesno(
                "Download Complete",
                f"Cloud update package downloaded successfully:\n\n{os.path.basename(path)}\n\n"
                "Would you like to install the update now?"
            ):
                self._on_install_downloaded()
        else:
            self.lbl_cloud_status.configure(text="Download failed. Please check internet connection.", foreground="#DC2626")
            self.btn_download_cloud.configure(state="normal")
            self._log("Error: Cloud download was unsuccessful.")

    def _on_install_downloaded(self):
        if not self.downloaded_update_path or not os.path.exists(self.downloaded_update_path):
            messagebox.showerror("Error", "Downloaded update file was not found.")
            return

        self._log(f"Launching update package: {self.downloaded_update_path}")
        success = run_installer_safely(self.downloaded_update_path)
        if success:
            self._log("Setup installer launched with Windows administrative prompt.")
            self.destroy()
        else:
            messagebox.showerror("Error", "Could not launch installer. Try running it manually.")

    def _on_upgrade_installed_direct(self):
        installer = find_local_installer()
        if not installer:
            messagebox.showinfo(
                "Installer Needed",
                "Silver Premium Invoice Generator Setup.exe was not found automatically.\n\n"
                "Please click 'Select Setup.exe Manually...' to pick the installer file."
            )
            return

        if not messagebox.askyesno(
            "Upgrade Installed Version",
            f"This will launch the Windows Setup Installer:\n\n{os.path.basename(installer)}\n\n"
            f"It will upgrade 'C:\\Program Files (x86)\\Silver Premium Invoice Generator' to v{APP_VERSION} "
            "and preserve all your invoice records, customers, and company settings.\n\nProceed?"
        ):
            return

        self._log(f"Launching installer: {installer}")
        success = run_installer_safely(installer)
        if success:
            self._log("Windows Setup Installer launched successfully.")
            self.destroy()
        else:
            messagebox.showerror("Error", "Could not start installer.")

    def _on_select_custom_setup(self):
        file_selected = filedialog.askopenfilename(
            parent=self,
            title="Select Silver Premium Setup Executable",
            filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")]
        )
        if file_selected:
            self._log(f"Selected custom installer: {file_selected}")
            run_installer_safely(file_selected)

    def _on_backup(self):
        dest = filedialog.asksaveasfilename(
            parent=self,
            title="Save Full Data Backup Archive",
            initialfile=f"SilverPremium_Backup_{APP_VERSION}.zip",
            defaultextension=".zip",
            filetypes=[("ZIP Archive", "*.zip")]
        )
        if dest:
            self._log("Creating full backup...")
            if create_full_backup_zip(dest):
                self._log(f"Backup created: {dest}")
                messagebox.showinfo("Backup Created", f"Full backup successfully created:\n{dest}")
            else:
                messagebox.showerror("Backup Failed", "Could not create backup archive.")

    def _open_vault(self):
        vault = get_master_vault_dir()
        if os.path.exists(vault):
            try:
                os.startfile(vault)
            except Exception:
                pass


def main():
    app = StandaloneUpdaterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
