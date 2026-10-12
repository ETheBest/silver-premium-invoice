"""
Customer Profile Manager
Handles persistent storage, retrieval, updating, and importing of repeat customer profiles.
Saves to customers.json in the application configuration directory.
"""
import os
import sys
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from core.settings_manager import get_config_dir, load_settings
from core.records_manager import load_all_records


def get_customers_file_path() -> str:
    """Returns absolute path to customers.json configuration file."""
    return os.path.join(get_config_dir(), "customers.json")


def _get_default_seed_customers() -> List[Dict[str, Any]]:
    """Generates initial seed customers with clean generic informative sample."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    seed = [
        {
            "id": "cust_default_1",
            "company_name": "Sample Corporate Client LLC",
            "client_name": "General Services Reference",
            "address": "Dubai, United Arab Emirates",
            "trn": "100XXXXXXXXX003",
            "phone": "+971 4 000 0000",
            "email": "info@sampleclient.ae",
            "notes": "General sample corporate customer profile",
            "created_at": now_str,
            "updated_at": now_str
        }
    ]
    return seed


def get_known_customers_paths() -> List[str]:
    """Returns candidate paths where customers.json may exist from past versions."""
    primary = get_customers_file_path()
    paths = [primary]
    home = os.path.expanduser("~")
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        os.path.join(home, "OneDrive", "Desktop", "INVOICE APP", "customers.json"),
        os.path.join(home, "OneDrive", "Desktop", "INVOICE APP", "_developer_source", "customers.json"),
        os.path.join(home, "OneDrive", "Desktop", "Silver Premium - Invoice Generator", "customers.json"),
        os.path.join(home, "OneDrive", "Desktop", "Silver Premium Portable", "customers.json"),
        os.path.join(home, "Desktop", "INVOICE APP", "customers.json"),
        os.path.join(home, "Desktop", "Silver Premium Portable", "customers.json"),
        os.path.join(home, "Documents", "Silver Premium Invoices", "customers.json"),
        os.path.join(os.getenv("APPDATA", home), "SilverPremiumInvoice", "customers.json"),
        r"C:\Program Files (x86)\Silver Premium Invoice Generator\customers.json",
        r"C:\Program Files\Silver Premium Invoice Generator\customers.json",
        os.path.join(local_appdata, "Programs", "Silver Premium Invoice Generator", "customers.json")
    ]
    for c in candidates:
        if c not in paths and os.path.exists(c):
            paths.append(c)
    return paths


def load_customers() -> List[Dict[str, Any]]:
    """
    Loads all customer profiles from primary customers.json, merges with any
    existing profiles from other known installation/portable paths, and auto-harvests
    profiles from past invoice history to guarantee zero customer data loss.
    """
    customers_by_key = {}
    known_paths = get_known_customers_paths()

    for path in known_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    items = data if isinstance(data, list) else data.get("customers", []) if isinstance(data, dict) else []
                    for c in items:
                        comp = str(c.get("company_name", "")).strip()
                        cid = str(c.get("id", "")).strip()
                        key = comp.lower() if comp else cid
                        if key:
                            if key not in customers_by_key:
                                customers_by_key[key] = c
                            else:
                                curr = customers_by_key[key]
                                if len(str(c.get("trn", ""))) > len(str(curr.get("trn", ""))):
                                    customers_by_key[key] = c
            except Exception as e:
                print(f"Error loading customers from {path}: {e}")

    # Auto-harvest customers from invoice records if not already in profiles
    try:
        invoices = load_all_records()
        for inv in invoices:
            comp = str(inv.get("customer_company", "")).strip()
            if comp and comp.lower() not in customers_by_key:
                client = str(inv.get("client_name", "")).strip()
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                auto_prof = {
                    "id": f"cust_{uuid.uuid4().hex[:8]}",
                    "company_name": comp,
                    "client_name": client,
                    "address": "Dubai, United Arab Emirates",
                    "trn": "",
                    "phone": "",
                    "email": "",
                    "notes": f"Auto-recovered from invoice #{inv.get('invoice_no', '')}",
                    "created_at": inv.get("created_at", now_str),
                    "updated_at": now_str
                }
                customers_by_key[comp.lower()] = auto_prof
    except Exception as e:
        print(f"Error auto-harvesting customers from invoices: {e}")

    result = list(customers_by_key.values())
    if not result:
        # Initialize with default seed
        defaults = _get_default_seed_customers()
        if defaults:
            save_customers(defaults)
            return defaults
        return []

    # Guarantee every customer has a unique ID across all merged sources
    seen_ids = set()
    for cust in result:
        cid = str(cust.get("id", "")).strip()
        if not cid or cid in seen_ids:
            new_id = f"cust_{uuid.uuid4().hex[:8]}"
            cust["id"] = new_id
            seen_ids.add(new_id)
        else:
            seen_ids.add(cid)

    return result


def save_customers(customers: List[Dict[str, Any]]) -> bool:
    """
    Saves customer profiles list to primary customers.json and mirrors to:
    1. Documents Master Vault
    2. AppData Permanent Vault
    """
    # Guarantee unique IDs before saving
    seen_ids = set()
    for cust in customers:
        cid = str(cust.get("id", "")).strip()
        if not cid or cid in seen_ids:
            new_id = f"cust_{uuid.uuid4().hex[:8]}"
            cust["id"] = new_id
            seen_ids.add(new_id)
        else:
            seen_ids.add(cid)

    primary_path = get_customers_file_path()
    master_cust = os.path.join(os.path.expanduser("~"), "Documents", "Silver Premium Invoices", "customers.json")
    appdata_cust = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "SilverPremiumInvoice", "customers.json")

    targets = [primary_path, master_cust, appdata_cust]
    success = False

    for path in targets:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(customers, f, indent=2, ensure_ascii=False)
            success = True
        except Exception as e:
            print(f"Error saving customers to {path}: {e}")

    return success


def get_customer_by_id(cust_id: str) -> Optional[Dict[str, Any]]:
    """Finds a customer profile by its unique ID."""
    customers = load_customers()
    for c in customers:
        if c.get("id") == cust_id:
            return c
    return None


def get_customer_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Finds a customer profile by company name or client name (case-insensitive)."""
    clean = (name or "").strip().lower()
    if not clean:
        return None
    customers = load_customers()
    for c in customers:
        if c.get("company_name", "").strip().lower() == clean:
            return c
    for c in customers:
        if c.get("client_name", "").strip().lower() == clean:
            return c
    return None


