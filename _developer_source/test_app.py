"""
Comprehensive Test Suite for Silver Premium Invoice Generator
"""
import os
import sys
import unittest
import pymupdf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.num_to_words_helper import amount_to_aed_words
from core.settings_manager import load_settings, save_settings, get_next_invoice_number, increment_invoice_number
from core.pdf_engine import generate_invoice_pdf


class TestNumToWords(unittest.TestCase):
    def test_reference_value(self):
        self.assertEqual(
            amount_to_aed_words(6510.00),
            "AED SIX THOUSAND FIVE HUNDRED TEN & ZERO FILS ONLY"
        )

    def test_fils_value(self):
        self.assertEqual(
            amount_to_aed_words(6510.50),
            "AED SIX THOUSAND FIVE HUNDRED TEN & FIFTY FILS ONLY"
        )

    def test_zero_value(self):
        self.assertEqual(
            amount_to_aed_words(0.00),
            "AED ZERO & ZERO FILS ONLY"
        )

    def test_twenty_five_fils(self):
        self.assertEqual(
            amount_to_aed_words(100.25),
            "AED ONE HUNDRED & TWENTY FIVE FILS ONLY"
        )


class TestSettingsManager(unittest.TestCase):
    def test_load_defaults(self):
        s = load_settings()
        self.assertIn("company", s)
        self.assertIn("bank", s)
        self.assertEqual(s["company"]["trn"], "104171277700003")
        self.assertEqual(s["bank"]["bank_name"], "WIO BUSINESS")

    def test_invoice_sequence(self):
        inv_str = get_next_invoice_number()
        self.assertTrue(inv_str.isdigit() or len(inv_str) > 0)


class TestPDFEngine(unittest.TestCase):
    def test_pdf_generation(self):
        test_data = {
            "invoice_no": "102630",
            "date": "04th Sep 2026",
            "client_name": "Ms. Rochelle Visa Renewal",
            "company": {
                "name": "SILVER PREMIUM DOCUMENTS CLEARING CO. L.L.C",
                "trn": "104171277700003",
                "footer_text": "OFFICE 960, TAMANI ARTS, BAY SQUARE, DUBAI - U.A.E. | Tel: 04 433 8970"
            },
            "customer": {
                "company_name": "Petro Gulf Refined Oil Products Trading L.L.C",
                "address": "Business Bay, Dubai",
                "trn": "100459434500003"
            },
            "bank": {
                "bank_name": "WIO BUSINESS",
                "account_no": "9895248605",
                "beneficiary_name": "Silver Premium Documents Clearing Co LLC",
                "iban": "AE620860000009895248605"
            },
            "items": [
                {
                    "description": "Visa Renewal",
                    "quantity": 1,
                    "unit_amount": 6300.00,
                    "vat_applicable": False,
                    "vat_amount": 0.00,
                    "line_total": 6300.00
                },
                {
                    "description": "Service Charges",
                    "quantity": 1,
                    "unit_amount": 200.00,
                    "vat_applicable": True,
                    "vat_amount": 10.00,
                    "line_total": 210.00
                }
            ],
            "subtotal": 6500.00,
            "vat_total": 10.00,
            "grand_total": 6510.00,
            "amount_in_words": "AED SIX THOUSAND FIVE HUNDRED TEN & ZERO FILS ONLY",
            "terms": [
                "All govt. charges are estimates, may change at any time.",
                "Timely payment is required for us to proceed with your work."
            ]
        }
        test_pdf = os.path.join(BASE_DIR, "unit_test_out.pdf")
        generate_invoice_pdf(test_data, test_pdf)
        self.assertTrue(os.path.exists(test_pdf))
        self.assertGreater(os.path.getsize(test_pdf), 10000)

        # Inspect generated PDF with PyMuPDF
        doc = pymupdf.open(test_pdf)
        self.assertEqual(len(doc), 1)
        page = doc[0]
        # Check A4 dimensions
        self.assertAlmostEqual(page.rect.width, 595.28, delta=1.0)
        self.assertAlmostEqual(page.rect.height, 841.89, delta=1.0)

        text = page.get_text()
        self.assertIn("TAX INVOICE", text)
        self.assertIn("104171277700003", text)
        self.assertIn("102630", text)
        self.assertIn("Petro Gulf Refined Oil Products Trading L.L.C", text)
        self.assertIn("Visa Renewal", text)
        self.assertIn("Service Charges", text)
        self.assertIn("WIO BUSINESS", text)
        self.assertIn("AE620860000009895248605", text)
        self.assertIn("AED SIX THOUSAND FIVE HUNDRED TEN & ZERO FILS ONLY", text)
        doc.close()

    def test_pdf_generation_clean_layout(self):
        test_data = {
            "invoice_no": "102631",
            "date": "04th Sep 2026",
            "client_name": "Sample Reference",
            "company": {
                "name": "SILVER PREMIUM DOCUMENTS CLEARING CO. L.L.C",
                "trn": "104171277700003"
            },
            "customer": {
                "company_name": "Sample Corporate Client LLC",
                "address": "Dubai, United Arab Emirates",
                "trn": "100XXXXXXXXX003"
            },
            "bank": {
                "bank_name": "WIO BUSINESS",
                "account_no": "9895248605",
                "beneficiary_name": "Silver Premium Documents Clearing Co LLC",
                "iban": "AE620860000009895248605"
            },
            "items": [
                {
                    "description": "General Consulting Services",
                    "quantity": 1,
                    "unit_amount": 1000.00,
                    "vat_applicable": True,
                    "vat_amount": 50.00,
                    "line_total": 1050.00
                }
            ],
            "subtotal": 1000.00,
            "vat_total": 50.00,
            "grand_total": 1050.00,
            "amount_in_words": "AED ONE THOUSAND FIFTY & ZERO FILS ONLY",
            "terms": [
                "All govt. charges are estimates, may change at any time."
            ]
        }
        test_pdf = os.path.join(BASE_DIR, "unit_test_stamp_out.pdf")
        generate_invoice_pdf(test_data, test_pdf)
        self.assertTrue(os.path.exists(test_pdf))
        doc = pymupdf.open(test_pdf)
        text = doc[0].get_text()
        self.assertIn("TAX INVOICE", text)
        self.assertIn("Terms & Conditions", text)
        self.assertNotIn("Authorized Signatory", text)
        doc.close()


class TestNativeAppGUI(unittest.TestCase):
    def setUp(self):
        from gui.app_native import NativeInvoiceApp
        self.app = NativeInvoiceApp()

    def tearDown(self):
        self.app.destroy()

    def test_customer_dropdown_populated(self):
        values = list(self.app.combo_cust["values"])
        self.assertGreaterEqual(len(values), 1)

    def test_customer_dropdown_selection(self):
        values = list(self.app.combo_cust["values"])
        if values:
            selected = values[0]
            self.app.var_cust_dropdown.set(selected)
            self.app._on_customer_selected()
            self.assertEqual(self.app.entry_cust_company.get(), selected)


if __name__ == "__main__":
    unittest.main()
