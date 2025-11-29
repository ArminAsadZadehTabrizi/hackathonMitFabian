from fastapi import FastAPI, Depends
from sqlmodel import Session, select
from contextlib import asynccontextmanager
from typing import Annotated

from database import init_db, get_session
from models import Receipt, LineItem
from schemas import ReceiptCreate, ReceiptRead
from audit import run_audit
from analytics import router as analytics_router

# Type alias for cleaner dependency injection
SessionDep = Annotated[Session, Depends(get_session)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for FastAPI app."""
    # Startup
    print("🚀 Starting up...")
    init_db()
    yield
    # Shutdown
    print("👋 Shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title="Small Business Auto-Bookkeeper API",
    description="Backend for automatic receipt processing and bookkeeping",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(analytics_router)


@app.get("/")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Small Business Auto-Bookkeeper API",
        "version": "1.0.0"
    }


@app.get("/api/receipts")
def get_receipts(session: SessionDep):
    """Get all receipts with their audit flags."""
    statement = select(Receipt)
    receipts = session.exec(statement).all()
    return {
        "count": len(receipts),
        "receipts": receipts
    }


@app.get("/api/audit")
def get_audit_receipts(session: SessionDep):
    """
    Get all receipts that have ANY audit flag set to True.
    
    Useful for displaying flagged receipts on the audit page.
    
    Returns:
        List of receipts with at least one audit flag set
    """
    statement = select(Receipt).where(
        (Receipt.flag_duplicate == True) |
        (Receipt.flag_suspicious == True) |
        (Receipt.flag_missing_vat == True) |
        (Receipt.flag_math_error == True)
    )
    flagged_receipts = session.exec(statement).all()
    return {
        "count": len(flagged_receipts),
        "flagged_receipts": flagged_receipts
    }


@app.post("/api/ingest", response_model=ReceiptRead)
def ingest_receipt(receipt_data: ReceiptCreate, session: SessionDep):
    """
    Ingest a new receipt with line items.
    
    Automatically runs audit checks:
    - Missing VAT detection
    - Math error detection (sum of line items vs total)
    - Suspicious items detection (alcohol/tobacco)
    - Duplicate detection
    
    Args:
        receipt_data: Receipt data with line items
        session: Database session
        
    Returns:
        Created receipt with audit flags and line items
    """
    # Create receipt object (without line items first)
    receipt = Receipt(
        vendor_name=receipt_data.vendor_name,
        date=receipt_data.date,
        total_amount=receipt_data.total_amount,
        tax_amount=receipt_data.tax_amount,
        currency=receipt_data.currency,
        category=receipt_data.category
    )
    
    # Create line items
    line_items = [
        LineItem(
            description=item.description,
            amount=item.amount
        )
        for item in receipt_data.items
    ]
    
    # Add receipt to session to get an ID (needed for duplicate check)
    session.add(receipt)
    session.flush()  # Get ID without committing
    
    # Link line items to receipt
    for item in line_items:
        item.receipt_id = receipt.id
        session.add(item)
    
    # Run audit checks
    receipt = run_audit(receipt, line_items, session)
    
    # Commit everything
    session.commit()
    session.refresh(receipt)
    
    return receipt
