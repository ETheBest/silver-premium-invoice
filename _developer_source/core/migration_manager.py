"""
Multi-Version Migration & Data Synchronization Manager
Handles:
1. Version ledger tracking (v2.2.0).
2. Deep discovery & auto-migration of past invoices, customer profiles, and settings across all previous folders.
3. Orphaned PDF invoice recovery (extracts invoice number, client, date, and amounts).
4. Master Vault synchronization (Documents & AppData) to guarantee zero data loss across updates.
5. In-app Backup (.zip export) and Custom Folder / USB Import.
"""
import os
import sys
import re
import json
import uuid
import shutil
import zipfile
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core.settings_manager import DEFAULT_SETTINGS, _merge_settings_dict

APP_VERSION = "2.3.0"


def get_master_vault_dir() -> str:
    """Returns permanent Windows Documents folder for Silver Premium Invoices."""
    doc_dir = os.path.join(os.path.expanduser("~"), "Documents", "Silver Premium Invoices")
    os.makedirs(doc_dir, exist_ok=True)
    return doc_dir


def get_master_appdata_dir() -> str:
    """Returns permanent AppData folder for Silver Premium Invoices."""
    appdata = os.getenv("APPDATA", os.path.expanduser("~"))
    target = os.path.join(appdata, "SilverPremiumInvoice")
    os.makedirs(target, exist_ok=True)
    return target


