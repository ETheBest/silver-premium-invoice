"""
PDF Engine
Generates official Tax Invoices matching the exact geometry, typography,
and layout of the Silver Premium reference invoice.
Built with ReportLab.
"""
import os
import sys
from typing import Dict, Any, List
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from core.num_to_words_helper import amount_to_aed_words


def get_asset_path(filename: str) -> str:
    """Resolves asset paths in both development and PyInstaller bundled environments."""
    if getattr(sys, 'frozen', False):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Check assets directory
    path = os.path.join(base_dir, "assets", filename)
    if os.path.exists(path):
        return path
    
    # Fallback to direct path
    alt = os.path.join(base_dir, filename)
    if os.path.exists(alt):
        return alt
    
    return path


class InvoicePDFGenerator:
    # Page Dimensions
    PAGE_WIDTH, PAGE_HEIGHT = A4  # 595.28 x 841.89 pt

    # Grid & Box Geometry (Matching reference invoice exact points)
    BOX_LEFT = 72.02
    BOX_RIGHT = 523.39
    BOX_WIDTH = BOX_RIGHT - BOX_LEFT  # 451.37 pt

    # Top & Bottom of main outer box
    Y_BOX_TOP = 667.84       # Top border of outer box
    Y_DIV_TAX_INV = 636.0    # Line under TAX INVOICE
    Y_DIV_METADATA = 574.0   # Line under Customer/Invoice metadata
    Y_DIV_TBL_HDR = 558.0    # Line under Table Header
    Y_DIV_ITEMS_END = 401.13 # Line under Items Table / above Bank Details
    Y_DIV_BANK_END = 312.07  # Line under Bank Details & Totals
    Y_DIV_WORDS_END = 298.87 # Line under Amount in Words banner
    Y_BOX_BOTTOM = 180.0     # Bottom border with ample room for conditions & stamp
    BOX_HEIGHT = Y_BOX_TOP - Y_BOX_BOTTOM  # 487.84 pt

    # Vertical Column Dividers in Items Table
    X_COL_S = 72.02
    X_COL_DESC = 100.61      # S# width: 28.59 pt
    X_COL_QTY = 277.78       # Description width: 177.17 pt
    X_COL_AMT = 334.68       # Quantity width: 56.90 pt
    X_COL_VAT = 397.10       # Amount width: 62.42 pt
    X_COL_TOTAL = 446.33     # VAT width: 49.23 pt
    X_COL_END = 523.39       # Total Amount width: 77.06 pt

    # Vertical Dividers in Metadata & Bank/Totals Sections
    X_DIV_METADATA = 334.44  # Splits Customer (left) and Invoice Info (right)
    X_DIV_BANK = 334.44      # Splits Bank Details (left) and Totals (right)
    X_DIV_TOTALS_VAL = 446.09 # Splits Totals labels from amounts

    # Colors
    FILL_GRAY = colors.Color(0.949, 0.949, 0.949)  # #F2F2F2
    BORDER_COLOR = colors.black
    LINE_WIDTH = 0.48

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.letterhead_path = get_asset_path("letterhead_bg.jpg")

    def generate(self, output_path: str):
        c = canvas.Canvas(output_path, pagesize=A4)
        c.setTitle(f"Tax Invoice - {self.data.get('invoice_no', '102630')}")

        # 1. Background Letterhead
        if os.path.exists(self.letterhead_path):
            c.drawImage(
                self.letterhead_path,
                0, 0,
                width=self.PAGE_WIDTH,
                height=self.PAGE_HEIGHT,
                preserveAspectRatio=False,
                mask=None
            )

        # 2. Company TRN above main table
        company = self.data.get("company", {})
        issuer_trn = company.get("trn", "104171277700003")
        c.setFont("Times-Bold", 10.1)
        c.setFillColor(colors.black)
        trn_text = f"TRN {issuer_trn}"
        c.drawCentredString(self.PAGE_WIDTH / 2.0, 694.5, trn_text)

        # 3. Main Outer Table Frame & Section Backgrounds
        self._draw_structure(c)

        # 4. Content Sections
        self._draw_tax_invoice_header(c)
        self._draw_metadata_section(c)
        self._draw_table_headers(c)
        self._draw_line_items(c)
        self._draw_bank_and_totals(c)
        self._draw_currency_words_banner(c)
        self._draw_terms_and_conditions(c)

        # 5. Check if custom footer needs to be rendered over default
        self._draw_footer_if_custom(c)

        c.showPage()
        c.save()

    def _draw_structure(self, c: canvas.Canvas):
        """Draws background fills and all grid lines."""
        # A. Fill Gray Banners
        # 1. TAX INVOICE banner fill
        c.setFillColor(self.FILL_GRAY)
        c.rect(
            self.BOX_LEFT, self.Y_DIV_TAX_INV,
            self.BOX_WIDTH, self.Y_BOX_TOP - self.Y_DIV_TAX_INV,
            fill=1, stroke=0
        )

        # 2. Table Column Headers fill
        c.rect(
            self.BOX_LEFT, self.Y_DIV_TBL_HDR,
            self.BOX_WIDTH, self.Y_DIV_METADATA - self.Y_DIV_TBL_HDR,
            fill=1, stroke=0
        )

        # 3. Currency in Words banner fill
        c.rect(
            self.BOX_LEFT, self.Y_DIV_WORDS_END,
            self.BOX_WIDTH, self.Y_DIV_BANK_END - self.Y_DIV_WORDS_END,
            fill=1, stroke=0
        )

        # B. Outer Box Border
        c.setStrokeColor(self.BORDER_COLOR)
        c.setLineWidth(self.LINE_WIDTH)
        c.rect(
            self.BOX_LEFT, self.Y_BOX_BOTTOM,
            self.BOX_WIDTH, self.BOX_HEIGHT,
            fill=0, stroke=1
        )

        # C. Horizontal Grid Lines
        for y in [
            self.Y_DIV_TAX_INV,
            self.Y_DIV_METADATA,
            self.Y_DIV_TBL_HDR,
            self.Y_DIV_ITEMS_END,
            self.Y_DIV_BANK_END,
            self.Y_DIV_WORDS_END
        ]:
            c.line(self.BOX_LEFT, y, self.BOX_RIGHT, y)

        # D. Vertical Dividers
        # Metadata section vertical divider
        c.line(self.X_DIV_METADATA, self.Y_DIV_METADATA, self.X_DIV_METADATA, self.Y_DIV_TAX_INV)

        # Items Table vertical dividers (from Table Header top down to Items End)
        for x in [self.X_COL_DESC, self.X_COL_QTY, self.X_COL_AMT, self.X_COL_VAT, self.X_COL_TOTAL]:
            c.line(x, self.Y_DIV_ITEMS_END, x, self.Y_DIV_METADATA)

        # Bank Details & Totals vertical dividers
        c.line(self.X_DIV_BANK, self.Y_DIV_BANK_END, self.X_DIV_BANK, self.Y_DIV_ITEMS_END)
        c.line(self.X_DIV_TOTALS_VAL, self.Y_DIV_BANK_END, self.X_DIV_TOTALS_VAL, self.Y_DIV_ITEMS_END)

    def _draw_tax_invoice_header(self, c: canvas.Canvas):
        """Draws 'TAX INVOICE' centered in top section."""
        c.setFont("Times-Bold", 10.5)
        c.setFillColor(colors.black)
        c.drawCentredString(self.PAGE_WIDTH / 2.0, 648.0, "TAX INVOICE")

    def _draw_metadata_section(self, c: canvas.Canvas):
        """Draws customer details on left and invoice info on right."""
        # Left Side: Customer Entity Info
        client = self.data.get("customer", {})
        company_name = client.get("company_name", "")
        address = client.get("address", "")
        trn = client.get("trn", "")

        c.setFillColor(colors.black)
        # Line 1: Company Name (Times-Bold 10.5pt)
        c.setFont("Times-Bold", 10.5)
        c.drawString(77.8, 619.0, company_name[:48])

        # Line 2: Address (Times-Roman 10.0pt)
        c.setFont("Times-Roman", 10.0)
        c.drawString(77.8, 605.0, address[:52])

        # Line 3: Customer TRN (Times-Bold 10.0pt, clean 17pt margin above divider line)
        c.setFont("Times-Bold", 10.0)
        trn_str = f"Customer TRN: {trn}" if trn else ""
        c.drawString(77.8, 591.0, trn_str)

        # Right Side: Invoice #, Date, Reference
        inv_no = str(self.data.get("invoice_no", ""))
        inv_date = str(self.data.get("date", ""))
        client_ref = str(self.data.get("client_name", "")).strip()

        # Line 1: Invoice # : 102630
        c.setFont("Times-Bold", 10.0)
        c.drawString(339.7, 619.0, "Invoice #")
        c.drawString(404.0, 619.0, ":")
        c.drawString(414.0, 619.0, inv_no)

        # Line 2: Invoice Date : 04th Sep 2026
        c.drawString(339.7, 605.0, "Invoice Date")
        c.drawString(404.0, 605.0, ":")
        c.drawString(414.0, 605.0, inv_date)

        # Line 3: Reference : <Reference Name> (Aligned with colons)
        if client_ref:
            c.drawString(339.7, 591.0, "Reference")
            c.drawString(404.0, 591.0, ":")
            font_size = 10.0
            max_w = self.BOX_RIGHT - 418.0
            cur_w = c.stringWidth(client_ref, "Times-Bold", font_size)
            if cur_w > max_w:
                font_size = max(7.5, font_size * (max_w / cur_w))
            c.setFont("Times-Bold", font_size)
            c.drawString(414.0, 591.0, client_ref)

    def _draw_table_headers(self, c: canvas.Canvas):
        """Draws column titles in the table header row."""
        c.setFont("Times-Bold", 10.0)
        c.setFillColor(colors.black)
        y_text = 563.0

        # S# (Centered in S# col)
        c.drawCentredString((self.X_COL_S + self.X_COL_DESC) / 2.0, y_text, "S#")

        # Description (Left aligned with padding)
        c.drawString(self.X_COL_DESC + 5.0, y_text, "Description")

        # Quantity (Centered)
        c.drawCentredString((self.X_COL_QTY + self.X_COL_AMT) / 2.0, y_text, "Quantity")

        # Amount (Centered in amount col)
        c.drawCentredString((self.X_COL_AMT + self.X_COL_VAT) / 2.0, y_text, "Amount")

        # VAT (Centered)
        c.drawCentredString((self.X_COL_VAT + self.X_COL_TOTAL) / 2.0, y_text, "VAT")

        # Total Amount (Centered)
        c.drawCentredString((self.X_COL_TOTAL + self.X_COL_END) / 2.0, y_text, "Total Amount")

    def _draw_line_items(self, c: canvas.Canvas):
        """Draws each row of line items."""
        items = self.data.get("items", [])
        c.setFont("Times-Roman", 10.5)
        c.setFillColor(colors.black)

        row_y = 544.0
        line_height = 12.7

        for idx, item in enumerate(items, start=1):
            if row_y < self.Y_DIV_ITEMS_END + 5:
                # Stop if approaching bottom divider
                break

            s_no = f"{idx}."
            desc = str(item.get("description", ""))
            qty = str(item.get("quantity", 1))
            unit_amt = float(item.get("unit_amount", 0.0))
            vat_amt = float(item.get("vat_amount", 0.0))
            line_total = float(item.get("line_total", unit_amt + vat_amt))

            # S#
            c.drawCentredString((self.X_COL_S + self.X_COL_DESC) / 2.0, row_y, s_no)

            # Description (truncated if too long)
            c.drawString(self.X_COL_DESC + 5.0, row_y, desc[:32])

            # Quantity
            c.drawCentredString((self.X_COL_QTY + self.X_COL_AMT) / 2.0, row_y, qty)

            # Unit Amount (Right-aligned with margin)
            c.drawRightString(self.X_COL_VAT - 9.0, row_y, f"{unit_amt:,.2f}")

            # VAT Amount (Right-aligned with margin)
            c.drawRightString(self.X_COL_TOTAL - 9.0, row_y, f"{vat_amt:,.2f}")

            # Line Total Amount (Right-aligned with margin)
            c.drawRightString(self.X_COL_END - 14.0, row_y, f"{line_total:,.2f}")

            row_y -= line_height

    def _draw_bank_and_totals(self, c: canvas.Canvas):
        """Draws Bank Details on left and Financial Totals on right."""
        bank = self.data.get("bank", {})
        bank_name = bank.get("bank_name", "WIO BUSINESS")
        account_no = bank.get("account_no", "9895248605")
        beneficiary = bank.get("beneficiary_name", "Silver Premium Documents Clearing Co LLC")
        iban = bank.get("iban", "AE620860000009895248605")

        # Left Side: Bank Details
        # Title "Bank Details" bold
        c.setFont("Times-Bold", 11.0)
        c.setFillColor(colors.black)
        c.drawString(172.1, 388.5, "Bank Details")

        # Labels & Values (Times-Roman 10.1 pt)
        c.setFont("Times-Roman", 10.1)

        # Row 1: Bank Name
        c.drawString(77.8, 376.5, "Bank Name")
        c.drawString(172.1, 376.5, bank_name)

        # Row 2: Account No
        c.drawString(77.8, 365.2, "Account No")
        c.drawString(172.1, 365.2, account_no)

        # Row 3 & 4: Beneficiary Name (split if long)
        c.drawString(77.8, 353.7, "Beneficiary Name")
        if len(beneficiary) > 34:
            # Split into 2 lines
            c.drawString(172.1, 353.7, beneficiary[:34])
            c.drawString(172.1, 342.2, beneficiary[34:].strip())
        else:
            c.drawString(172.1, 353.7, beneficiary)

        # Row 5: IBAN No
        c.setFont("Times-Roman", 11.0)
        c.drawString(77.8, 330.5, "IBAN No")
        c.setFont("Times-Roman", 10.1)
        c.drawString(172.1, 330.5, iban)

        # Right Side: Financial Totals
        subtotal = float(self.data.get("subtotal", 0.0))
        vat_total = float(self.data.get("vat_total", 0.0))
        grand_total = float(self.data.get("grand_total", subtotal + vat_total))

        # Amount (Subtotal)
        c.setFont("Times-Roman", 11.0)
        c.drawRightString(self.X_DIV_TOTALS_VAL - 8.0, 376.5, "Amount")
        c.setFont("Times-Bold", 11.0)
        c.drawRightString(self.BOX_RIGHT - 14.0, 376.5, f"{subtotal:,.2f}")

        # Vat 5%
        c.setFont("Times-Roman", 11.0)
        c.drawRightString(self.X_DIV_TOTALS_VAL - 8.0, 351.0, "Vat 5%")
        c.setFont("Times-Bold", 11.0)
        c.drawRightString(self.BOX_RIGHT - 14.0, 351.0, f"{vat_total:,.2f}")

        # Grand Total
        c.setFont("Times-Roman", 11.0)
        c.drawRightString(self.X_DIV_TOTALS_VAL - 8.0, 325.8, "Grand Total")
        c.setFont("Times-Bold", 11.0)
        c.drawRightString(self.BOX_RIGHT - 14.0, 325.8, f"{grand_total:,.2f}")

    def _draw_currency_words_banner(self, c: canvas.Canvas):
        """Draws highlighted currency in words banner, automatically scaling font size so text never overlaps borders."""
        grand_total = float(self.data.get("grand_total", 0.0))
        words_text = self.data.get("amount_in_words") or amount_to_aed_words(grand_total)

        font_name = "Times-Bold"
        font_size = 11.0
        max_allowed_width = self.BOX_WIDTH - 24.0  # 427.37 pt (safe 12pt margin from both left and right borders)

        current_width = c.stringWidth(words_text, font_name, font_size)
        if current_width > max_allowed_width:
            font_size = max(6.5, font_size * (max_allowed_width / current_width))

        c.setFont(font_name, font_size)
        c.setFillColor(colors.black)
        y_text = (self.Y_DIV_BANK_END + self.Y_DIV_WORDS_END) / 2.0 - (font_size * 0.32)
        c.drawCentredString(self.PAGE_WIDTH / 2.0, y_text, words_text)

    def _draw_terms_and_conditions(self, c: canvas.Canvas):
        """Draws Terms & Conditions section."""
        terms = self.data.get("terms", [
            "All govt. charges are estimates, may change at any time.",
            "Timely payment is required for us to proceed with your work."
        ])

        c.setFont("Times-Bold", 10.5)
        c.setFillColor(colors.black)
        c.drawString(77.8, 283.0, "Terms & Conditions")

        c.setFont("Times-Roman", 9.2)
        y_item = 268.0
        for idx, term in enumerate(terms, start=1):
            c.drawString(95.8, y_item, f"{idx}.")
            c.drawString(111.0, y_item, term[:95])
            y_item -= 14.0

    def _draw_footer_if_custom(self, c: canvas.Canvas):
        """
        If the company details or footer line was edited by user,
        cleanly overlay the custom footer text.
        """
        company = self.data.get("company", {})
        custom_footer = company.get("footer_text", "")
        default_footer = "OFFICE 960, TAMANI ARTS, BAY SQUARE, DUBAI - U.A.E. | Tel: 04 433 8970"

        if custom_footer and custom_footer.strip() != default_footer.strip():
            # Clear default footer text with white rect
            c.setFillColor(colors.white)
            c.rect(100, 15, 395, 25, fill=1, stroke=0)
            # Render new custom footer
            c.setFont("Helvetica-Bold", 8.5)
            c.setFillColor(colors.HexColor("#777777"))
            c.drawCentredString(self.PAGE_WIDTH / 2.0, 22.0, custom_footer.strip())


def generate_invoice_pdf(data: Dict[str, Any], output_path: str) -> str:
    """Convenience helper to generate invoice PDF."""
    generator = InvoicePDFGenerator(data)
    generator.generate(output_path)
    return output_path
