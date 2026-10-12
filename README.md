# Silver Premium Tax Invoice Generator

A standalone, single-file desktop application for Windows. Everything is self-contained inside **`Silver Premium Invoice Generator.exe`** with zero external dependencies, no Python required, and no other files needed to run.

---

## 🚀 Instant Launch

Simply double-click:
```
Silver Premium Invoice Generator.exe
```
*(Available directly on your Desktop and inside the `INVOICE APP` folder).*

---

## 🌟 Key Features

1. **Self-Contained Single `.EXE`**:
   - All letterhead graphics, official logos, fonts, ReportLab PDF generators, and dependencies are packed inside this single executable.
   - You can copy this `.exe` anywhere (USB flash drive, Desktop, another computer) and it works right out of the box.

2. **Automated `Invoices/` Folder Archiving**:
   - Every invoice you create is automatically saved with clean naming:
     ```
     Invoices/102630 - Rochelle Visa Renewal.pdf
     ```
   - Automatically opens the PDF immediately for review or printing.
   - A single click on **"📂 Invoices"** opens your saved folder anytime.

3. **Automatic Sequential (+1) Numbering**:
   - Automatically tracks your previous invoices and always increments by **+1** (e.g. `102630` -> `102631` -> `102632`).

4. **VAT & Tax History Analytics**:
   - Filter invoice history by **Company / Customer Profile**, **Year**, **Month**, or search terms.
   - **Real-Time KPI Dashboard**: Live totals for Invoices Count, Taxable Subtotal, **Total VAT 5% Paid (AED)**, and Grand Total.
   - **Company VAT Breakdown Tab**: Aggregates and displays exact VAT taxes paid for each company profile.
   - Double-click any company to instantly filter their invoices.
   - 1-Click **"📊 Export VAT Report"** and **"📄 Open Full History (CSV)"** for easy Microsoft Excel tax filing and accounting.

5. **Pixel-Perfect PDF**:
   - Replicates the official Silver Premium Tax Invoice layout, typography, and borders.
   - Automatically scales text so long amounts in words never overlap borders.

6. **Responsive Screen Scaling**:
   - Pinned top and bottom toolbars that stay visible even on smaller laptop displays (e.g. 768p / 125% scaling).
   - Mousewheel-enabled scrolling for comfortable viewing.

7. **Customer Profiles & 1-Click Dropdown Selection**:
   - Save and organize repeat customer accounts (Company Name, Address, TRN, Contact Reference, Phone, Email, Notes).
   - **Instant Dropdown**: Choose any customer from the dropdown to automatically fetch and fill their company name, address, TRN, and client reference into the invoice.
   - **Quick Save**: Click `💾 Save` on the customer form to save newly entered customer details into the profile database instantly.
   - **Profile Manager (`👥 Customers`)**: Search, view, edit, delete profiles, or auto-import customers from past invoice records with 1 click.