def get_active_base_dir() -> str:
    """Returns directory of application (where exe or script resides)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    # 2 levels up from core/migration_manager.py is project root
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_active_invoices_dir() -> str:
    """Returns the local Invoices directory for current execution location."""
    base_dir = get_active_base_dir()
    test_file = os.path.join(base_dir, ".write_test_mig")
    try:
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        folder = os.path.join(base_dir, "Invoices")
    except (IOError, PermissionError):
        folder = get_master_vault_dir()
    os.makedirs(folder, exist_ok=True)
    return folder


def get_version_ledger_path() -> str:
    """Returns path to version_ledger.json."""
    return os.path.join(get_master_appdata_dir(), "version_ledger.json")


def load_version_ledger() -> Dict[str, Any]:
    path = get_version_ledger_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "current_version": APP_VERSION,
        "previous_versions": [],
        "last_migration_at": None,
        "total_invoices_recorded": 0,
        "scanned_locations": []
    }


def save_version_ledger(data: Dict[str, Any]) -> bool:
    path = get_version_ledger_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving version ledger: {e}")
        return False


def get_known_candidate_directories() -> List[str]:
    """
    Returns list of all candidate directories on user's system where previous versions,
    portables, or invoice folders might be located.
    """
    home = os.path.expanduser("~")
    desktop_candidates = [
        os.path.join(home, "OneDrive", "Desktop"),
        os.path.join(home, "Desktop"),
    ]

    candidate_roots = set()
    # Add active dir and master dirs
    candidate_roots.add(get_active_base_dir())
    candidate_roots.add(get_master_vault_dir())
    candidate_roots.add(get_master_appdata_dir())

    for dt in desktop_candidates:
        if os.path.exists(dt):
            candidate_roots.add(dt)
            # Scan top-level folders on Desktop that match invoice keywords
            try:
                for entry in os.listdir(dt):
                    full_p = os.path.join(dt, entry)
                    if os.path.isdir(full_p):
                        name_lower = entry.lower()
                        if any(k in name_lower for k in ["invoice", "silver", "premium"]):
                            candidate_roots.add(full_p)
            except Exception:
                pass

    # Documents candidates
    doc_candidates = [
        os.path.join(home, "Documents"),
        os.path.join(home, "OneDrive", "Documents"),
    ]
    for d in doc_candidates:
        if os.path.exists(d):
            try:
                for entry in os.listdir(d):
                    full_p = os.path.join(d, entry)
                    if os.path.isdir(full_p) and any(k in entry.lower() for k in ["invoice", "silver"]):
                        candidate_roots.add(full_p)
            except Exception:
                pass

    # Program Files & Local AppData installations
    for pf in [os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", ""), r"C:\Program Files (x86)", r"C:\Program Files"]:
        if pf:
            app_p = os.path.join(pf, "Silver Premium Invoice Generator")
            if os.path.exists(app_p):
                candidate_roots.add(app_p)

    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        lap = os.path.join(local_appdata, "Programs", "Silver Premium Invoice Generator")
        if os.path.exists(lap):
            candidate_roots.add(lap)

    return sorted(list(candidate_roots))


def recover_record_from_pdf(pdf_path: str) -> Optional[Dict[str, Any]]:
    """
    Extracts invoice details from an orphaned PDF file using regex & PyMuPDF (if available).
    Allows recovering past invoices even if their JSON record was lost.
    """
    if not os.path.exists(pdf_path):
        return None

    filename = os.path.basename(pdf_path)
    # Matches patterns like '102630 - Rochelle Visa Renewal.pdf'
    m = re.match(r'^(\d{4,10})\s*[-_]\s*(.*?)\.pdf$', filename, re.IGNORECASE)
    if not m:
        m2 = re.match(r'^Invoice_?(\d{4,10})\.pdf$', filename, re.IGNORECASE)
        if m2:
            inv_no = m2.group(1)
            client_name = "Invoice Client"
        else:
            return None
    else:
        inv_no = m.group(1)
        client_name = m.group(2).strip() or "Invoice Client"

    # Default fallback values from file metadata
    mtime = os.path.getmtime(pdf_path)
    dt_file = datetime.fromtimestamp(mtime)
    date_str = dt_file.strftime("%dth %b %Y")
    created_at = dt_file.strftime("%Y-%m-%d %H:%M:%S")

    customer_company = client_name
    subtotal = 0.0
    vat_total = 0.0
    grand_total = 0.0

    # Try deep parsing with pymupdf (fitz)
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
        doc = fitz.open(pdf_path)
        if len(doc) > 0:
            text = doc[0].get_text("text")

            # Look for customer name
            comp_m = re.search(r'(?:Customer|Billed To|Company Name)[:\s]*([^\n]+)', text, re.IGNORECASE)
            if comp_m:
                customer_company = comp_m.group(1).strip()

            # Look for date
            date_m = re.search(r'(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}\s+\d{4})', text)
            if date_m:
                date_str = date_m.group(1)

            # Look for grand total / VAT
            grand_m = re.search(r'Grand Total.*?([\d,]+\.\d{2})', text, re.IGNORECASE)
            if grand_m:
                try:
                    grand_total = float(grand_m.group(1).replace(",", ""))
                except Exception:
                    pass

            vat_m = re.search(r'VAT.*?([\d,]+\.\d{2})', text, re.IGNORECASE)
            if vat_m:
                try:
                    vat_total = float(vat_m.group(1).replace(",", ""))
                except Exception:
                    pass

            sub_m = re.search(r'Sub\s*Total.*?([\d,]+\.\d{2})', text, re.IGNORECASE)
            if sub_m:
                try:
                    subtotal = float(sub_m.group(1).replace(",", ""))
                except Exception:
                    pass

            if grand_total > 0 and subtotal == 0.0:
                subtotal = round(grand_total - vat_total, 2)
        doc.close()
    except Exception:
        pass

    return {
        "invoice_no": inv_no,
        "date": date_str,
        "client_name": client_name,
        "customer_company": customer_company,
        "subtotal": round(subtotal, 2),
        "vat_total": round(vat_total, 2),
        "grand_total": round(grand_total, 2),
        "filename": filename,
        "pdf_filename": filename,
        "created_at": created_at
    }


def scan_and_merge_previous_versions(extra_candidate_dirs: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Exhaustively scans all candidate directories for past invoices, JSON records,
    CSV history, customer profiles, and loose PDF invoices.
    Merges everything into both the Active Invoices directory and Master Vault.
    Returns a summary report dictionary.
    """
    candidate_dirs = get_known_candidate_directories()
    if extra_candidate_dirs:
        for ed in extra_candidate_dirs:
            if ed and os.path.exists(ed) and ed not in candidate_dirs:
                candidate_dirs.append(ed)

    active_invoices_dir = get_active_invoices_dir()
    master_vault_dir = get_master_vault_dir()

    # Determine baseline invoice count before migration
    initial_records_count = 0
    active_json = os.path.join(active_invoices_dir, "invoices_record.json")
    if os.path.exists(active_json):
        try:
            with open(active_json, "r", encoding="utf-8") as f:
                d = json.load(f)
                if isinstance(d, list):
                    initial_records_count = len(d)
        except Exception:
            pass

    # Targets that must receive the synchronized records and PDFs
    sync_targets = list(set([active_invoices_dir, master_vault_dir]))

    records_by_inv: Dict[str, Dict[str, Any]] = {}
    customers_by_id: Dict[str, Dict[str, Any]] = {}
    discovered_pdfs: Dict[str, str] = {}  # filename -> full_path
    merged_settings: Dict[str, Any] = json.loads(json.dumps(DEFAULT_SETTINGS))

    locations_scanned = []

    for d in candidate_dirs:
        if not os.path.exists(d):
            continue

        locations_scanned.append(d)

        # 1. Check for invoices_record.json in d or d/Invoices or d/_developer_source/Invoices
        possible_json_paths = [
            os.path.join(d, "invoices_record.json"),
            os.path.join(d, "Invoices", "invoices_record.json"),
            os.path.join(d, "_developer_source", "Invoices", "invoices_record.json")
        ]
        for jp in possible_json_paths:
            if os.path.exists(jp):
                try:
                    with open(jp, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for r in data:
                                inv = str(r.get("invoice_no", "")).strip()
                                if inv:
                                    if inv not in records_by_inv:
                                        records_by_inv[inv] = r
                                    else:
                                        curr = records_by_inv[inv]
                                        # Prefer the record with higher grand_total or more complete fields
                                        if float(r.get("grand_total", 0.0) or 0.0) >= float(curr.get("grand_total", 0.0) or 0.0):
                                            records_by_inv[inv] = r
                except Exception as e:
                    print(f"Error reading {jp}: {e}")

        # 2. Check for customers.json
        possible_cust_paths = [
            os.path.join(d, "customers.json"),
            os.path.join(d, "_developer_source", "customers.json"),
            os.path.join(d, "Invoices", "customers.json")
        ]
        for cp in possible_cust_paths:
            if os.path.exists(cp):
                try:
                    with open(cp, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        items = data if isinstance(data, list) else data.get("customers", []) if isinstance(data, dict) else []
                        for c in items:
                            comp = str(c.get("company_name", "")).strip()
                            cid = str(c.get("id", "")).strip()
                            key = comp.lower() if comp else cid
                            if key:
                                if key not in customers_by_id:
                                    customers_by_id[key] = c
                                else:
                                    curr = customers_by_id[key]
                                    if len(str(c.get("trn", ""))) > len(str(curr.get("trn", ""))):
                                        customers_by_id[key] = c
                except Exception as e:
                    print(f"Error reading {cp}: {e}")

        # 3. Check for settings.json
        possible_settings_paths = [
            os.path.join(d, "settings.json"),
            os.path.join(d, "_developer_source", "settings.json")
        ]
        for sp in possible_settings_paths:
            if os.path.exists(sp):
                try:
                    with open(sp, "r", encoding="utf-8") as f:
                        s_data = json.load(f)
                        if isinstance(s_data, dict):
                            merged_settings = _merge_settings_dict(merged_settings, s_data)
                except Exception as e:
                    print(f"Error reading {sp}: {e}")

        # 4. Check for PDF invoice files in d and d/Invoices
        pdf_folders = [d, os.path.join(d, "Invoices")]
        for pfolder in pdf_folders:
            if os.path.exists(pfolder) and os.path.isdir(pfolder):
                try:
                    for fname in os.listdir(pfolder):
                        if fname.lower().endswith(".pdf") and not fname.startswith("_preview"):
                            # Check if matches pattern
                            if re.match(r'^\d{4,10}\b', fname):
                                full_pdf = os.path.join(pfolder, fname)
                                if fname not in discovered_pdfs or os.path.getsize(full_pdf) > os.path.getsize(discovered_pdfs[fname]):
                                    discovered_pdfs[fname] = full_pdf
                except Exception:
                    pass

    # 4. Recover any PDFs missing from records_by_inv
    recovered_from_pdf_count = 0
    for fname, fpath in discovered_pdfs.items():
        nums = re.findall(r'\b\d{4,10}\b', fname)
        if nums:
            inv_no = nums[0]
            if inv_no not in records_by_inv:
                rec = recover_record_from_pdf(fpath)
                if rec:
                    records_by_inv[inv_no] = rec
                    recovered_from_pdf_count += 1

    # 5. Sort records descending
    merged_records = list(records_by_inv.values())
    try:
        merged_records.sort(key=lambda r: int(r.get("invoice_no", 0)), reverse=True)
    except Exception:
        pass

    # Auto-harvest customers from invoices if missing from profiles
    for inv in merged_records:
        comp = str(inv.get("customer_company", "")).strip()
        if comp and comp.lower() not in customers_by_id:
            client = str(inv.get("client_name", "")).strip()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            customers_by_id[comp.lower()] = {
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

    # 6. Replicate merged records and PDFs to all sync targets
    pdfs_copied_count = 0
    for target_dir in sync_targets:
        os.makedirs(target_dir, exist_ok=True)

        # Write invoices_record.json
        target_json = os.path.join(target_dir, "invoices_record.json")
        try:
            with open(target_json, "w", encoding="utf-8") as f:
                json.dump(merged_records, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error writing {target_json}: {e}")

        # Write invoice_history.csv
        target_csv = os.path.join(target_dir, "invoice_history.csv")
        try:
            import csv
            with open(target_csv, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Invoice #", "Date", "Client Name", "Customer Company",
                    "Subtotal (AED)", "VAT 5% (AED)", "Grand Total (AED)",
                    "File Name", "Created Timestamp"
                ])
                for r in merged_records:
                    sub = float(r.get("subtotal", 0.0) or 0.0)
                    vat = float(r.get("vat_total", 0.0) or 0.0)
                    grand = float(r.get("grand_total", 0.0) or 0.0)
                    writer.writerow([
                        r.get("invoice_no", ""),
                        r.get("date", ""),
                        r.get("client_name", ""),
                        r.get("customer_company", ""),
                        f"{sub:,.2f}",
                        f"{vat:,.2f}",
                        f"{grand:,.2f}",
                        r.get("filename", ""),
                        r.get("created_at", "")
                    ])
        except Exception as e:
            print(f"Error writing {target_csv}: {e}")

        # Copy missing PDFs
        for fname, src_pdf in discovered_pdfs.items():
            dest_pdf = os.path.join(target_dir, fname)
            if not os.path.exists(dest_pdf) or os.path.getsize(dest_pdf) != os.path.getsize(src_pdf):
                try:
                    shutil.copy2(src_pdf, dest_pdf)
                    pdfs_copied_count += 1
                except Exception:
                    pass

    # 7. Replicate Customers to Active dir, Master Vault, and AppData
    final_customers = list(customers_by_id.values())
    cust_sync_dirs = [get_active_base_dir(), master_vault_dir, get_master_appdata_dir()]
    for c_dir in cust_sync_dirs:
        try:
            os.makedirs(c_dir, exist_ok=True)
            with open(os.path.join(c_dir, "customers.json"), "w", encoding="utf-8") as f:
                json.dump(final_customers, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error replicating customers to {c_dir}: {e}")

    # 8. Replicate Settings to Active dir, Master Vault, and AppData
    settings_sync_dirs = [get_active_base_dir(), master_vault_dir, get_master_appdata_dir()]
    for s_dir in settings_sync_dirs:
        try:
            os.makedirs(s_dir, exist_ok=True)
            with open(os.path.join(s_dir, "settings.json"), "w", encoding="utf-8") as f:
                json.dump(merged_settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error replicating settings to {s_dir}: {e}")

    # 9. Update version ledger
    ledger = load_version_ledger()
    ledger["current_version"] = APP_VERSION
    ledger["last_migration_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ledger["total_invoices_recorded"] = len(merged_records)
    ledger["total_customers_recorded"] = len(final_customers)
    ledger["scanned_locations"] = locations_scanned
    save_version_ledger(ledger)

    new_invoices_count = max(0, len(merged_records) - initial_records_count)

    return {
        "status": "success",
        "total_invoices": len(merged_records),
        "new_invoices": new_invoices_count,
        "total_customers": len(final_customers),
        "total_pdfs": len(discovered_pdfs),
        "recovered_from_pdf": recovered_from_pdf_count,
        "locations_scanned_count": len(locations_scanned),
        "synced_targets": sync_targets
    }


def import_from_custom_directory(folder_path: str) -> Dict[str, Any]:
    """
    Allows user to point to any custom folder (e.g., USB drive, backup folder, old PC transfer)
    and imports all invoice records, customer accounts, and PDF documents into the vault.
    """
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        return {"status": "error", "message": "Selected path is not a valid directory."}

    extra_dirs = [folder_path]
    sub_inv = os.path.join(folder_path, "Invoices")
    if os.path.exists(sub_inv):
        extra_dirs.append(sub_inv)

    res = scan_and_merge_previous_versions(extra_candidate_dirs=extra_dirs)
    return res


def create_full_backup_zip(target_zip_path: str) -> bool:
    """
    Creates a single consolidated ZIP file containing:
    1. invoices_record.json
    2. invoice_history.csv
    3. customers.json
    4. settings.json
    5. All generated PDF invoices
    """
    active_dir = get_active_invoices_dir()
    master_dir = get_master_vault_dir()

    # Ensure records are up to date
    scan_and_merge_previous_versions()

    try:
        with zipfile.ZipFile(target_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # 1. Invoices JSON and CSV
            for f_name in ["invoices_record.json", "invoice_history.csv"]:
                p = os.path.join(active_dir, f_name)
                if not os.path.exists(p):
                    p = os.path.join(master_dir, f_name)
                if os.path.exists(p):
                    zipf.write(p, arcname=f"Invoices/{f_name}")

            # 2. All PDF invoices
            for f_name in os.listdir(active_dir):
                if f_name.lower().endswith(".pdf"):
                    p = os.path.join(active_dir, f_name)
                    zipf.write(p, arcname=f"Invoices/{f_name}")

            # 3. customers.json and settings.json
            base = get_active_base_dir()
            for cfg_name in ["customers.json", "settings.json"]:
                cfg_p = os.path.join(base, cfg_name)
                if os.path.exists(cfg_p):
                    zipf.write(cfg_p, arcname=cfg_name)

        return True
    except Exception as e:
        print(f"Error creating backup ZIP: {e}")
        return False


def check_and_run_startup_migration() -> Tuple[bool, int]:
    """
    Lightweight startup hook.
    Checks if current version differs from ledger or if new records exist.
    Returns (migrated: bool, total_invoices: int).
    """
    ledger = load_version_ledger()
    current_ver = ledger.get("current_version")
    
    # Always run once on startup to guarantee records from any parallel folder are present
    res = scan_and_merge_previous_versions()
    return (current_ver != APP_VERSION, res.get("total_invoices", 0))


if __name__ == "__main__":
    print(f"Silver Premium Invoice Migration Manager v{APP_VERSION}")
    print("Master Vault:", get_master_vault_dir())
    summary = scan_and_merge_previous_versions()
    print("Migration Summary:", json.dumps(summary, indent=2))
