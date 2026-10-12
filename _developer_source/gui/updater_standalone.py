"""
Silver Premium - Standalone Cloud & System Updater GUI
Provides an independent, client-ready interface to:
1. Check for online cloud updates (GitHub Releases & Cloud Manifest).
2. Download official Windows Setup installer or Portable Edition with a live progress bar.
3. 1-Click upgrade the installed application in Program Files with zero data loss.
4. Auto-detect missing local installers and download them seamlessly on demand.
5. Guarantee zero data loss across upgrades by preserving the Master Vault in Documents.
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
        self.title(f"Silver Premium - Official Cloud & System Update Assistant v{APP_VERSION}")
        self.geometry("760x620")
        self.minsize(680, 500)

        self.cloud_info: Dict[str, Any] = {}
        self.downloaded_update_path: Optional[str] = None
        self._is_downloading = False

        self._configure_styles()
        self._build_ui()
        center_window(self, width=760, height=620)

        # Automatically check for updates on startup in background
        self.after(350, self._start_async_check)

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
        # 1. Header banner
        hdr = ttk.Frame(self, padding=(16, 12))
        hdr.pack(fill="x", side="top")

        hdr_left = ttk.Frame(hdr)
        hdr_left.pack(side="left", fill="x", expand=True)

        ttk.Label(
            hdr_left,
            text="SILVER PREMIUM DOCUMENTS CLEARING CO. L.L.C",
            font=("Segoe UI", 12, "bold"),
            foreground="#1E3A8A"
        ).pack(anchor="w")

        ttk.Label(
            hdr_left,
            text="Official Cloud & System Update Assistant • Zero Data Loss Protection",
            font=("Segoe UI", 9),
            foreground="#64748B"
        ).pack(anchor="w", pady=(2, 0))

        badge_box = ttk.Frame(hdr)
        badge_box.pack(side="right", anchor="e")

        ttk.Label(
            badge_box,
            text=f"Version: v{APP_VERSION}",
            font=("Segoe UI", 10, "bold"),
            foreground="#047857"
        ).pack(anchor="e")

        ttk.Label(
            badge_box,
            text="Live Cloud Connected",
            font=("Segoe UI", 8),
            foreground="#475569"
        ).pack(anchor="e")

        ttk.Separator(self, orient="horizontal").pack(fill="x")

        # 2. Pinned Bottom Bar
        bot_bar = ttk.Frame(self, padding=(14, 10))
        bot_bar.pack(fill="x", side="bottom")

        btn_close = ttk.Button(bot_bar, text="Close", command=self.destroy, width=10)
        btn_close.pack(side="right", padx=(6, 0))

        btn_backup = ttk.Button(bot_bar, text="💾 Create Backup (.zip)", command=self._on_backup)
        btn_backup.pack(side="right", padx=(6, 0))

        btn_sync = ttk.Button(bot_bar, text="🔄 Sync & Verify Vault", command=self._on_sync_vault)
        btn_sync.pack(side="left", padx=(0, 6))

        btn_vault = ttk.Button(bot_bar, text="📂 Open Master Vault", command=self._open_vault)
        btn_vault.pack(side="left")

        ttk.Separator(self, orient="horizontal").pack(fill="x", side="bottom")

        # 3. Scrollable middle area
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
        cloud_card = ttk.LabelFrame(content, text=" ☁️ Online Cloud Updates & Downloads ", padding=12)
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
            text="Connecting to cloud update repository...",
            font=("Segoe UI", 9),
            foreground="#1E3A8A"
        )
        self.lbl_cloud_status.pack(anchor="w", pady=(0, 6))

        # Progress bar
        self.prog_bar = ttk.Progressbar(cloud_card, mode="determinate")
        self.prog_bar.pack(fill="x", pady=(0, 8))
        self.prog_bar["value"] = 0

        # Action buttons for cloud download
        row_act = ttk.Frame(cloud_card)
        row_act.pack(fill="x")

        self.btn_download_cloud = ttk.Button(
            row_act,
            text="☁️ Download Setup Installer from Cloud",
            command=lambda: self._start_async_download(kind="installer"),
            state="disabled",
            style="Primary.TButton"
        )
        self.btn_download_cloud.pack(side="left", padx=(0, 8))

        self.btn_download_portable = ttk.Button(
            row_act,
            text="📦 Download Portable (.exe)",
            command=lambda: self._start_async_download(kind="portable"),
            state="disabled"
        )
        self.btn_download_portable.pack(side="left", padx=(0, 8))

        self.btn_install_downloaded = ttk.Button(
            row_act,
            text="🚀 Launch Downloaded Setup",
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
                 "using the Windows Setup engine with native Windows UAC administrative security.\n"
                 "If the installer is not on this PC, clicking Upgrade will automatically download it from the Cloud.",
            font=("Segoe UI", 9)
        )
        lbl_inst_desc.pack(anchor="w", pady=(0, 6))

        lbl_shield = ttk.Label(
            inst_card,
            text="🔒 Master Data Protection Active: Invoices, Customers, and Settings in Documents are 100% preserved.",
            font=("Segoe UI", 8, "italic"),
            foreground="#047857"
        )
        lbl_shield.pack(anchor="w", pady=(0, 8))

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
            self.btn_download_cloud.configure(
                text=f"🚀 Download & Install Update (v{remote_v})",
                state="normal"
            )
            self.btn_download_portable.configure(state="normal")
            self._log(f"Cloud Update Available: v{remote_v} (Current: v{APP_VERSION})")
            if res.get("changelog"):
                self._log(f"Changelog:\n{res.get('changelog')}")
        elif res.get("success"):
            self.lbl_cloud_status.configure(
                text=f"✓ System is up to date! (v{APP_VERSION} matches latest cloud release).",
                foreground="#047857"
            )
            self.btn_download_cloud.configure(
                text=f"☁️ Re-download Setup (v{APP_VERSION}) from Cloud",
                state="normal"
            )
            self.btn_download_portable.configure(state="normal")
            self._log(f"Cloud check confirmed: System is at latest version v{APP_VERSION}.")
        else:
            msg = res.get("message", "Could not connect to cloud server.")
            self.lbl_cloud_status.configure(text=msg, foreground="#B45309")
            self.btn_download_cloud.configure(
                text="☁️ Download Setup from Cloud",
                state="normal"
            )
            self._log(f"Note: {msg}")

        # Check local installer
        local_inst = find_local_installer()
        if local_inst:
            self._log(f"Local Windows Setup Installer ready: {local_inst}")
        else:
            self._log("No local installer found on PC. Cloud download is ready.")

    def _start_async_download(self, kind: str = "installer"):
        if self._is_downloading:
            return

        if kind == "portable":
            dl_url = self.cloud_info.get("portable_url")
            default_name = "Silver.Premium.Invoice.Generator.Portable.exe"
        else:
            dl_url = self.cloud_info.get("installer_url")
            default_name = "Silver.Premium.Invoice.Generator.Setup.exe"

        if not dl_url:
            # Fallback to official GitHub Release asset URL
            dl_url = f"https://github.com/ETheBest/silver-premium-invoice/releases/download/v{APP_VERSION}/{default_name}"

        # If user is downloading the portable version, let them choose where to save it
        dest_path = None
        if kind == "portable":
            dest_path = filedialog.asksaveasfilename(
                parent=self,
                title="Save Portable Executable",
                initialfile="Silver Premium Invoice Generator (Portable).exe",
                filetypes=[("Executable Files", "*.exe")]
            )
            if not dest_path:
                return

        self._is_downloading = True
        self.btn_download_cloud.configure(state="disabled")
        self.btn_download_portable.configure(state="disabled")
        self.btn_check_cloud.configure(state="disabled")

        label_kind = "Portable Edition" if kind == "portable" else "Setup Installer"
        self.lbl_cloud_status.configure(text=f"Downloading {label_kind} from cloud...", foreground="#1E3A8A")
        self._log(f"Downloading {label_kind} from: {dl_url}")

        def progress(dl, total, pct):
            self.after(0, lambda: self._update_progress(dl, total, pct))

        def worker():
            path = download_cloud_file(dl_url, dest_path=dest_path, progress_callback=progress)
            self.after(0, lambda: self._on_download_completed(path, kind=kind))

        threading.Thread(target=worker, daemon=True).start()

    def _update_progress(self, dl, total, pct):
        self.prog_bar["value"] = pct
        mb_dl = dl / (1024 * 1024)
        mb_tot = total / (1024 * 1024)
        if total > 0:
            self.lbl_cloud_status.configure(
                text=f"Downloading: {mb_dl:.1f} MB / {mb_tot:.1f} MB ({pct:.0f}%)"
            )
        else:
            self.lbl_cloud_status.configure(
                text=f"Downloading: {mb_dl:.1f} MB received..."
            )

    def _on_download_completed(self, path: Optional[str], kind: str = "installer"):
        self._is_downloading = False
        self.btn_check_cloud.configure(state="normal")
        self.btn_download_cloud.configure(state="normal")
        self.btn_download_portable.configure(state="normal")

        if path and os.path.exists(path):
            self.prog_bar["value"] = 100
            if kind == "portable":
                self.lbl_cloud_status.configure(
                    text=f"✓ Download complete: {os.path.basename(path)} saved.",
                    foreground="#047857"
                )
                self._log(f"Portable executable saved to: {path}")
                if messagebox.askyesno(
                    "Download Complete",
                    f"Portable Edition downloaded successfully:\n\n{path}\n\n"
                    "Would you like to launch the Portable Edition now?"
                ):
                    try:
                        os.startfile(path)
                    except Exception as e:
                        self._log(f"Could not launch: {e}")
            else:
                self.downloaded_update_path = path
                self.lbl_cloud_status.configure(
                    text=f"✓ Download complete: {os.path.basename(path)} ready to install.",
                    foreground="#047857"
                )
                self.btn_install_downloaded.configure(state="normal")
                self._log(f"Setup installer saved to: {path}")

                if messagebox.askyesno(
                    "Download Complete",
                    f"Setup Installer downloaded successfully:\n\n{os.path.basename(path)}\n\n"
                    "Would you like to run the installation now?"
                ):
                    self._on_install_downloaded()
        else:
            self.lbl_cloud_status.configure(text="Download failed. Please check your internet connection.", foreground="#DC2626")
            self._log("Error: Cloud download was unsuccessful.")

    def _on_install_downloaded(self):
        if not self.downloaded_update_path or not os.path.exists(self.downloaded_update_path):
            messagebox.showerror("Error", "Downloaded setup file was not found.")
            return

        self._log(f"Launching setup package: {self.downloaded_update_path}")
        success = run_installer_safely(self.downloaded_update_path)
        if success:
            self._log("Setup installer launched with Windows administrative prompt.")
            self.destroy()
        else:
            messagebox.showerror("Error", "Could not launch installer. Try running it manually.")

    def _on_upgrade_installed_direct(self):
        installer = find_local_installer()
        if not installer:
            if messagebox.askyesno(
                "Download Installer from Cloud?",
                "The Windows Setup Installer was not found locally on this computer.\n\n"
                "Would you like to automatically download the official Setup installer from the Cloud now?"
            ):
                self._start_async_download(kind="installer")
                return
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

    def _on_sync_vault(self):
        self._log("Scanning and synchronizing Master Vault...")
        try:
            stats = scan_and_merge_previous_versions()
            vault_dir = get_master_vault_dir()
            self._log(f"Master Vault confirmed at: {vault_dir}")
            self._log(f"Sync complete. Recorded ledger: {stats.get('total_invoices_recorded', 0)} invoices.")
            messagebox.showinfo(
                "Vault Synchronized",
                f"Master Vault is synchronized and protected:\n\n{vault_dir}\n\n"
                f"Total Invoices in Vault: {stats.get('total_invoices_recorded', 0)}"
            )
        except Exception as e:
            self._log(f"Error syncing vault: {e}")
            messagebox.showerror("Sync Error", f"Could not sync vault: {e}")

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
