from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class LineItemCreate(BaseModel):
    """Schema for creating a line item."""
    description: str
    amount: float


class ReceiptCreate(BaseModel):
    """Schema for creating a receipt with line items."""
    vendor_name: str
    date: datetime
    total_amount: float
    tax_amount: float
    currency: str = "EUR"
    category: Optional[str] = None
    items: list[LineItemCreate]


class LineItemRead(BaseModel):
    """Schema for reading a line item."""
    id: int
    receipt_id: int
    description: str
    amount: float
    
    model_config = {"from_attributes": True}


class ReceiptRead(BaseModel):
    """Schema for reading a receipt with audit flags and line items."""
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