def save_or_update_customer(customer_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates or updates a customer profile.
    If customer_data contains an 'id' that matches an existing profile, updates it.
    Otherwise matches by company_name (case-insensitive) or generates a new ID.
    Returns the saved customer dictionary.
    """
    customers = load_customers()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cust_id = customer_data.get("id")
    company_name = customer_data.get("company_name", "").strip()

    target_idx = -1
    if cust_id:
        for idx, c in enumerate(customers):
            if c.get("id") == cust_id:
                target_idx = idx
                break

    if target_idx == -1 and company_name:
        for idx, c in enumerate(customers):
            if c.get("company_name", "").strip().lower() == company_name.lower():
                target_idx = idx
                break

    record = dict(customer_data)
    record["company_name"] = company_name
    record["client_name"] = customer_data.get("client_name", "").strip()
    record["address"] = customer_data.get("address", "").strip()
    record["trn"] = customer_data.get("trn", "").strip()
    record["phone"] = customer_data.get("phone", "").strip()
    record["email"] = customer_data.get("email", "").strip()
    record["notes"] = customer_data.get("notes", "").strip()
    record["updated_at"] = now_str

    if target_idx >= 0:
        record["id"] = customers[target_idx].get("id", cust_id or f"cust_{uuid.uuid4().hex[:8]}")
        record["created_at"] = customers[target_idx].get("created_at", now_str)
        customers[target_idx] = record
    else:
        record["id"] = cust_id or f"cust_{uuid.uuid4().hex[:8]}"
        record["created_at"] = now_str
        customers.append(record)

    save_customers(customers)
    return record


def delete_customer(cust_id: str) -> bool:
    """Deletes a customer profile by ID."""
    customers = load_customers()
    initial_count = len(customers)
    customers = [c for c in customers if c.get("id") != cust_id]
    if len(customers) < initial_count:
        save_customers(customers)
        return True
    return False


def import_from_invoices() -> int:
    """
    Scans past invoice history and automatically creates profiles
    for any unique customers not yet saved.
    Returns the count of newly imported customers.
    """
    existing = load_customers()
    existing_companies = {
        c.get("company_name", "").strip().lower() for c in existing if c.get("company_name")
    }

    invoices = load_all_records()
    new_count = 0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for inv in invoices:
        comp = inv.get("customer_company", "").strip()
        client = inv.get("client_name", "").strip()
        if comp and comp.lower() not in existing_companies:
            new_cust = {
                "id": f"cust_{uuid.uuid4().hex[:8]}",
                "company_name": comp,
                "client_name": client,
                "address": "",
                "trn": "",
                "phone": "",
                "email": "",
                "notes": f"Imported from past Invoice #{inv.get('invoice_no', '')}",
                "created_at": now_str,
                "updated_at": now_str
            }
            existing.append(new_cust)
            existing_companies.add(comp.lower())
            new_count += 1

    if new_count > 0:
        save_customers(existing)
    return new_count
