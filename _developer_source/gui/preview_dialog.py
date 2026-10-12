"""
Preview Dialog
Displays an interactive high-resolution visual preview of the generated invoice PDF.
Allows zooming, saving, and opening directly in system default viewer.
"""
import os
import tempfile
import pymupdf
from PIL import Image
import customtkinter as ctk
from tkinter import filedialog, messagebox
from typing import Dict, Any

from core.pdf_engine import generate_invoice_pdf


class PreviewDialog(ctk.CTkToplevel):
    def __init__(self, parent, invoice_data: Dict[str, Any], on_saved_callback=None):
        super().__init__(parent)
        self.invoice_data = invoice_data
        self.on_saved_callback = on_saved_callback
        self.title(f"Invoice Preview - #{self.invoice_data.get('invoice_no', 'Preview')}")
        self.geometry("780x860")
        self.minsize(600, 700)

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Temporary PDF path
        self.temp_pdf = os.path.join(tempfile.gettempdir(), f"temp_invoice_{self.invoice_data.get('invoice_no', 'preview')}.pdf")
        generate_invoice_pdf(self.invoice_data, self.temp_pdf)

        self.zoom_level = 1.0
        self.current_img = None
        self.current_ctk_img = None

        self._build_ui()
        self._load_and_render_pdf()

    def _build_ui(self):
        # Top toolbar
        toolbar = ctk.CTkFrame(self, height=50, corner_radius=0, fg_color="#1E293B")
        toolbar.pack(fill="x", side="top")

        lbl_title = ctk.CTkLabel(
            toolbar,
            text=f"📄 Tax Invoice Preview (#{self.invoice_data.get('invoice_no', '')})",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#F8FAFC"
        )
        lbl_title.pack(side="left", padx=16, pady=10)

        # Action Buttons on toolbar right
        btn_close = ctk.CTkButton(
            toolbar,
            text="✕ Close",
            width=75,
            height=32,
            fg_color="#475569",
            hover_color="#334155",
            command=self.destroy
        )
        btn_close.pack(side="right", padx=12, pady=8)

        btn_save = ctk.CTkButton(
            toolbar,
            text="💾 Save PDF",
            width=95,
            height=32,
            fg_color="#10B981",
            hover_color="#059669",
            font=ctk.CTkFont(weight="bold"),
            command=self._on_save_as
        )
        btn_save.pack(side="right", padx=6, pady=8)

        btn_system = ctk.CTkButton(
            toolbar,
            text="🖨️ Open in Viewer",
            width=130,
            height=32,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            command=self._open_in_system_viewer
        )
        btn_system.pack(side="right", padx=6, pady=8)

        # Zoom controls
        zoom_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        zoom_frame.pack(side="right", padx=12)

        btn_zoom_out = ctk.CTkButton(
            zoom_frame, text="➖", width=30, height=28,
            fg_color="#334155", hover_color="#475569",
            command=lambda: self._adjust_zoom(0.85)
        )
        btn_zoom_out.pack(side="left", padx=2)

        self.lbl_zoom = ctk.CTkLabel(zoom_frame, text="100%", width=45, font=ctk.CTkFont(size=12))
        self.lbl_zoom.pack(side="left", padx=2)

        btn_zoom_in = ctk.CTkButton(
            zoom_frame, text="➕", width=30, height=28,
            fg_color="#334155", hover_color="#475569",
            command=lambda: self._adjust_zoom(1.15)
        )
        btn_zoom_in.pack(side="left", padx=2)

        # Scrollable image container
        self.scroll_canvas = ctk.CTkScrollableFrame(self, fg_color="#0F172A")
        self.scroll_canvas.pack(fill="both", expand=True, padx=8, pady=8)

        self.lbl_image = ctk.CTkLabel(self.scroll_canvas, text="")
        self.lbl_image.pack(padx=10, pady=10, expand=True)

    def _load_and_render_pdf(self):
        """Renders the temporary PDF using PyMuPDF to high-DPI image."""
        try:
            doc = pymupdf.open(self.temp_pdf)
            page = doc[0]
            # Render at 160 DPI base
            dpi = int(160 * self.zoom_level)
            pix = page.get_pixmap(dpi=dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()

            display_w = int(img.width * (72.0 / dpi) * 1.6)
            display_h = int(img.height * (72.0 / dpi) * 1.6)

            self.current_ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width // 2, img.height // 2))
            self.lbl_image.configure(image=self.current_ctk_img)
            self.lbl_zoom.configure(text=f"{int(self.zoom_level * 100)}%")
        except Exception as e:
            messagebox.showerror("Preview Error", f"Failed to render preview: {e}")

    def _adjust_zoom(self, factor: float):
        new_zoom = round(self.zoom_level * factor, 2)
        if 0.5 <= new_zoom <= 2.5:
            self.zoom_level = new_zoom
            self._load_and_render_pdf()

    def _open_in_system_viewer(self):
        try:
            os.startfile(self.temp_pdf)
        except Exception as e:
            messagebox.showerror("Viewer Error", f"Unable to launch default PDF viewer: {e}")

    def _on_save_as(self):
        inv_no = str(self.invoice_data.get("invoice_no", "102630")).strip()
        client = str(self.invoice_data.get("client_name", "Invoice")).replace(" ", "_")
        init_name = f"Invoice_{inv_no}_{client}.pdf"

        target_file = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".pdf",
            filetypes=[("PDF Document", "*.pdf")],
            initialfile=init_name,
            title="Save Tax Invoice"
        )
        if target_file:
            try:
                generate_invoice_pdf(self.invoice_data, target_file)
                messagebox.showinfo("Success", f"Invoice saved successfully:\n{target_file}")
                if self.on_saved_callback:
                    self.on_saved_callback(target_file)
            except Exception as e:
                messagebox.showerror("Save Error", f"Could not save PDF: {e}")
