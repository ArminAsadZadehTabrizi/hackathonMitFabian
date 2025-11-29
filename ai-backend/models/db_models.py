"""
SQLModel Datenbankmodelle für Quittungen
Integriert von Partner 2's Backend
"""
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional


class ReceiptDB(SQLModel, table=True):
    """Receipt model mit Audit-Flags für die Buchhaltung."""
    
    __tablename__ = "receipts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_name: str = Field(index=True)
    date: datetime
    total_amount: float
    tax_amount: float
    currency: str = Field(default="EUR", max_length=3)
    category: Optional[str] = Field(default=None, index=True)
    
    # Audit flags
    flag_duplicate: bool = Field(default=False)
    flag_suspicious: bool = Field(default=False)  # z.B. Alkohol/Tabak
    flag_missing_vat: bool = Field(default=False)
    flag_math_error: bool = Field(default=False)
    
    # Relationship to line items
    line_items: list["LineItemDB"] = Relationship(back_populates="receipt")


class LineItemDB(SQLModel, table=True):
    """Line item zu einer Quittung."""
    
    __tablename__ = "line_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    receipt_id: int = Field(foreign_key="receipts.id", index=True)
    description: str
    amount: float
    
    # Relationship back to receipt
    receipt: Optional[ReceiptDB] = Relationship(back_populates="line_items")


