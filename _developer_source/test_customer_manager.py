"""
Unit Tests for Customer Manager Module
"""
import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.customer_manager import (
    load_customers,
    save_customers,
    save_or_update_customer,
    get_customer_by_id,
    get_customer_by_name,
    delete_customer,
    import_from_invoices,
    get_customers_file_path
)


class TestCustomerManager(unittest.TestCase):
    def setUp(self):
        # Backup existing customers file if any
        self.path = get_customers_file_path()
        self.backup = None
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                self.backup = f.read()

    def tearDown(self):
        # Restore backup if available
        if self.backup is not None:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(self.backup)

    def test_load_and_seed(self):
        customers = load_customers()
        self.assertIsInstance(customers, list)
        self.assertGreaterEqual(len(customers), 1)
        # First entry should have company_name
        self.assertTrue(bool(customers[0].get("company_name")))

    def test_create_and_fetch_customer(self):
        test_cust = {
            "company_name": "Al Noor Trading FZE",
            "client_name": "Mr. Ahmed Al Mansoori",
            "address": "Downtown Dubai, UAE",
            "trn": "100987654321003",
            "phone": "+971 50 123 4567",
            "email": "ahmed@alnoor.ae",
            "notes": "VIP Corporate Account"
        }
        saved = save_or_update_customer(test_cust)
        self.assertTrue(saved.get("id"))
        self.assertEqual(saved["company_name"], "Al Noor Trading FZE")

        # Fetch by ID
        fetched = get_customer_by_id(saved["id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["client_name"], "Mr. Ahmed Al Mansoori")

        # Fetch by Name
        fetched_name = get_customer_by_name("al noor trading fze")
        self.assertIsNotNone(fetched_name)
        self.assertEqual(fetched_name["id"], saved["id"])

        # Update
        test_cust["id"] = saved["id"]
        test_cust["address"] = "DIFC Gate Avenue, Dubai"
        updated = save_or_update_customer(test_cust)
        self.assertEqual(updated["id"], saved["id"])
        self.assertEqual(updated["address"], "DIFC Gate Avenue, Dubai")

        # Delete
        deleted = delete_customer(saved["id"])
        self.assertTrue(deleted)
        self.assertIsNone(get_customer_by_id(saved["id"]))

    def test_import_from_invoices(self):
        # Even if invoice records are empty, import_from_invoices should run cleanly and return an int
        count = import_from_invoices()
        self.assertIsInstance(count, int)
        self.assertGreaterEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
