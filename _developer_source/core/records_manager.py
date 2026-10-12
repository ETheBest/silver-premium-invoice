"""
Invoice Records and Archive Manager
Maintains:
1. Invoices/ directory where all generated PDFs are saved with clean filenames.
2. Invoices/invoices_record.json for application persistence.
3. Invoices/invoice_history.csv for 1-click Excel spreadsheet tracking.
4. Auto-sequential (+1) invoice number tracking based on existing records and files.
"""
import os
import sys
import re
import json
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional


def get_base_dir() -> str:
    """Returns directory of application (where exe or script resides)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_invoices_dir() -> str:
    """Returns absolute path to Invoices archive folder, creating it if needed."""
    base_dir = get_base_dir()
    test_file = os.path.join(base_dir, ".write_test")
    try:
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        folder = os.path.join(base_dir, "Invoices")
    except (IOError, PermissionError):
        # Fallback to Documents folder if installed in a write-protected directory (e.g., Program Files)
        folder = os.path.join(os.path.expanduser("~"), "Documents", "Silver Premium Invoices")
    os.makedirs(folder, exist_ok=True)
    return folder


def get_records_json_path() -> str:
    return os.path.join(get_invoices_dir(), "invoices_record.json")


def get_records_csv_path() -> str:
    return os.path.join(get_invoices_dir(), "invoice_history.csv")


def sanitize_filename(name: str) -> str:
    """Removes invalid filename characters."""
    clean = re.sub(r'[\\/*?:"<>|]', '', name).strip()
    return clean or "Invoice"


def get_known_records_paths() -> List[str]:
    """Returns all known persistent records JSON file paths on this system."""
    paths = [get_records_json_path()]
    candidates = [
        os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop", "INVOICE APP", "Invoices", "invoices_record.json"),
        os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop", "INVOICE APP", "_developer_source", "Invoices", "invoices_record.json"),
        os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop", "Silver Premium - Invoice Generator", "Invoices", "invoices_record.json"),
        os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop", "Silver Premium Portable", "Invoices", "invoices_record.json"),
        os.path.join(os.path.expanduser("~"), "Documents", "Silver Premium Invoices", "invoices_record.json"),
        os.path.join(os.path.expanduser("~"), "Desktop", "INVOICE APP", "Invoices", "invoices_record.json"),
        os.path.join(os.path.expanduser("~"), "Desktop", "Silver Premium Portable", "Invoices", "invoices_record.json"),
    ]
    for c in candidates:
        if c not in paths and os.path.exists(c):
            paths.append(c)
    return paths


def load_all_records() -> List[Dict[str, Any]]:
    """
    Loads all invoice records from primary JSON file and merges
    with any existing records from other known app installation/portable directories.
    Ensures no past invoices are missing across portable and installed versions.
    """
    records_by_no = {}
    known_paths = get_known_records_paths()

    for path in known_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for r in data:
                            inv = str(r.get("invoice_no", "")).strip()
                            if inv:
                                if inv not in records_by_no:
                                    records_by_no[inv] = r
                                else:
                                    curr = records_by_no[inv]
                                    if float(r.get("grand_total", 0.0) or 0.0) >= float(curr.get("grand_total", 0.0) or 0.0):
                                        records_by_no[inv] = r
            except Exception as e:
                print(f"Error reading records from {path}: {e}")

    result = list(records_by_no.values())
    try:
        result.sort(key=lambda r: int(r.get("invoice_no", 0)), reverse=True)
    except Exception:
        pass

    primary_path = get_records_json_path()
    try:
        with open(primary_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    return result


def save_all_records(records: List[Dict[str, Any]]) -> bool:
    """Saves records list to primary JSON file and mirrors to Master Vault."""
    path = get_records_json_path()
    success = False
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        success = True
    except Exception as e:
        print(f"Error saving records to {path}: {e}")

    # Mirror to Master Vault in Documents if different
    master_json = os.path.join(os.path.expanduser("~"), "Documents", "Silver Premium Invoices", "invoices_record.json")
    if os.path.abspath(master_json) != os.path.abspath(path):
        try:
            os.makedirs(os.path.dirname(master_json), exist_ok=True)
            with open(master_json, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    return success


def get_next_sequential_number(default_start: int = 102630) -> int:
    """
    Finds the highest existing invoice number from:
    1. Saved records JSON
    2. Any existing PDF filenames in the Invoices/ directory
    and returns highest + 1.
    """
    highest = default_start - 1  # So default next will be default_start

    # 1. Check JSON records
    records = load_all_records()
    for rec in records:
        inv_str = str(rec.get("invoice_no", ""))
        nums = re.findall(r'\d+', inv_str)
        if nums:
            try:
                val = int(nums[-1])
                if val > highest:
                    highest = val
            except ValueError:
                pass

    # 2. Check files in Invoices directory
    invoices_folder = get_invoices_dir()
    if os.path.exists(invoices_folder):
        for fname in os.listdir(invoices_folder):
            if fname.lower().endswith(".pdf"):
                # Matches patterns like '102630 - ...' or 'Invoice_102630...'
                nums = re.findall(r'\b\d{4,10}\b', fname)
                if nums:
                    try:
                        val = int(nums[0])
                        if val > highest:
                            highest = val
                    except ValueError:
                        pass

    return highest + 1


def record_new_invoice(
    invoice_no: str,
    date_str: str,
    client_name: str,
    customer_company: str,
    subtotal: float,
    vat_total: float,
    grand_total: float,
    pdf_filename: str
) -> Dict[str, Any]:
    """
    Appends a new invoice record to both JSON and CSV files.
    """
    invoices_dir = get_invoices_dir()
    full_pdf_path = os.path.join(invoices_dir, pdf_filename)

    record = {
        "invoice_no": invoice_no,
        "date": date_str,
        "client_name": client_name,
        "customer_company": customer_company,
        "subtotal": round(subtotal, 2),
        "vat_total": round(vat_total, 2),
        "grand_total": round(grand_total, 2),
        "filename": pdf_filename,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # 1. Update JSON
    records = load_all_records()
    # Remove existing with same invoice_no if overwriting
    records = [r for r in records if str(r.get("invoice_no")) != str(invoice_no)]
    records.append(record)
    save_all_records(records)

    # 2. Sync to CSV
    sync_csv_from_records(records)

    # 3. Mirror PDF file to Master Vault in Documents if different
    master_dir = os.path.join(os.path.expanduser("~"), "Documents", "Silver Premium Invoices")
    if os.path.abspath(master_dir) != os.path.abspath(invoices_dir):
        try:
            os.makedirs(master_dir, exist_ok=True)
            master_pdf = os.path.join(master_dir, pdf_filename)
            if os.path.exists(full_pdf_path) and not os.path.exists(master_pdf):
                import shutil
                shutil.copy2(full_pdf_path, master_pdf)
        except Exception:
            pass

    return record


def sync_csv_from_records(records: List[Dict[str, Any]]) -> bool:
    """Rewrites the CSV history file cleanly from the full records list and mirrors to Master Vault."""
    csv_path = get_records_csv_path()
    success = False
    try:
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Invoice #",
                "Date",
                "Client Name",
                "Customer Company",
                "Subtotal (AED)",
                "VAT 5% (AED)",
                "Grand Total (AED)",
                "File Name",
                "Created Timestamp"
            ])
            for rec in records:
                sub = float(rec.get("subtotal", 0.0))
                vat = float(rec.get("vat_total", 0.0))
                grand = float(rec.get("grand_total", 0.0))
                writer.writerow([
                    rec.get("invoice_no", ""),
                    rec.get("date", ""),
                    rec.get("client_name", ""),
                    rec.get("customer_company", ""),
                    f"{sub:,.2f}",
                    f"{vat:,.2f}",
                    f"{grand:,.2f}",
                    rec.get("filename", ""),
                    rec.get("created_at", "")
                ])
        success = True
    except Exception as e:
        print(f"Error syncing CSV: {e}")

    # Mirror to Master Vault
    master_csv = os.path.join(os.path.expanduser("~"), "Documents", "Silver Premium Invoices", "invoice_history.csv")
    if os.path.abspath(master_csv) != os.path.abspath(csv_path):
        try:
            os.makedirs(os.path.dirname(master_csv), exist_ok=True)
            import shutil
            shutil.copy2(csv_path, master_csv)
        except Exception:
            pass

    return success


def delete_invoice_record(invoice_no: str, delete_pdf: bool = True) -> bool:
    """
    Deletes an invoice record by invoice number.
    1. Removes from JSON records
    2. Synchronizes CSV history file
    3. Deletes associated PDF files from Invoices/ directory so sequential counting rolls back
    """
    records = load_all_records()
    inv_str = str(invoice_no).strip()

    # Find matching records
    matching = [r for r in records if str(r.get("invoice_no", "")).strip() == inv_str]
    if not matching:
        matching = [r for r in records if str(r.get("filename", "")).strip() == inv_str]

    # Delete PDF files if requested
    if delete_pdf:
        invoices_dir = get_invoices_dir()
        files_to_remove = set()

        for r in matching:
            fname = r.get("filename")
            if fname:
                files_to_remove.add(fname)

        if os.path.exists(invoices_dir):
            for fname in os.listdir(invoices_dir):
                if fname.lower().endswith(".pdf"):
                    if fname.startswith(f"{inv_str} - ") or fname == f"{inv_str}.pdf" or fname == f"_preview_{inv_str}.pdf":
                        files_to_remove.add(fname)

        for fname in files_to_remove:
            fpath = os.path.join(invoices_dir, fname)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception as e:
                    print(f"Warning: Could not delete PDF file {fpath}: {e}")

    # Remove from records list
    records = [r for r in records if str(r.get("invoice_no", "")).strip() != inv_str and str(r.get("filename", "")).strip() != inv_str]
    save_all_records(records)
    sync_csv_from_records(records)
    return True


def get_standard_pdf_filename(invoice_no: str, client_name: str) -> str:
    """
    Generates standard formatted filename:
    e.g. '102630 - Rochelle Visa Renewal.pdf'
    """
    inv_clean = sanitize_filename(str(invoice_no))
    client_clean = sanitize_filename(str(client_name))
    if client_clean:
        return f"{inv_clean} - {client_clean}.pdf"
    return f"{inv_clean}.pdf"


def open_invoices_folder():
    """Opens the Invoices archive directory in Windows Explorer."""
    folder = get_invoices_dir()
    os.startfile(folder)


def open_pdf_file(filename_or_path: str) -> bool:
    """Opens a PDF file in system default viewer, searching known invoice archives as fallback."""
    if os.path.isabs(filename_or_path) and os.path.exists(filename_or_path):
        os.startfile(filename_or_path)
        return True

    fname = os.path.basename(filename_or_path)
    # 1. Primary invoices directory
    primary = os.path.join(get_invoices_dir(), fname)
    if os.path.exists(primary):
        os.startfile(primary)
        return True

    # 2. Check other known invoice folders
    for rec_p in get_known_records_paths():
        cand = os.path.join(os.path.dirname(rec_p), fname)
        if os.path.exists(cand):
            os.startfile(cand)
            return True

    return False


def parse_record_date(date_str: str, created_at: str = "") -> Optional[datetime]:
    """
    Parses date from invoice record date string or created_at string.
    Supports formats like '11th Sep 2026', '04th September 2026', '2026-09-11', '11/09/2026', etc.
    """
    # 1. Try date_str with ordinal suffixes removed (e.g. 11th -> 11)
    if date_str:
        clean = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', str(date_str)).strip()
        for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(clean, fmt)
            except ValueError:
                pass

    # 2. Try created_at
    if created_at:
        clean_created = str(created_at).strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
            try:
                return datetime.strptime(clean_created, fmt)
            except ValueError:
                pass

    return None


def get_available_years(records: Optional[List[Dict[str, Any]]] = None) -> List[str]:
    """Returns sorted unique years (descending) found in records."""
    if records is None:
        records = load_all_records()
    years = set()
    for r in records:
        dt = parse_record_date(r.get("date", ""), r.get("created_at", ""))
        if dt:
            years.add(str(dt.year))
    if not years:
        years.add(str(datetime.now().year))
    return sorted(list(years), reverse=True)


def filter_records(
    records: List[Dict[str, Any]],
    query: str = "",
    company: str = "",
    year: str = "",
    month: str = ""
) -> List[Dict[str, Any]]:
    """
    Filters records by query string, company name, year (e.g. '2026'), and month ('1'..'12').
    Completely case-insensitive and robust against dropdown display text.
    """
    filtered = []
    clean_query = (query or "").lower().strip()
    clean_company = (company or "").lower().strip()
    clean_year = (year or "").lower().strip()
    clean_month = (month or "").lower().strip()

    is_all_companies = (not clean_company) or clean_company.startswith("all")
    is_all_years = (not clean_year) or clean_year.startswith("all")
    is_all_months = (not clean_month) or clean_month.startswith("all")

    target_month_int = None
    if not is_all_months:
        digits = re.findall(r'\d+', clean_month)
        if digits:
            try:
                target_month_int = int(digits[0])
            except ValueError:
                pass

    for rec in records:
        # 1. Check company filter
        rec_comp = str(rec.get("customer_company", "")).strip()
        if not is_all_companies:
            if rec_comp.lower() != clean_company:
                continue

        # 2. Check date filter (year & month)
        dt = parse_record_date(rec.get("date", ""), rec.get("created_at", ""))
        if not is_all_years:
            if not dt or str(dt.year) != clean_year:
                continue

        if not is_all_months and target_month_int is not None:
            if not dt or dt.month != target_month_int:
                continue

        # 3. Check search query
        if clean_query:
            inv_no = str(rec.get("invoice_no", ""))
            date_s = str(rec.get("date", ""))
            client = str(rec.get("client_name", ""))
            fname = str(rec.get("filename", ""))
            combined = f"{inv_no} {date_s} {client} {rec_comp} {fname}".lower()
            if clean_query not in combined:
                continue

        filtered.append(rec)
    return filtered


def calculate_vat_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates aggregated financial metrics for given records:
    total_subtotal, total_vat, total_grand, and invoice_count.
    """
    tot_sub = 0.0
    tot_vat = 0.0
    tot_grand = 0.0
    for r in records:
        tot_sub += float(r.get("subtotal", 0.0) or 0.0)
        tot_vat += float(r.get("vat_total", 0.0) or 0.0)
        tot_grand += float(r.get("grand_total", 0.0) or 0.0)

    return {
        "invoice_count": len(records),
        "total_subtotal": round(tot_sub, 2),
        "total_vat": round(tot_vat, 2),
        "total_grand": round(tot_grand, 2),
    }


