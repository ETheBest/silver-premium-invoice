"""
Window Geometry & UI Utilities
Provides smooth window centering and responsive geometry calculations.
"""
import tkinter as tk


def get_screen_work_area():
    """
    Returns (left, top, width, height) of the usable screen area
    excluding the Windows taskbar and system docks.
    """
    try:
        import ctypes
        from ctypes import wintypes
        rect = wintypes.RECT()
        # SPI_GETWORKAREA = 0x0030
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
            return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
    except Exception:
        pass
    return None


def center_window(window, parent=None, width: int = None, height: int = None):
    """
    Centers a Tkinter window or Toplevel dialog smoothly over its parent or screen.
    Guarantees the window fits within the visible work area and is NEVER obscured by the Windows taskbar.
    """
    window.update_idletasks()
    w = width if width else window.winfo_reqwidth()
    h = height if height else window.winfo_reqheight()

    # Fallback to current dimensions if req dimensions too small
    if w < 100:
        w = window.winfo_width()
    if h < 100:
        h = window.winfo_height()

    wa = get_screen_work_area()
    if wa:
        wa_left, wa_top, wa_w, wa_h = wa
    else:
        wa_left, wa_top = 0, 0
        wa_w = window.winfo_screenwidth()
        wa_h = window.winfo_screenheight() - 70

    # Title bar & frame border headroom buffer
    titlebar_pad = 42

    # Clamp window dimensions to usable work area
    w = min(w, wa_w - 24)
    h = min(h, wa_h - titlebar_pad - 16)

    if parent and hasattr(parent, "winfo_exists") and parent.winfo_exists():
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
    else:
        x = wa_left + (wa_w - w) // 2
        y = wa_top + (wa_h - h - titlebar_pad) // 2

    # Strictly clamp bounds inside work area so bottom action bar is never lost
    min_x = wa_left + 12
    max_x = max(min_x, wa_left + wa_w - w - 12)
    min_y = wa_top + 10
    max_y = max(min_y, wa_top + wa_h - h - titlebar_pad)

    x = max(min_x, min(x, max_x))
    y = max(min_y, min(y, max_y))

    window.geometry(f"{w}x{h}+{x}+{y}")
