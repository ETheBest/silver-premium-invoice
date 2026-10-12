"""
Silver Premium Tax Invoice Generator
Desktop Application Entry Point (Native High-Performance Edition)
"""
import os
import sys
import ctypes

# Fix high-DPI scaling on Windows
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from gui.app_native import NativeInvoiceApp


def main():
    app = NativeInvoiceApp()
    app.mainloop()


if __name__ == "__main__":
    main()
