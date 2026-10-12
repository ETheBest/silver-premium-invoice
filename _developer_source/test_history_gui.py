"""
Automated unit tests for HistoryDialog UI logic
"""
import unittest
import tkinter as tk
import os
import tempfile

from gui.history_view import HistoryDialog
from core.records_manager import export_vat_summary_csv, get_company_vat_breakdown


class TestHistoryGUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception:
            cls.root = None

    @classmethod
    def tearDownClass(cls):
        if cls.root:
            try:
                cls.root.destroy()
            except Exception:
                pass

    def test_history_dialog_instantiation_and_filtering(self):
        if not self.root:
            self.skipTest("Tkinter display not available")

        dialog = HistoryDialog(self.root)
        self.assertIsNotNone(dialog)

        # Check KPI values initialized
        self.assertIn("Invoices", dialog.lbl_kpi_count.cget("text"))
        self.assertIn("AED", dialog.lbl_kpi_vat.cget("text"))

        # Test selecting a year filter
        years = dialog.cb_year.cget("values")
        if len(years) > 1:
            dialog.var_year.set(years[1])
            dialog._apply_filters()
            self.assertIsNotNone(dialog.lbl_kpi_subtotal.cget("text"))

        # Test selecting a month filter
        dialog.var_month.set("09 - Sep")
        dialog._apply_filters()

        # Test resetting filters
        dialog._reset_filters()
        self.assertEqual(dialog.var_company.get(), "All Companies")
        self.assertEqual(dialog.var_year.get(), "All Years")
        self.assertEqual(dialog.var_month.get(), "All Months")

        # Test export vat summary to temp file
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
            temp_path = tf.name
        try:
            breakdown = get_company_vat_breakdown(dialog.records)
            success = export_vat_summary_csv(breakdown, temp_path)
            self.assertTrue(success)
            self.assertTrue(os.path.exists(temp_path))
            self.assertGreater(os.path.getsize(temp_path), 0)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        dialog.destroy()


if __name__ == "__main__":
    unittest.main()
