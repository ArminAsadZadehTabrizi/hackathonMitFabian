from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select, func
from typing import Annotated

from database import get_session
from models import Receipt

# Type alias for dependency injection
SessionDep = Annotated[Session, Depends(get_session)]

# Create router for chat endpoints
router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Request schema for chat queries."""
    query: str


class ChatResponse(BaseModel):
    """Response schema for chat queries."""
    answer: str
    related_receipt_ids: list[int] = []


@router.post("/query", response_model=ChatResponse)
def chat_query(request: ChatRequest, session: SessionDep):
    """
    AI Auditor chat endpoint with keyword-based query matching.
    
    Supports queries for:
    - Total/Sum calculations
    - Audit findings (flagged receipts)
    - Vendor-specific searches
    """
    query = request.query.lower().strip()
    
    # Case 1: Total/Sum query
    if any(keyword in query for keyword in ["total", "sum", "umsatz", "kosten", "summe"]):
        # Calculate total of all receipts
        statement = select(func.sum(Receipt.total_amount))
        total = session.exec(statement).one()
        
        if total is None:
            total = 0.0
        
        return ChatResponse(
            answer=f"Der aktuelle Gesamtumsatz beträgt {total:.2f} EUR.",
            related_receipt_ids=[]
        )
    
    # Case 2: Audit/Error query
    elif any(keyword in query for keyword in ["audit", "fehler", "warnung", "suspicious", "problem", "flag"]):
        # Find all receipts with any flag set to True
        statement = select(Receipt).where(
            (Receipt.flag_duplicate == True) |
            (Receipt.flag_suspicious == True) |
            (Receipt.flag_missing_vat == True) |
            (Receipt.flag_math_error == True)
        )
        flagged_receipts = session.exec(statement).all()
        
        receipt_ids = [r.id for r in flagged_receipts]
        count = len(receipt_ids)
        
        if count == 0:
            return ChatResponse(
                answer="Ich habe keine auffälligen Belege gefunden. Alle Receipts sind in Ordnung.",
                related_receipt_ids=[]
            )
        
        return ChatResponse(
            answer=f"Ich habe {count} auffällige Belege gefunden. Diese sollten überprüft werden.",
            related_receipt_ids=receipt_ids
        )
    
    # Case 3: Vendor search
    else:
        # Try to find a vendor name in the query
        # Get all unique vendor names
        statement = select(Receipt.vendor_name).distinct()
        all_vendors = session.exec(statement).all()
        
        # Check if any vendor name appears in the query
        matching_vendor = None
        for vendor in all_vendors:
            if vendor.lower() in query:
                matching_vendor = vendor
                break
        
        if matching_vendor:
            # Get all receipts for this vendor
            statement = select(Receipt).where(Receipt.vendor_name == matching_vendor)
            vendor_receipts = session.exec(statement).all()
            
            count = len(vendor_receipts)
            total = sum(r.total_amount for r in vendor_receipts)
            receipt_ids = [r.id for r in vendor_receipts]
            
            return ChatResponse(
                answer=f"Ich habe {count} Belege von '{matching_vendor}' gefunden mit einem Gesamtwert von {total:.2f} EUR.",
                related_receipt_ids=receipt_ids
            )
        
        # Fallback: Query not understood
        return ChatResponse(
            answer="Ich habe deine Anfrage nicht verstanden. Versuche es mit 'Gesamtkosten' oder 'Zeige Fehler'.",
            related_receipt_ids=[]
        )
