"""
Item Row Widget
Represents a single editable line item row in the invoice table.
Automatically calculates VAT (5% if Yes, 0 if No) and Line Total.
Supports reordering and deletion.
"""
import customtkinter as ctk
from typing import Callable, Optional, Dict, Any


class ItemRow(ctk.CTkFrame):
    def __init__(
        self,
        master,
        index: int,
        description: str = "",
        quantity: str = "1",
        unit_amount: str = "0.00",
        vat_toggle: str = "No",
        on_change_callback: Optional[Callable[[], None]] = None,
        on_move_up: Optional[Callable[["ItemRow"], None]] = None,
        on_move_down: Optional[Callable[["ItemRow"], None]] = None,
        on_delete: Optional[Callable[["ItemRow"], None]] = None,
        **kwargs
    ):
        super().__init__(master, corner_radius=6, **kwargs)
        self.index = index
        self.on_change_callback = on_change_callback
        self.on_move_up = on_move_up
        self.on_move_down = on_move_down
        self.on_delete = on_delete

        # Grid configuration
        # Columns: [0: S# (30)], [1: Desc (220)], [2: Qty (60)], [3: Unit Amt (90)], [4: VAT Toggle (70)], [5: VAT Amt (75)], [6: Total (85)], [7: Actions (80)]
        self.grid_columnconfigure(0, weight=0, minsize=35)
        self.grid_columnconfigure(1, weight=3, minsize=180)
        self.grid_columnconfigure(2, weight=0, minsize=65)
        self.grid_columnconfigure(3, weight=1, minsize=95)
        self.grid_columnconfigure(4, weight=0, minsize=75)
        self.grid_columnconfigure(5, weight=1, minsize=80)
        self.grid_columnconfigure(6, weight=1, minsize=90)
        self.grid_columnconfigure(7, weight=0, minsize=85)

        # 0. S# Label
        self.lbl_sno = ctk.CTkLabel(
            self,
            text=f"{self.index}.",
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            width=30
        )
        self.lbl_sno.grid(row=0, column=0, padx=(6, 2), pady=6, sticky="w")

        # 1. Description Entry
        self.entry_desc = ctk.CTkEntry(
            self,
            placeholder_text="Item description...",
            font=ctk.CTkFont(family="Arial", size=12),
            height=30
        )
        self.entry_desc.insert(0, description)
        self.entry_desc.grid(row=0, column=1, padx=4, pady=6, sticky="ew")
        self.entry_desc.bind("<KeyRelease>", lambda e: self._notify_change())

        # 2. Quantity Entry
        self.entry_qty = ctk.CTkEntry(
            self,
            placeholder_text="1",
            font=ctk.CTkFont(family="Arial", size=12),
            width=60,
            height=30,
            justify="center"
        )
        self.entry_qty.insert(0, str(quantity))
        self.entry_qty.grid(row=0, column=2, padx=4, pady=6)
        self.entry_qty.bind("<KeyRelease>", lambda e: self.recalculate())

        # 3. Unit Amount Entry (AED)
        self.entry_unit_amt = ctk.CTkEntry(
            self,
            placeholder_text="0.00",
            font=ctk.CTkFont(family="Arial", size=12),
            width=90,
            height=30,
            justify="right"
        )
        self.entry_unit_amt.insert(0, str(unit_amount))
        self.entry_unit_amt.grid(row=0, column=3, padx=4, pady=6, sticky="ew")
        self.entry_unit_amt.bind("<KeyRelease>", lambda e: self.recalculate())

        # 4. VAT Toggle ("Yes" / "No")
        self.var_vat = ctk.StringVar(value="Yes" if vat_toggle.lower() in ["yes", "true", "1"] else "No")
        self.seg_vat = ctk.CTkSegmentedButton(
            self,
            values=["No", "Yes"],
            variable=self.var_vat,
            command=lambda v: self.recalculate(),
            width=70,
            height=28,
            font=ctk.CTkFont(family="Arial", size=11, weight="bold")
        )
        self.seg_vat.grid(row=0, column=4, padx=4, pady=6)

        # 5. VAT Amount Label
        self.lbl_vat_amt = ctk.CTkLabel(
            self,
            text="0.00",
            font=ctk.CTkFont(family="Arial", size=12),
            width=75,
            anchor="e"
        )
        self.lbl_vat_amt.grid(row=0, column=5, padx=4, pady=6, sticky="e")

        # 6. Line Total Label
        self.lbl_line_total = ctk.CTkLabel(
            self,
            text="0.00",
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            width=85,
            anchor="e"
        )
        self.lbl_line_total.grid(row=0, column=6, padx=4, pady=6, sticky="e")

        # 7. Action Buttons (Up, Down, Delete)
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=0, column=7, padx=(4, 6), pady=6)

        self.btn_up = ctk.CTkButton(
            action_frame,
            text="▲",
            width=22,
            height=26,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#374151",
            hover_color="#4B5563",
            command=lambda: self.on_move_up(self) if self.on_move_up else None
        )
        self.btn_up.pack(side="left", padx=1)

        self.btn_down = ctk.CTkButton(
            action_frame,
            text="▼",
            width=22,
            height=26,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#374151",
            hover_color="#4B5563",
            command=lambda: self.on_move_down(self) if self.on_move_down else None
        )
        self.btn_down.pack(side="left", padx=1)

        self.btn_del = ctk.CTkButton(
            action_frame,
            text="✕",
            width=24,
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#EF4444",
            hover_color="#DC2626",
            command=lambda: self.on_delete(self) if self.on_delete else None
        )
        self.btn_del.pack(side="left", padx=(2, 0))

        # Initial calculation
        self.recalculate(notify=False)

    def set_index(self, new_index: int):
        self.index = new_index
        self.lbl_sno.configure(text=f"{self.index}.")

    def recalculate(self, notify: bool = True):
        """Computes VAT and Line Total based on quantity and unit amount."""
        qty = self.get_quantity()
        unit_amt = self.get_unit_amount()
        vat_applicable = self.var_vat.get() == "Yes"

        subtotal = qty * unit_amt
        vat_amt = round(subtotal * 0.05, 2) if vat_applicable else 0.00
        line_total = round(subtotal + vat_amt, 2)

        self.lbl_vat_amt.configure(text=f"{vat_amt:,.2f}")
        self.lbl_line_total.configure(text=f"{line_total:,.2f}")

        if notify:
            self._notify_change()

    def _notify_change(self):
        if self.on_change_callback:
            self.on_change_callback()

    def get_description(self) -> str:
        return self.entry_desc.get().strip()

    def get_quantity(self) -> float:
        val = self.entry_qty.get().strip()
        try:
            return float(val) if val else 0.0
        except ValueError:
            return 0.0

    def get_unit_amount(self) -> float:
        val = self.entry_unit_amt.get().strip().replace(",", "")
        try:
            return float(val) if val else 0.0
        except ValueError:
            return 0.0

    def is_vat_applicable(self) -> bool:
        return self.var_vat.get() == "Yes"

    def get_vat_amount(self) -> float:
        if self.is_vat_applicable():
            return round(self.get_quantity() * self.get_unit_amount() * 0.05, 2)
        return 0.00

    def get_line_total(self) -> float:
        sub = self.get_quantity() * self.get_unit_amount()
        return round(sub + self.get_vat_amount(), 2)

    def to_dict(self) -> Dict[str, Any]:
        """Returns structured dictionary for PDF engine."""
        return {
            "description": self.get_description(),
            "quantity": int(self.get_quantity()) if self.get_quantity().is_integer() else self.get_quantity(),
            "unit_amount": self.get_unit_amount(),
            "vat_applicable": self.is_vat_applicable(),
            "vat_amount": self.get_vat_amount(),
            "line_total": self.get_line_total()
        }
