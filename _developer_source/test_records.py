"""
Tests for records manager and sequential numbering
"""
import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.records_manager import (
    get_invoices_dir,
    get_next_sequential_number,
    record_new_invoice,
    load_all_records,
    delete_invoice_record,
    get_standard_pdf_filename,
    sanitize_filename
)


class TestRecordsManager(unittest.TestCase):
    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("Ms. Rochelle / Visa : Test?"), "Ms. Rochelle  Visa  Test")

    def test_standard_pdf_name(self):
        name = get_standard_pdf_filename("102630", "Ms. Rochelle Visa Renewal")
        self.assertEqual(name, "102630 - Ms. Rochelle Visa Renewal.pdf")

    def test_record_and_sequence(self):
        next_num = get_next_sequential_number(102630)
        self.assertGreaterEqual(next_num, 102630)

        # Record a test invoice
        test_inv = str(next_num)
        rec = record_new_invoice(
            invoice_no=test_inv,
            date_str="04th Sep 2026",
            client_name="Test Client",
            customer_company="Test Company",
            subtotal=1000.0,
            vat_total=50.0,
            grand_total=1050.0,
            pdf_filename=f"{test_inv} - Test Client.pdf"
        )
        self.assertEqual(rec["invoice_no"], test_inv)

        # Next sequential number should now be next_num + 1!
        new_next = get_next_sequential_number(102630)
        self.assertEqual(new_next, next_num + 1)

        # Check records loaded
        all_recs = load_all_records()
        self.assertTrue(any(r["invoice_no"] == test_inv for r in all_recs))

        # Delete the test invoice
        delete_invoice_record(test_inv, delete_pdf=True)

        # Sequence should roll back to next_num
        rolled_back = get_next_sequential_number(102630)
        self.assertEqual(rolled_back, next_num)

        # Verify not in records
        all_recs = load_all_records()
        self.assertFalse(any(r["invoice_no"] == test_inv for r in all_recs))


if __name__ == "__main__":
    unittest.main()
