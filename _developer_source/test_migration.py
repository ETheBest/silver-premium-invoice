"""
Tests for Multi-Version Migration & Data Synchronization Manager
"""
import os
import sys
import json
import shutil
import tempfile
import zipfile
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.migration_manager import (
    APP_VERSION,
    get_master_vault_dir,
    get_master_appdata_dir,
    load_version_ledger,
    save_version_ledger,
    recover_record_from_pdf,
    scan_and_merge_previous_versions,
    import_from_custom_directory,
    create_full_backup_zip,
    check_and_run_startup_migration
)
from core.records_manager import load_all_records


class TestMigrationManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="silver_test_mig_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_version_ledger(self):
        ledger = load_version_ledger()
        self.assertIn("current_version", ledger)
        self.assertIn("previous_versions", ledger)
        self.assertIn("scanned_locations", ledger)
        
        # Test modifying and saving
        orig_ver = ledger.get("current_version")
        ledger["test_flag"] = True
        save_version_ledger(ledger)
        
        reloaded = load_version_ledger()
        self.assertTrue(reloaded.get("test_flag"))

    def test_pdf_recovery_fallback_from_name(self):
        # Create a blank or dummy file named in standard format
        dummy_pdf = os.path.join(self.temp_dir, "109999 - Quantum Robotics Services.pdf")
        with open(dummy_pdf, "w") as f:
            f.write("%PDF-1.4 dummy content")

        rec = recover_record_from_pdf(dummy_pdf)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["invoice_no"], "109999")
        self.assertEqual(rec["client_name"], "Quantum Robotics Services")
        self.assertEqual(rec["pdf_filename"], "109999 - Quantum Robotics Services.pdf")

    def test_custom_directory_import(self):
        # Setup an external folder representing an older backup
        old_invoices_dir = os.path.join(self.temp_dir, "Invoices")
        os.makedirs(old_invoices_dir, exist_ok=True)
        
        mock_record = {
            "invoice_no": "109888",
            "date": "15th Aug 2026",
            "client_name": "Old Backup Client",
            "customer_company": "Legacy Corp",
            "subtotal": 5000.0,
            "vat_total": 250.0,
            "grand_total": 5250.0,
            "pdf_filename": "109888 - Old Backup Client.pdf"
        }
        with open(os.path.join(old_invoices_dir, "invoices_record.json"), "w", encoding="utf-8") as f:
            json.dump([mock_record], f)

        # Also place a customer profile in old root
        with open(os.path.join(self.temp_dir, "customers.json"), "w", encoding="utf-8") as f:
            json.dump({
                "customers": [
                    {
                        "id": "cust_mock_1",
                        "company_name": "Legacy Corp",
                        "client_name": "Old Backup Client",
                        "address": "Dubai Silicon Oasis",
                        "trn": "100000000000003"
                    }
                ]
            }, f)

        # Run custom import
        summary = import_from_custom_directory(self.temp_dir)
        self.assertGreaterEqual(summary["new_invoices"], 1)

        # Verify record exists in active records
        records = load_all_records()
        self.assertTrue(any(r["invoice_no"] == "109888" for r in records))

        # Cleanup the test invoice so we don't pollute live data
        from core.records_manager import delete_invoice_record
        delete_invoice_record("109888", delete_pdf=False)

    def test_create_full_backup_zip(self):
        target_zip = os.path.join(self.temp_dir, "test_backup.zip")
        success = create_full_backup_zip(target_zip)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(target_zip))
        self.assertGreater(os.path.getsize(target_zip), 0)

        with zipfile.ZipFile(target_zip, "r") as z:
            names = z.namelist()
            # Must have at least Invoices/invoices_record.json or invoice_history.csv
            self.assertTrue(any("invoices_record.json" in n or "invoice_history.csv" in n for n in names))

    def test_check_and_run_startup_migration(self):
        migrated, count = check_and_run_startup_migration()
        self.assertIsInstance(migrated, bool)
        self.assertGreaterEqual(count, 6)


if __name__ == "__main__":
    unittest.main()
