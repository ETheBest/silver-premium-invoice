"""
Settings Manager
Handles persistence of Company defaults, Bank details, Terms & Conditions, and Invoice sequence.
Saves to local JSON configuration.
"""
import os
import sys
import json
from typing import Dict, Any, List

DEFAULT_SETTINGS: Dict[str, Any] = {
    "company": {
        "name": "SILVER PREMIUM DOCUMENTS CLEARING CO. L.L.C",
        "trn": "104171277700003",
        "footer_text": "OFFICE 960, TAMANI ARTS, BAY SQUARE, DUBAI - U.A.E. | Tel: 04 433 8970"
    },
    "bank": {
        "bank_name": "WIO BUSINESS",
        "account_no": "9895248605",
        "beneficiary_name": "Silver Premium Documents Clearing Co LLC",
        "iban": "AE620860000009895248605"
    },
    "terms": [
        "All govt. charges are estimates, may change at any time.",
        "Timely payment is required for us to proceed with your work."
    ],
    "invoice": {
        "next_number": 102630,
        "prefix": "",
        "suffix": ""
    },
    "defaults": {
        "client_name": "",
        "customer_company": "Customer Company Name",
        "customer_address": "Dubai, United Arab Emirates",
        "customer_trn": ""
    },
    "stamp": {
        "enabled": False,
        "image_path": "",
        "show_signatory_text": True
    }
}


def get_config_dir() -> str:
    """Returns directory for storing runtime config."""
    # If running as bundled exe or in dev, store settings adjacent to executable or in AppData
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Try writing to base_dir; fallback to AppData if not writable
    test_file = os.path.join(base_dir, ".perm_test")
    try:
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return base_dir
    except (IOError, PermissionError):
        appdata = os.getenv("APPDATA", os.path.expanduser("~"))
        target = os.path.join(appdata, "SilverPremiumInvoice")
        os.makedirs(target, exist_ok=True)
        return target


def get_master_vault_settings_path() -> str:
    """Returns path to settings.json in Windows Documents Master Vault."""
    doc_dir = os.path.join(os.path.expanduser("~"), "Documents", "Silver Premium Invoices")
    os.makedirs(doc_dir, exist_ok=True)
    return os.path.join(doc_dir, "settings.json")


def get_master_appdata_settings_path() -> str:
    """Returns path to settings.json in AppData vault."""
    appdata = os.getenv("APPDATA", os.path.expanduser("~"))
    target = os.path.join(appdata, "SilverPremiumInvoice")
    os.makedirs(target, exist_ok=True)
    return os.path.join(target, "settings.json")


def get_settings_file_path() -> str:
    return os.path.join(get_config_dir(), "settings.json")


def get_known_settings_paths() -> List[str]:
    """Returns candidate paths where settings.json may exist from past/parallel versions."""
    paths = [get_settings_file_path(), get_master_vault_settings_path(), get_master_appdata_settings_path()]
    home = os.path.expanduser("~")
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        os.path.join(home, "OneDrive", "Desktop", "INVOICE APP", "settings.json"),
        os.path.join(home, "OneDrive", "Desktop", "INVOICE APP", "_developer_source", "settings.json"),
        os.path.join(home, "OneDrive", "Desktop", "Silver Premium - Invoice Generator", "settings.json"),
        os.path.join(home, "OneDrive", "Desktop", "Silver Premium Portable", "settings.json"),
        os.path.join(home, "Desktop", "INVOICE APP", "settings.json"),
        os.path.join(home, "Desktop", "Silver Premium Portable", "settings.json"),
        r"C:\Program Files (x86)\Silver Premium Invoice Generator\settings.json",
        r"C:\Program Files\Silver Premium Invoice Generator\settings.json",
        os.path.join(local_appdata, "Programs", "Silver Premium Invoice Generator", "settings.json")
    ]
    for c in candidates:
        if c not in paths and os.path.exists(c):
            paths.append(c)
    return paths


