"""
Pydantic Schemas für API-Validierung
Integriert von Partner 2's Backend
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class LineItemCreate(BaseModel):
    """Schema für das Erstellen eines Line Items."""
    description: str
    amount: float


class ReceiptCreateDB(BaseModel):
    """Schema für das Erstellen einer Quittung mit Line Items."""
    vendor_name: str
    date: datetime
    total_amount: float
    tax_amount: float
    currency: str = "EUR"
    category: Optional[str] = None
    items: list[LineItemCreate]


class LineItemRead(BaseModel):
    """Schema für das Lesen eines Line Items."""
    id: int
    receipt_id: int
    description: str
    amount: float
    
    model_config = {"from_attributes": True}


class ReceiptReadDB(BaseModel):
    """Schema für das Lesen einer Quittung mit Audit-Flags und Line Items."""
    id: int
    vendor_name: str
    date: datetime
    total_amount: float
    tax_amount: float
    currency: str
    category: Optional[str]
    
    # Audit flags
    flag_duplicate: bool
    flag_suspicious: bool
    flag_missing_vat: bool
    flag_math_error: bool
    
    # Line items
    line_items: list[LineItemRead]
    
    model_config = {"from_attributes": True}