def get_company_vat_breakdown(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Groups records by customer company / profile name and returns aggregated summary:
    - company_name
    - invoice_count
    - total_subtotal
    - total_vat
    - total_grand
    - latest_date
    Sorted descending by total_vat.
    """
    grouped = {}
    for r in records:
        comp = str(r.get("customer_company", "")).strip() or "Unassigned Company"
        sub = float(r.get("subtotal", 0.0) or 0.0)
        vat = float(r.get("vat_total", 0.0) or 0.0)
        grand = float(r.get("grand_total", 0.0) or 0.0)
        date_s = str(r.get("date", "")).strip()
        dt = parse_record_date(date_s, r.get("created_at", ""))

        if comp not in grouped:
            grouped[comp] = {
                "company_name": comp,
                "invoice_count": 0,
                "total_subtotal": 0.0,
                "total_vat": 0.0,
                "total_grand": 0.0,
                "latest_date": date_s,
                "_latest_dt": dt or datetime.min
            }

        entry = grouped[comp]
        entry["invoice_count"] += 1
        entry["total_subtotal"] += sub
        entry["total_vat"] += vat
        entry["total_grand"] += grand
        if dt and dt > entry["_latest_dt"]:
            entry["latest_date"] = date_s
            entry["_latest_dt"] = dt

    result = []
    for comp, data in grouped.items():
        result.append({
            "company_name": data["company_name"],
            "invoice_count": data["invoice_count"],
            "total_subtotal": round(data["total_subtotal"], 2),
            "total_vat": round(data["total_vat"], 2),
            "total_grand": round(data["total_grand"], 2),
            "latest_date": data["latest_date"]
        })

    # Sort primarily by total_vat descending, then total_grand descending
    result.sort(key=lambda x: (x["total_vat"], x["total_grand"]), reverse=True)
    return result


def export_vat_summary_csv(breakdown: List[Dict[str, Any]], filepath: str) -> bool:
    """Exports company VAT breakdown to CSV."""
    try:
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Customer / Company Profile",
                "Invoice Count",
                "Taxable Subtotal (AED)",
                "Total VAT 5% (AED)",
                "Grand Total (AED)",
                "Latest Invoice Date"
            ])
            for item in breakdown:
                writer.writerow([
                    item.get("company_name", ""),
                    item.get("invoice_count", 0),
                    f"{item.get('total_subtotal', 0.0):,.2f}",
                    f"{item.get('total_vat', 0.0):,.2f}",
                    f"{item.get('total_grand', 0.0):,.2f}",
                    item.get("latest_date", "")
                ])
        return True
    except Exception as e:
        print(f"Error exporting VAT summary CSV: {e}")
        return False


if __name__ == "__main__":
    print("Invoices directory:", get_invoices_dir())
    print("Next sequential invoice #:", get_next_sequential_number())

