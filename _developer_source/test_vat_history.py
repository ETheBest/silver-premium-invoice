"""
Unit tests for VAT tracking, date parsing, company breakdown, and history filters.
"""
import unittest
from datetime import datetime

from core.records_manager import (
    parse_record_date,
    get_available_years,
    filter_records,
    calculate_vat_summary,
    get_company_vat_breakdown
)


class TestVATHistory(unittest.TestCase):
    def setUp(self):
        self.sample_records = [
            {
                "invoice_no": "102630",
                "date": "11th Sep 2026",
                "client_name": "Ms. Rochelle Visa",
                "customer_company": "Petro Gulf Trading LLC",
                "subtotal": 10000.0,
                "vat_total": 500.0,
                "grand_total": 10500.0,
                "filename": "102630 - Petro.pdf",
                "created_at": "2026-09-11 12:00:00"
            },
            {
                "invoice_no": "102631",
                "date": "15th Aug 2026",
                "client_name": "Capt. Tariq",
                "customer_company": "Falcon Aviation",
                "subtotal": 20000.0,
                "vat_total": 1000.0,
                "grand_total": 21000.0,
                "filename": "102631 - Falcon.pdf",
                "created_at": "2026-08-15 10:00:00"
            },
            {
                "invoice_no": "102632",
                "date": "02nd Jan 2025",
                "client_name": "Ms. Rochelle",
                "customer_company": "Petro Gulf Trading LLC",
                "subtotal": 4000.0,
                "vat_total": 200.0,
                "grand_total": 4200.0,
                "filename": "102632 - Petro.pdf",
                "created_at": "2025-01-02 09:30:00"
            },
        ]

    def test_parse_record_date(self):
        dt1 = parse_record_date("11th Sep 2026")
        self.assertIsNotNone(dt1)
        self.assertEqual(dt1.year, 2026)
        self.assertEqual(dt1.month, 9)
        self.assertEqual(dt1.day, 11)

        dt2 = parse_record_date("01st January 2025")
        self.assertIsNotNone(dt2)
        self.assertEqual(dt2.year, 2025)
        self.assertEqual(dt2.month, 1)

        dt3 = parse_record_date("", "2024-05-20 14:00:00")
        self.assertIsNotNone(dt3)
        self.assertEqual(dt3.year, 2024)
        self.assertEqual(dt3.month, 5)

    def test_get_available_years(self):
        years = get_available_years(self.sample_records)
        self.assertIn("2026", years)
        self.assertIn("2025", years)

    def test_vat_summary(self):
        summary = calculate_vat_summary(self.sample_records)
        self.assertEqual(summary["invoice_count"], 3)
        self.assertAlmostEqual(summary["total_subtotal"], 34000.0)
        self.assertAlmostEqual(summary["total_vat"], 1700.0)
        self.assertAlmostEqual(summary["total_grand"], 35700.0)

    def test_company_vat_breakdown(self):
        breakdown = get_company_vat_breakdown(self.sample_records)
        self.assertEqual(len(breakdown), 2)
        
        # Falcon Aviation has 1000 VAT, Petro Gulf has 500+200 = 700 VAT
        # Sorted by VAT descending: Falcon Aviation first (1000), then Petro Gulf (700)
        self.assertEqual(breakdown[0]["company_name"], "Falcon Aviation")
        self.assertEqual(breakdown[0]["invoice_count"], 1)
        self.assertEqual(breakdown[0]["total_vat"], 1000.0)

        self.assertEqual(breakdown[1]["company_name"], "Petro Gulf Trading LLC")
        self.assertEqual(breakdown[1]["invoice_count"], 2)
        self.assertEqual(breakdown[1]["total_vat"], 700.0)
        self.assertEqual(breakdown[1]["total_subtotal"], 14000.0)

    def test_filter_by_company(self):
        filtered = filter_records(self.sample_records, company="Petro Gulf Trading LLC")
        self.assertEqual(len(filtered), 2)
        for r in filtered:
            self.assertEqual(r["customer_company"], "Petro Gulf Trading LLC")

    def test_filter_by_year(self):
        filtered_2026 = filter_records(self.sample_records, year="2026")
        self.assertEqual(len(filtered_2026), 2)

        filtered_2025 = filter_records(self.sample_records, year="2025")
        self.assertEqual(len(filtered_2025), 1)
        self.assertEqual(filtered_2025[0]["invoice_no"], "102632")

    def test_filter_by_month(self):
        filtered_sep = filter_records(self.sample_records, month="9")
        self.assertEqual(len(filtered_sep), 1)
        self.assertEqual(filtered_sep[0]["invoice_no"], "102630")

        filtered_aug = filter_records(self.sample_records, month="08")
        self.assertEqual(len(filtered_aug), 1)
        self.assertEqual(filtered_aug[0]["invoice_no"], "102631")

    def test_filter_combined(self):
        filtered = filter_records(
            self.sample_records,
            company="Petro Gulf Trading LLC",
            year="2026",
            month="9"
        )
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["invoice_no"], "102630")


if __name__ == "__main__":
    unittest.main()
