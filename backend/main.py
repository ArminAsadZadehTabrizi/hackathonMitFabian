from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from contextlib import asynccontextmanager
from typing import Annotated
from datetime import datetime

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

# Add CORS middleware to allow frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8082",  # Frontend default port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:8082"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    """
    Get all receipts with their audit flags.
    Returns data in the format expected by the frontend.
    """
    statement = select(Receipt)
    receipts = session.exec(statement).all()
    
    # Transform receipts to frontend format
    formatted_receipts = []
    for receipt in receipts:
        # Get line items for this receipt
        line_items_stmt = select(LineItem).where(LineItem.receipt_id == receipt.id)
        line_items = session.exec(line_items_stmt).all()
        
        # Transform line items to frontend format
        formatted_line_items = [
            {
                "id": str(item.id),
                "description": item.description,
                "quantity": 1,
                "unitPrice": item.amount,
                "total": item.amount,
                "vat": 0
            }
            for item in line_items
        ]
        
        # Calculate subtotal (total - tax)
        subtotal = receipt.total_amount - (receipt.tax_amount or 0)
        
        # Transform receipt to frontend format
        formatted_receipt = {
            "id": str(receipt.id),
            "receiptNumber": f"RCP-{receipt.id:06d}",
            "vendor": receipt.vendor_name,
            "vendorVAT": None,
            "date": receipt.date.isoformat() if isinstance(receipt.date, datetime) else str(receipt.date),
            "total": float(receipt.total_amount),
            "subtotal": float(subtotal),
            "vat": float(receipt.tax_amount) if receipt.tax_amount else None,
            "vatRate": None,
            "paymentMethod": "Unknown",
            "category": receipt.category or "Uncategorized",
            "currency": receipt.currency,
            "lineItems": formatted_line_items,
            "imageUrl": None,
            "status": "flagged" if (receipt.flag_duplicate or receipt.flag_suspicious or 
                                   receipt.flag_missing_vat or receipt.flag_math_error) else "verified",
            "tags": [],
            "notes": None,
            "createdAt": receipt.date.isoformat() if isinstance(receipt.date, datetime) else str(receipt.date),
            "updatedAt": receipt.date.isoformat() if isinstance(receipt.date, datetime) else str(receipt.date),
            "auditFlags": {
                "isDuplicate": receipt.flag_duplicate,
                "hasTotalMismatch": receipt.flag_math_error,
                "missingVAT": receipt.flag_missing_vat,
                "suspiciousCategory": "Alcohol/Tobacco" if receipt.flag_suspicious else None
            }
        }
        formatted_receipts.append(formatted_receipt)
    
    return {
        "count": len(formatted_receipts),
        "receipts": formatted_receipts
    }


@app.get("/api/audit")
def get_audit_receipts(session: SessionDep):
    """
    Get all receipts that have ANY audit flag set to True.
    
    Useful for displaying flagged receipts on the audit page.
    Returns data in the format expected by the frontend.
    """
    statement = select(Receipt).where(
        (Receipt.flag_duplicate == True) |
        (Receipt.flag_suspicious == True) |
        (Receipt.flag_missing_vat == True) |
        (Receipt.flag_math_error == True)
    )
    flagged_receipts = session.exec(statement).all()
    
    # Transform to frontend format
    duplicates = []
    mismatches = []
    missing_vat = []
    suspicious = []
    
    for receipt in flagged_receipts:
        audit_finding = {
            "receiptId": str(receipt.id),
            "receiptNumber": f"RCP-{receipt.id:06d}",
            "vendor": receipt.vendor_name,
            "date": receipt.date.isoformat() if isinstance(receipt.date, datetime) else str(receipt.date),
            "total": float(receipt.total_amount),
        }
        
        if receipt.flag_duplicate:
            audit_finding["reason"] = "Duplicate receipt detected"
            duplicates.append(audit_finding)
        
        if receipt.flag_math_error:
            # Get line items to calculate expected total
            line_items_stmt = select(LineItem).where(LineItem.receipt_id == receipt.id)
            line_items = session.exec(line_items_stmt).all()
            expected_total = sum(item.amount for item in line_items)
            audit_finding["issue"] = "Total mismatch"
            audit_finding["expectedTotal"] = float(expected_total)
            audit_finding["actualTotal"] = float(receipt.total_amount)
            audit_finding["difference"] = float(abs(expected_total - receipt.total_amount))
            mismatches.append(audit_finding)
        
        if receipt.flag_missing_vat:
            audit_finding["issue"] = "Missing VAT"
            missing_vat.append(audit_finding)
        
        if receipt.flag_suspicious:
            audit_finding["category"] = "Alcohol/Tobacco"
            audit_finding["issue"] = "Suspicious items detected"
            suspicious.append(audit_finding)
    
    return {
        "duplicates": duplicates,
        "mismatches": mismatches,
        "missingVAT": missing_vat,
        "suspicious": suspicious,
        "summary": {
            "totalDuplicates": len(duplicates),
            "totalMismatches": len(mismatches),
            "totalMissingVAT": len(missing_vat),
            "totalSuspicious": len(suspicious)
        }
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