def _merge_settings_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merges override dictionary into base dictionary."""
    result = json.loads(json.dumps(base))
    for k, v in override.items():
        if isinstance(v, dict) and k in result and isinstance(result[k], dict):
            for sub_k, sub_v in v.items():
                if sub_v is not None and str(sub_v).strip():
                    result[k][sub_k] = sub_v
        elif isinstance(v, list) and k in result and isinstance(result[k], list):
            if v:
                result[k] = list(v)
        elif v is not None:
            result[k] = v
    return result


def load_settings() -> Dict[str, Any]:
    """
    Loads settings from primary file, and cross-merges with Master Vault, AppData,
    and previous version directories to guarantee zero configuration loss across updates.
    """
    merged = json.loads(json.dumps(DEFAULT_SETTINGS))
    known_paths = get_known_settings_paths()

    # Load from all known paths in reverse order (primary has final say if valid)
    valid_found = False
    for path in reversed(known_paths):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        merged = _merge_settings_dict(merged, data)
                        valid_found = True
            except Exception as e:
                print(f"Error loading settings from {path}: {e}")

    # If primary exists, give it final merge pass
    primary = get_settings_file_path()
    if os.path.exists(primary):
        try:
            with open(primary, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    merged = _merge_settings_dict(merged, data)
        except Exception:
            pass

    return merged


def save_settings(data: Dict[str, Any]) -> bool:
    """
    Saves settings to local JSON file and mirrors automatically to:
    1. Documents Master Vault
    2. AppData Permanent Vault
    """
    primary = get_settings_file_path()
    targets = [primary, get_master_vault_settings_path(), get_master_appdata_settings_path()]

    success = False
    for t in targets:
        try:
            os.makedirs(os.path.dirname(t), exist_ok=True)
            with open(t, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            success = True
        except Exception as e:
            print(f"Error saving settings to {t}: {e}")

    return success


def get_next_invoice_number() -> str:
    """Returns formatted next invoice number (e.g. 102630)."""
    settings = load_settings()
    num = settings.get("invoice", {}).get("next_number", 102630)
    prefix = settings.get("invoice", {}).get("prefix", "")
    suffix = settings.get("invoice", {}).get("suffix", "")
    return f"{prefix}{num}{suffix}"


def increment_invoice_number() -> str:
    """Increments the invoice counter and returns the new number."""
    settings = load_settings()
    num = settings.get("invoice", {}).get("next_number", 102630)
    settings["invoice"]["next_number"] = num + 1
    save_settings(settings)
    return str(num + 1)


def save_stamp_image(source_path: str) -> str:
    """Copies an uploaded stamp image to config dir and updates settings."""
    import shutil
    if not os.path.exists(source_path):
        return ""
    ext = os.path.splitext(source_path)[1].lower() or ".png"
    target = os.path.join(get_config_dir(), f"company_stamp{ext}")
    try:
        shutil.copy2(source_path, target)
        s = load_settings()
        if "stamp" not in s:
            s["stamp"] = {}
        s["stamp"]["image_path"] = target
        s["stamp"]["enabled"] = True
        save_settings(s)
        return target
    except Exception as e:
        print(f"Error copying stamp: {e}")
        return ""


def get_stamp_settings() -> Dict[str, Any]:
    """Returns stamp settings with resolved paths."""
    s = load_settings()
    stamp_cfg = s.get("stamp", {"enabled": False, "image_path": ""})
    img_path = stamp_cfg.get("image_path", "")
    # Check if configured path exists
    if img_path and os.path.exists(img_path):
        return stamp_cfg
    # Check default asset
    default_asset = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "default_stamp.png")
    if os.path.exists(default_asset):
        stamp_cfg["image_path"] = default_asset
    return stamp_cfg


if __name__ == "__main__":
    s = load_settings()
    print("Loaded settings:", json.dumps(s, indent=2))
    print("Next invoice #:", get_next_invoice_number())
