"""
Cloud & Online Updates Engine
Enables Silver Premium Invoice Generator to:
1. Check online cloud repositories (GitHub, raw JSON manifests, or web servers) for new versions.
2. Download update packages directly from online cloud storage with real-time progress tracking.
3. Perform seamless 1-click upgrades using Windows-native installer elevation (eliminating fragile batch scripts).
4. Fall back intelligently to local Master Vault and compiled installers if offline.
"""
import os
import sys
import json
import shutil
import tempfile
import subprocess
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Callable

from core.migration_manager import (
    APP_VERSION,
    get_master_vault_dir,
    get_master_appdata_dir,
    get_active_base_dir,
    scan_and_merge_previous_versions
)
from core.settings_manager import load_settings, save_settings


DEFAULT_MANIFEST_URL = "https://raw.githubusercontent.com/ETheBest/silver-premium-invoice/main/version.json"


def parse_version_tuple(v_str: str) -> tuple:
    """Converts a version string like 'v2.3.0' or '2.3' into an integer tuple (2, 3, 0)."""
    cleaned = str(v_str).strip().lstrip("vV")
    parts = []
    for p in cleaned.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def is_newer_version(remote_ver: str, local_ver: str = APP_VERSION) -> bool:
    """Returns True if remote_ver is strictly newer than local_ver."""
    try:
        return parse_version_tuple(remote_ver) > parse_version_tuple(local_ver)
    except Exception:
        return False


def get_cloud_config() -> Dict[str, Any]:
    """Retrieves cloud update configuration from settings."""
    settings = load_settings()
    cfg = settings.get("cloud_update", {})
    manifest_url = cfg.get("manifest_url") or DEFAULT_MANIFEST_URL
    if "erfanofficial" in manifest_url or not manifest_url.startswith("http"):
        manifest_url = DEFAULT_MANIFEST_URL
        cfg["manifest_url"] = manifest_url
        settings["cloud_update"] = cfg
        try:
            save_settings(settings)
        except Exception:
            pass
    return {
        "enabled": cfg.get("enabled", True),
        "manifest_url": manifest_url,
        "auto_check_on_startup": cfg.get("auto_check_on_startup", False),
        "last_checked": cfg.get("last_checked", "")
    }


def save_cloud_config(cloud_cfg: Dict[str, Any]):
    """Saves updated cloud configuration to settings."""
    settings = load_settings()
    settings["cloud_update"] = cloud_cfg
    save_settings(settings)


