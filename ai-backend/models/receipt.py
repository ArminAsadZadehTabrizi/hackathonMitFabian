"""
Pydantic Models für Quittungen
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class LineItem(BaseModel):
    """Einzelne Position auf einer Quittung"""
    description: str
    quantity: Optional[float] = 1.0
    unit_price: Optional[float] = None
    total_price: float
    category: Optional[str] = None


class Receipt(BaseModel):
    """Vollständige Quittung"""
    id: Optional[str] = None
    vendor_name: str
    vendor_address: Optional[str] = None
    date: Optional[str] = None
    total: float
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    tax_rate: Optional[float] = None
    currency: str = "EUR"
    payment_method: Optional[str] = None
    line_items: List[LineItem] = []
    category: Optional[str] = None  # Restaurant, Bürobedarf, etc.
    raw_text: Optional[str] = None  # Original OCR Text
    image_path: Optional[str] = None
    
    # Audit Flags (von Person 2 berechnet)
    has_vat: Optional[bool] = None
    is_duplicate: Optional[bool] = False
    audit_notes: Optional[List[str]] = []


class ReceiptExtractionRequest(BaseModel):
    """Request für Quittungs-Extraktion"""
    image_base64: Optional[str] = None
    image_path: Optional[str] = None


class ChatMessage(BaseModel):
    """Chat Message für RAG"""
    role: str  # "user" oder "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request für den Chatbot"""
    message: str
    history: List[ChatMessage] = []


