"""
Installed Application Updater Engine
Detects, upgrades, and synchronizes the installed version of Silver Premium Invoice Generator
(e.g., C:\Program Files (x86)\Silver Premium Invoice Generator or AppData\Local\Programs).
"""
import os
import sys
import shutil
import subprocess
from typing import Dict, Any, Optional, List

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core.migration_manager import (
    APP_VERSION,
    get_master_vault_dir,
    get_master_appdata_dir,
    get_active_base_dir,
    get_active_invoices_dir,
    scan_and_merge_previous_versions
)


def find_installed_app_directory() -> Optional[str]:
    """
    Finds the directory where the application is installed on this PC.
    Checks Program Files (x86), Program Files, and LocalAppData Programs.
    """
    candidates = [
        r"C:\Program Files (x86)\Silver Premium Invoice Generator",
        r"C:\Program Files\Silver Premium Invoice Generator",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Silver Premium Invoice Generator"),
    ]
    for c in candidates:
        if c and os.path.exists(c) and os.path.isdir(c):
            exe = os.path.join(c, "Silver Premium Invoice Generator.exe")
            if os.path.exists(exe):
                return c
            # Even if exe is named slightly differently or directory exists
            if os.path.exists(c):
                return c

    # Check Windows Registry for uninstall location
    try:
        import winreg
        key_paths = [
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        ]
        for kp in key_paths:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, kp) as root_key:
                    num_subkeys = winreg.QueryInfoKey(root_key)[0]
                    for i in range(num_subkeys):
                        sub_name = winreg.EnumKey(root_key, i)
                        try:
                            with winreg.OpenKey(root_key, sub_name) as sub_key:
                                disp_name, _ = winreg.QueryValueEx(sub_key, "DisplayName")
                                if "Silver Premium" in disp_name:
                                    inst_loc, _ = winreg.QueryValueEx(sub_key, "InstallLocation")
                                    if inst_loc and os.path.exists(inst_loc):
                                        return inst_loc
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception:
        pass

    return None


def close_running_application() -> bool:
    """Terminates running instances of the app to release file locks before updating."""
    try:
        subprocess.run(
            'taskkill /F /IM "Silver Premium Invoice Generator.exe" /FI "STATUS eq RUNNING"',
            shell=True,
            capture_output=True
        )
        subprocess.run(
            'taskkill /F /IM "SilverPremiumInvoice.exe" /FI "STATUS eq RUNNING"',
            shell=True,
            capture_output=True
        )
        return True
    except Exception:
        return False


def get_latest_built_exe() -> Optional[str]:
    """Finds the latest compiled standalone executable."""
    base = get_active_base_dir()
    candidates = [
        os.path.join(base, "Silver Premium Invoice Generator.exe"),
        os.path.join(base, "dist", "SilverPremiumInvoice.exe"),
        os.path.join(base, "dist", "Silver Premium Invoice Generator.exe"),
        os.path.join(os.path.dirname(base), "Silver Premium Invoice Generator.exe"),
        os.path.join(os.path.dirname(base), "Silver Premium Portable", "Silver Premium Invoice Generator.exe")
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def update_installed_version(target_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Upgrades the installed application directory with:
    1. Latest executable binary
    2. Latest assets (icons, letterhead, stamps)
    3. Unified data files (customers.json, settings.json, invoices_record.json, invoice_history.csv)
    4. Migrates all invoice records and PDFs into Master Vault and AppData
    """
    install_dir = target_dir or find_installed_app_directory()
    if not install_dir:
        return {
            "status": "error",
            "message": "Installed application folder could not be found on this PC."
        }

    # 1. Close any running instance
    close_running_application()

    # 2. Run migration first to ensure all data is consolidated in Master Vault
    scan_and_merge_previous_versions()

    # 3. Locate source executable
    src_exe = get_latest_built_exe()
    if not src_exe or not os.path.exists(src_exe):
        return {
            "status": "error",
            "message": f"Source executable not found. Please build the project first."
        }

    # 4. Copy executable to installed location
    dest_exe = os.path.join(install_dir, "Silver Premium Invoice Generator.exe")
    try:
        shutil.copy2(src_exe, dest_exe)
    except PermissionError:
        return {
            "status": "elevation_required",
            "message": f"Administrator permission required to write to {install_dir}. Please run the updater as Administrator.",
            "target_dir": install_dir
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed copying executable to {dest_exe}: {e}"
        }

    # 5. Copy assets
    src_assets = os.path.join(get_active_base_dir(), "assets")
    if not os.path.exists(src_assets):
        src_assets = os.path.join(os.path.dirname(get_active_base_dir()), "_developer_source", "assets")

    if os.path.exists(src_assets):
        dest_assets = os.path.join(install_dir, "assets")
        try:
            os.makedirs(dest_assets, exist_ok=True)
            for item in os.listdir(src_assets):
                s_item = os.path.join(src_assets, item)
                d_item = os.path.join(dest_assets, item)
                if os.path.isfile(s_item):
                    shutil.copy2(s_item, d_item)
        except Exception as e:
            print(f"Note on assets copy: {e}")

    # 6. Copy unified data files (customers.json, settings.json, invoices_record.json, invoice_history.csv)
    master_vault = get_master_vault_dir()
    master_appdata = get_master_appdata_dir()
    data_files = ["customers.json", "settings.json", "invoices_record.json", "invoice_history.csv"]

    for df in data_files:
        src_df = os.path.join(master_vault, df)
        if not os.path.exists(src_df):
            src_df = os.path.join(master_appdata, df)
        if not os.path.exists(src_df):
            src_df = os.path.join(get_active_base_dir(), df)

        if os.path.exists(src_df):
            # Copy to installed folder if writable
            try:
                shutil.copy2(src_df, os.path.join(install_dir, df))
            except Exception:
                pass
            # Always ensure AppData and Documents have it
            try:
                shutil.copy2(src_df, os.path.join(master_appdata, df))
                shutil.copy2(src_df, os.path.join(master_vault, df))
            except Exception:
                pass

    return {
        "status": "success",
        "install_dir": install_dir,
        "exe_path": dest_exe,
        "version": APP_VERSION,
        "message": f"Successfully updated installed version in '{install_dir}' to v{APP_VERSION}!"
    }


if __name__ == "__main__":
    print(f"Silver Premium Installed Updater v{APP_VERSION}")
    target = find_installed_app_directory()
    print("Detected Install Directory:", target)
    if target:
        res = update_installed_version(target)
        print("Update Result:", res)
    else:
        print("No installed directory found.")
