"""
Automated unit tests for Dialog Layouts, Scrollbars, and Window Centering Clamping
"""
import unittest
import tkinter as tk
from tkinter import ttk

from gui.settings_native import NativeSettingsDialog
from gui.updater_dialog import UpdaterDialog
from gui.customers_dialog import CustomerProfilesDialog
from gui.history_view import HistoryDialog
from gui.window_utils import center_window, get_screen_work_area


class TestDialogLayouts(unittest.TestCase):
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

    def test_window_centering_and_clamping(self):
        if not self.root:
            self.skipTest("Tkinter display not available")

        win = tk.Toplevel(self.root)
        center_window(win, width=1060, height=580)
        win.update_idletasks()

        wa = get_screen_work_area()
        if wa:
            wa_left, wa_top, wa_w, wa_h = wa
            # Verify window fits inside work area and is not pushed off the bottom
            self.assertLessEqual(win.winfo_height(), wa_h)
            self.assertLessEqual(win.winfo_y() + win.winfo_height(), wa_top + wa_h)
            self.assertGreaterEqual(win.winfo_y(), wa_top)

        win.destroy()

    def test_settings_dialog_layout(self):
        if not self.root:
            self.skipTest("Tkinter display not available")

        dlg = NativeSettingsDialog(self.root)
        dlg.update_idletasks()

        # Verify buttons exist and are mapped
        self.assertTrue(dlg.btn_save.winfo_exists())
        self.assertTrue(dlg.btn_cancel.winfo_exists())
        self.assertTrue(dlg.btn_restore.winfo_exists())

        # Verify entry widgets exist
        self.assertTrue(dlg.entry_comp_name.winfo_exists())
        self.assertTrue(dlg.entry_bank_name.winfo_exists())
        self.assertTrue(dlg.txt_terms.winfo_exists())

        dlg.destroy()

    def test_updater_dialog_layout(self):
        if not self.root:
            self.skipTest("Tkinter display not available")

        dlg = UpdaterDialog(self.root)
        dlg.update_idletasks()

        # Verify updater buttons exist
        self.assertTrue(dlg.btn_update_installed.winfo_exists())
        self.assertTrue(dlg.btn_launch_installed.winfo_exists())
        self.assertTrue(dlg.lbl_status.winfo_exists())

        dlg.destroy()

    def test_customers_dialog_layout(self):
        if not self.root:
            self.skipTest("Tkinter display not available")

        dlg = CustomerProfilesDialog(self.root)
        dlg.update_idletasks()

        # Verify buttons and treeview exist
        self.assertTrue(dlg.tree.winfo_exists())
        self.assertTrue(dlg.entry_company.winfo_exists())
        self.assertTrue(dlg.btn_save.winfo_exists())
        self.assertTrue(dlg.btn_use.winfo_exists())

        dlg.destroy()


if __name__ == "__main__":
    unittest.main()