def check_for_updates(manifest_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Checks for updates by querying an online cloud manifest URL.
    If offline or unreachable, checks local builds and reports status.
    """
    cfg = get_cloud_config()
    target_url = manifest_url or cfg.get("manifest_url") or DEFAULT_MANIFEST_URL

    result = {
        "success": False,
        "available": False,
        "current_version": APP_VERSION,
        "remote_version": None,
        "release_date": None,
        "changelog": None,
        "installer_url": None,
        "portable_url": None,
        "source": "online",
        "message": ""
    }

    if not target_url:
        result["message"] = "No cloud manifest URL configured."
        return result

    headers = {
        "User-Agent": f"SilverPremiumInvoice/{APP_VERSION} (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json"
    }

    try:
        req = urllib.request.Request(target_url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as response:
            if response.status == 200:
                raw_data = response.read().decode("utf-8")
                manifest = json.loads(raw_data)

                remote_v = manifest.get("version", "")
                result["remote_version"] = remote_v
                result["release_date"] = manifest.get("release_date", "")
                result["changelog"] = manifest.get("changelog", "Enhancements & bug fixes.")
                result["installer_url"] = manifest.get("installer_url", "")
                result["portable_url"] = manifest.get("portable_url", "")
                result["success"] = True

                if remote_v and is_newer_version(remote_v, APP_VERSION):
                    result["available"] = True
                    result["message"] = f"A new version v{remote_v} is available online!"
                else:
                    result["available"] = False
                    result["message"] = f"You are up to date! (v{APP_VERSION} is the latest version)."
                return result
    except urllib.error.HTTPError as e:
        if e.code == 404:
            result["message"] = (
                "Cloud repository URL is not active or published yet. "
                "You can upgrade your PC directly using the '1-Click Upgrade' button below."
            )
        else:
            result["message"] = f"Cloud server returned HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        result["message"] = f"Could not connect to cloud server (offline or unreachable): {e.reason}"
    except Exception as e:
        result["message"] = f"Error checking online updates: {e}"

    # Fallback to local installer check if online check was unable to reach remote
    local_setup = find_local_installer()
    if local_setup and os.path.exists(local_setup):
        result["source"] = "local"
        result["local_installer_path"] = local_setup
        result["message"] += f"\nLocal Windows Setup installer detected ready for upgrade: {os.path.basename(local_setup)}"

    return result


def find_local_installer() -> Optional[str]:
    """Finds the most recent Windows Setup installer executable on this PC."""
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "OneDrive", "Desktop", "Silver Premium Invoice Generator Setup.exe"),
        os.path.join(home, "Desktop", "Silver Premium Invoice Generator Setup.exe"),
        os.path.join(home, "Downloads", "Silver.Premium.Invoice.Generator.Setup.exe"),
        os.path.join(home, "Downloads", "Silver Premium Invoice Generator Setup.exe"),
        os.path.join(home, "OneDrive", "Desktop", "INVOICE APP", "Silver Premium Invoice Generator Setup.exe"),
        os.path.join(home, "Desktop", "INVOICE APP", "Silver Premium Invoice Generator Setup.exe"),
        os.path.join(get_active_base_dir(), "Silver Premium Invoice Generator Setup.exe"),
        os.path.join(tempfile.gettempdir(), "Silver.Premium.Invoice.Generator.Setup.exe"),
        os.path.join(tempfile.gettempdir(), "SilverPremiumInstallerOut", "Silver Premium Invoice Generator Setup.exe")
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.isfile(c):
            return c
    return None


def download_cloud_file(
    download_url: str,
    dest_path: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int, float], None]] = None
) -> Optional[str]:
    """
    Downloads an update file from an online cloud link with progress reporting.
    Returns path to downloaded file, or None on failure.
    """
    if not dest_path:
        filename = download_url.split("?")[0].split("/")[-1]
        if not filename.endswith((".exe", ".zip")):
            filename = "SilverPremiumUpdate.exe"
        dest_path = os.path.join(tempfile.gettempdir(), filename)

    headers = {
        "User-Agent": f"SilverPremiumInvoice/{APP_VERSION} (Windows NT 10.0; Win64; x64)"
    }

    try:
        req = urllib.request.Request(download_url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            content_len_hdr = resp.headers.get("content-length")
            try:
                total_size = int(content_len_hdr) if content_len_hdr else 0
            except (ValueError, TypeError):
                total_size = 0
            downloaded = 0
            chunk_size = 64 * 1024

            with open(dest_path, "wb") as f_out:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        pct = (downloaded / total_size * 100.0) if total_size > 0 else 0.0
                        progress_callback(downloaded, total_size, pct)

        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
            return dest_path
    except Exception as e:
        print(f"Error downloading update file from {download_url}: {e}")
        return None
    return None


def run_installer_safely(installer_path: Optional[str] = None) -> bool:
    """
    Launches the Windows Setup Installer directly using Windows Shell.
    This automatically triggers the native Windows UAC elevation prompt
    and shuts down old versions cleanly without PowerShell/batch errors.
    """
    setup_exe = installer_path or find_local_installer()
    if not setup_exe or not os.path.exists(setup_exe):
        return False

    # Synchronize all data into Master Vault first so installer never loses any records
    scan_and_merge_previous_versions()

    try:
        # Use os.startfile so Windows Explorer launches it with its built-in admin manifest
        os.startfile(setup_exe)
        return True
    except Exception as e:
        try:
            # Fallback to subprocess
            subprocess.Popen([setup_exe], shell=True)
            return True
        except Exception as e2:
            print(f"Could not launch installer: {e2}")
            return False


def generate_cloud_manifest_file(output_path: Optional[str] = None) -> str:
    """
    Generates a version.json manifest that can be uploaded to GitHub Releases,
    OneDrive/Dropbox public folder, or an AWS/web server for cloud update distribution.
    """
    manifest_data = {
        "version": APP_VERSION,
        "release_date": "2026-10-02",
        "app_name": "Silver Premium Invoice Generator",
        "installer_name": "Silver Premium Invoice Generator Setup.exe",
        "portable_name": "Silver Premium Invoice Generator (Portable).exe",
        "installer_url": f"https://github.com/ETheBest/silver-premium-invoice/releases/download/v{APP_VERSION}/Silver.Premium.Invoice.Generator.Setup.exe",
        "portable_url": f"https://github.com/ETheBest/silver-premium-invoice/releases/download/v{APP_VERSION}/Silver.Premium.Invoice.Generator.Portable.exe",
        "changelog": (
            "• High-DPI table text display fix (rowheight=28) - eliminates sliced text.\n"
            "• Responsive 2-row toolbar in Invoice History for seamless display on laptops.\n"
            "• Scrollable canvas containers in Settings and Updater dialogs.\n"
            "• Taskbar-safe window clamping guaranteeing bottom action buttons are never hidden.\n"
            "• Zero-data-loss multi-vault synchronization across local, Master Vault, and AppData.\n"
            "• Online Cloud Update engine and dedicated Windows GUI updater."
        ),
        "min_supported_version": "1.0.0"
    }

    if not output_path:
        base_dir = get_active_base_dir()
        output_path = os.path.join(base_dir, "version.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=4)

    return output_path
