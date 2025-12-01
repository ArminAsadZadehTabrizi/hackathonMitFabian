"""
🧠 AI Backend für Quittungs-Analyse
FastAPI Server mit Ollama LLM + ChromaDB RAG + SQLite DB

Endpoints:
    - POST /api/extract     - Extrahiert Daten aus Quittungsbild
    - POST /api/chat        - Chatbot mit RAG
    - GET  /api/search      - Semantische Suche in Quittungen
    - GET  /api/health      - Health Check
    - POST /api/ingest      - Daten in RAG laden
    - GET  /api/receipts    - Alle Quittungen aus DB
    - GET  /api/audit       - Geflaggte Quittungen
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Annotated
from sqlmodel import Session, select, func
from datetime import datetime
from pathlib import Path
import base64
import uvicorn

from config import API_HOST, API_PORT
from models.receipt import Receipt, ReceiptExtractionRequest, ChatRequest
from models.db_models import ReceiptDB, LineItemDB
from models.db_schemas import ReceiptCreateDB, ReceiptReadDB
from services.ollama_service import extract_receipt_from_image, generate_chat_response, check_ollama_status
from services.rag_service import init_rag, add_receipt_to_rag, search_receipts, get_context_for_query, get_collection_stats
from services.analytics_service import calculate_precise_answer
from services.formatters import format_receipt_for_api, format_audit_finding, format_chat_receipt
from services.database import init_db, get_session
from services.audit import run_audit
from smart_query_handler import parse_query_and_calculate

# Type alias for dependency injection
SessionDep = Annotated[Session, Depends(get_session)]

# Upload directory for images
UPLOAD_DIR = Path("./data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# APP SETUP
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & Shutdown Events."""
    print("🚀 AI Backend startet...")
    init_db()
    init_rag()
    print("✅ Alle Systeme bereit!")
    yield
    print("👋 AI Backend wird beendet...")


app = FastAPI(
    title="Finanz AI Backend",
    description="AI-powered Receipt Analysis with Local LLM + Database + Audit System",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/api/images", StaticFiles(directory=str(UPLOAD_DIR)), name="images")


# =============================================================================
# HEALTH & STATUS
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "🧠 Finanz AI Backend läuft!",
        "docs": "/docs",
        "endpoints": [
            "POST /api/extract - Quittung analysieren",
            "POST /api/chat/query - Mit Daten chatten",
            "GET /api/receipts - Alle Quittungen",
            "GET /api/audit - Audit-Findings"
        ]
    }


@app.get("/api/health")
async def health_check():
    """Health check - returns status of all systems."""
    return {
        "status": "healthy",
        "ollama": check_ollama_status(),
        "rag": get_collection_stats()
    }


@app.get("/api/ollama/verify")
def verify_ollama_usage():
    """Verify that Ollama is being used for LLM operations."""
    from services.ollama_service import OLLAMA_HOST, OLLAMA_CHAT_MODEL, OLLAMA_MODEL
    import requests
    
    test_success, test_error = False, None
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": OLLAMA_CHAT_MODEL, "prompt": "Test", "stream": False},
            timeout=5
        )
        test_success = response.status_code == 200
    except Exception as e:
        test_error = str(e)
    
    return {
        "ollama_configured": True,
        "ollama_host": OLLAMA_HOST,
        "chat_model": OLLAMA_CHAT_MODEL,
        "vision_model": OLLAMA_MODEL,
        "status": check_ollama_status(),
        "test_request": {"success": test_success, "error": test_error},
        "local": True,
        "no_cloud": True
    }


# =============================================================================
# EXTRACTION
# =============================================================================

@app.post("/api/extract", response_model=Receipt)
async def extract_receipt(request: ReceiptExtractionRequest):
    """Extract structured data from a receipt image."""
    try:
        return await extract_receipt_from_image(
            image_path=request.image_path,
            image_base64=request.image_base64
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@app.post("/api/extract/upload")
async def extract_receipt_upload(file: UploadFile = File(...), session: Session = Depends(get_session)):
    """Extract data from uploaded receipt image and store in database."""
    try:
        # Read and encode image
        contents = await file.read()
        image_base64 = base64.b64encode(contents).decode()
        
        # Extract receipt data
        receipt = await extract_receipt_from_image(image_base64=image_base64)
        
        # Validate
        from services.receipt_validator import validate_receipt
        validation = validate_receipt(receipt)
        
        # Add to RAG
        receipt_id = f"upload_{file.filename}"
        add_receipt_to_rag(receipt, receipt_id)
        receipt.id = receipt_id
        
        # Store in database
        receipt_db = _create_receipt_db(receipt, session)
        
        return {
            **receipt.dict(),
            "db_id": receipt_db.id,
            "validation": {"status": validation["status"], "warnings_count": len(validation["warnings"])},
            "audit_flags": _get_audit_flags(receipt_db)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


# =============================================================================
# CHAT / RAG
# =============================================================================

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat endpoint with RAG - answers questions about receipts."""
    try:
        receipts_data = search_receipts(request.message, n_results=100)
        context = get_context_for_query(request.message)
        calculations = calculate_precise_answer(request.message, receipts_data)
        
        response = await generate_chat_response(
            question=request.message,
            context=context,
            history=request.history,
            calculations=calculations
        )
        
        return {
            "response": response,
            "sources_used": len(receipts_data[:5]),
            "calculations_used": calculations is not None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.post("/api/chat/query")
async def chat_query(request: dict, session: SessionDep):
    """
    Chat query endpoint for frontend - uses local Ollama LLM.
    
    Returns: {"answer": "...", "receipts": [...], "totalAmount": ..., "count": ...}
    """
    query = request.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    try:
        # Get precise calculations from Python
        calculations, filtered_receipts, filter_desc = parse_query_and_calculate(query, session)
        
        print(f"\n🔍 Query: {query}")
        print(f"   Filter: {filter_desc}")
        print(f"   Results: {len(filtered_receipts)} receipts, {calculations['result']['total']}€")
        
        # Build context from filtered receipts
        context = _build_receipt_context(filtered_receipts[:20], session)
        
        # Generate LLM response
        response_text = await generate_chat_response(
            question=query,
            context=context,
            history=[],
            calculations=calculations
        )
        
        # Format receipts for response
        receipts_list = [format_chat_receipt(r) for r in filtered_receipts[:20]]
        
        return {
            "answer": response_text,
            "receipts": receipts_list,
            "receiptIds": [r["id"] for r in receipts_list],
            "totalAmount": round(calculations['result']['total'], 2),
            "count": len(receipts_list)
        }
    except Exception as e:
        import traceback
        print(f"❌ Chat Query Error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Chat query failed: {str(e)}")


@app.get("/api/search")
async def search(query: str, limit: int = 10, category: str = None):
    """Semantic search in receipts."""
    results = search_receipts(query, n_results=limit, category_filter=category)
    return {"query": query, "results": results, "total": len(results)}


# =============================================================================
# RECEIPTS
# =============================================================================

@app.get("/api/receipts")
def get_receipts(session: SessionDep, receiptId: str = None):
    """Get all receipts or a single receipt by ID."""
    if receiptId:
        return _get_single_receipt(session, receiptId)
    return _get_all_receipts(session)


def _get_single_receipt(session: Session, receipt_id: str) -> dict:
    """Get a single receipt by ID."""
    receipt = session.get(ReceiptDB, int(receipt_id))
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    line_items = session.exec(select(LineItemDB).where(LineItemDB.receipt_id == receipt.id)).all()
    return {"receipt": format_receipt_for_api(receipt, line_items)}


def _get_all_receipts(session: Session) -> dict:
    """Get all receipts."""
    receipts = session.exec(select(ReceiptDB)).all()
    formatted = []
    
    for receipt in receipts:
        line_items = session.exec(select(LineItemDB).where(LineItemDB.receipt_id == receipt.id)).all()
        formatted.append(format_receipt_for_api(receipt, line_items))
    
    return {"count": len(formatted), "receipts": formatted}


# =============================================================================
# AUDIT
# =============================================================================

@app.get("/api/audit")
def get_audit_receipts(session: SessionDep):
    """Get all audit findings grouped by type."""
    duplicates = session.exec(select(ReceiptDB).where(ReceiptDB.flag_duplicate == True)).all()
    mismatches = session.exec(select(ReceiptDB).where(ReceiptDB.flag_math_error == True)).all()
    missing_vat = session.exec(select(ReceiptDB).where(ReceiptDB.flag_missing_vat == True)).all()
    suspicious = session.exec(select(ReceiptDB).where(ReceiptDB.flag_suspicious == True)).all()
    
    def get_findings(receipts):
        return [
            format_audit_finding(r, session.exec(select(LineItemDB).where(LineItemDB.receipt_id == r.id)).all())
            for r in receipts
        ]
    
    return {
        "duplicates": get_findings(duplicates),
        "mismatches": get_findings(mismatches),
        "missingVAT": get_findings(missing_vat),
        "suspicious": get_findings(suspicious),
        "summary": {
            "totalDuplicates": len(duplicates),
            "totalMismatches": len(mismatches),
            "totalMissingVAT": len(missing_vat),
            "totalSuspicious": len(suspicious)
        }
    }


# =============================================================================
# ANALYTICS
# =============================================================================

@app.get("/api/analytics/summary")
def get_analytics_summary(session: SessionDep):
    """Get complete analytics summary for dashboard."""
    # Summary stats
    total_receipts = session.exec(select(func.count(ReceiptDB.id))).one()
    total_spending = session.exec(select(func.sum(ReceiptDB.total_amount))).one() or 0.0
    total_vat = session.exec(select(func.sum(ReceiptDB.tax_amount))).one() or 0.0
    
    # Monthly data
    monthly = session.exec(
        select(
            func.strftime("%Y-%m", ReceiptDB.date),
            func.sum(ReceiptDB.total_amount),
            func.count(ReceiptDB.id)
        ).group_by(func.strftime("%Y-%m", ReceiptDB.date))
        .order_by(func.strftime("%Y-%m", ReceiptDB.date))
    ).all()
    
    # Categories
    categories = session.exec(
        select(ReceiptDB.category, func.sum(ReceiptDB.total_amount), func.count(ReceiptDB.id))
        .where(ReceiptDB.category.is_not(None))
        .group_by(ReceiptDB.category)
        .order_by(func.sum(ReceiptDB.total_amount).desc())
    ).all()
    
    # Vendors
    vendors = session.exec(
        select(ReceiptDB.vendor_name, func.sum(ReceiptDB.total_amount), func.count(ReceiptDB.id))
        .group_by(ReceiptDB.vendor_name)
        .order_by(func.sum(ReceiptDB.total_amount).desc())
        .limit(10)
    ).all()
    
    return {
        "summary": {
            "totalSpending": round(float(total_spending), 2),
            "totalReceipts": total_receipts,
            "totalVAT": round(float(total_vat), 2),
            "avgReceiptValue": round(float(total_spending) / total_receipts, 2) if total_receipts > 0 else 0
        },
        "monthly": [{"month": m, "amount": round(float(a), 2), "count": c} for m, a, c in monthly],
        "categories": [{"category": c, "amount": round(float(a), 2), "count": n} for c, a, n in categories],
        "vendors": [{"vendor": v, "amount": round(float(a), 2), "count": n} for v, a, n in vendors]
    }


@app.get("/api/analytics/categories")
async def get_spending_by_category(session: SessionDep):
    """Get spending breakdown by category."""
    results = session.exec(
        select(ReceiptDB.category, func.sum(ReceiptDB.total_amount))
        .where(ReceiptDB.category.is_not(None))
        .group_by(ReceiptDB.category)
        .order_by(func.sum(ReceiptDB.total_amount).desc())
    ).all()
    
    return {"category_totals": [{"category": c, "total": round(float(t), 2)} for c, t in results]}


@app.get("/api/analytics/monthly")
def get_monthly_analytics(session: SessionDep):
    """Get monthly spending totals."""
    results = session.exec(
        select(func.strftime("%Y-%m", ReceiptDB.date), func.sum(ReceiptDB.total_amount))
        .group_by(func.strftime("%Y-%m", ReceiptDB.date))
        .order_by(func.strftime("%Y-%m", ReceiptDB.date))
    ).all()
    
    return {"monthly_totals": [{"month": m, "total": round(float(t), 2)} for m, t in results]}


@app.get("/api/analytics/vendors")
def get_vendor_analytics(session: SessionDep):
    """Get vendor spending breakdown."""
    results = session.exec(
        select(ReceiptDB.vendor_name, func.sum(ReceiptDB.total_amount), func.count(ReceiptDB.id))
        .group_by(ReceiptDB.vendor_name)
        .order_by(func.sum(ReceiptDB.total_amount).desc())
    ).all()
    
    return {"vendors": [{"vendor": v, "amount": round(float(a), 2), "count": c} for v, a, c in results]}


@app.get("/api/analytics/category")
def get_category_analytics(session: SessionDep):
    """Get category statistics."""
    results = session.exec(
        select(ReceiptDB.category, func.sum(ReceiptDB.total_amount), func.count(ReceiptDB.id))
        .where(ReceiptDB.category.is_not(None))
        .group_by(ReceiptDB.category)
        .order_by(func.sum(ReceiptDB.total_amount).desc())
    ).all()
    
    return {"category_totals": [{"category": c, "amount": round(float(a), 2), "count": n} for c, a, n in results]}


# =============================================================================
# DATA INGESTION
# =============================================================================

@app.post("/api/ingest")
def ingest_receipt(receipt_data: ReceiptCreateDB, session: SessionDep):
    """Ingest a new receipt with line items."""
    receipt = ReceiptDB(
        vendor_name=receipt_data.vendor_name,
        date=receipt_data.date,
        total_amount=receipt_data.total_amount,
        tax_amount=receipt_data.tax_amount,
        currency=receipt_data.currency,
        category=receipt_data.category
    )
    
    line_items = [LineItemDB(description=item.description, amount=item.amount) for item in receipt_data.items]
    
    session.add(receipt)
    session.flush()
    
    for item in line_items:
        item.receipt_id = receipt.id
        session.add(item)
    
    receipt = run_audit(receipt, line_items, session)
    
    # Add to RAG
    _add_receipt_to_rag(receipt, line_items)
    
    session.commit()
    session.refresh(receipt)
    
    return {
        "status": "success",
        "message": f"Quittung von {receipt.vendor_name} gespeichert",
        "receipt_id": receipt.id,
        "audit_flags": _get_audit_flags(receipt)
    }


@app.post("/api/ingest/db", response_model=ReceiptReadDB)
def ingest_receipt_to_db(receipt_data: ReceiptCreateDB, session: SessionDep):
    """Store a new receipt with line items in the database."""
    receipt = ReceiptDB(
        vendor_name=receipt_data.vendor_name,
        date=receipt_data.date,
        total_amount=receipt_data.total_amount,
        tax_amount=receipt_data.tax_amount,
        currency=receipt_data.currency,
        category=receipt_data.category
    )
    
    line_items = [LineItemDB(description=item.description, amount=item.amount) for item in receipt_data.items]
    
    session.add(receipt)
    session.flush()
    
    for item in line_items:
        item.receipt_id = receipt.id
        session.add(item)
    
    receipt = run_audit(receipt, line_items, session)
    session.commit()
    session.refresh(receipt)
    
    return receipt


@app.post("/api/ingest/demo")
async def ingest_demo():
    """Load demo data into RAG database."""
    try:
        from services.cord_ingestion import load_demo_data
        load_demo_data()
        return {"message": "Demo-Daten geladen!", "stats": get_collection_stats()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.post("/api/receipt")
async def add_receipt(receipt: Receipt):
    """Add a manually created receipt."""
    try:
        receipt_id = receipt.id or f"manual_{hash(receipt.vendor_name + str(receipt.total))}"
        add_receipt_to_rag(receipt, receipt_id)
        receipt.id = receipt_id
        return {"message": "Quittung hinzugefügt!", "receipt": receipt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add receipt: {str(e)}")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _create_receipt_db(receipt: Receipt, session: Session) -> ReceiptDB:
    """Create a ReceiptDB object from a Receipt and save to database."""
    receipt_date = datetime.now()
    if receipt.date:
        try:
            receipt_date = datetime.fromisoformat(receipt.date.replace('Z', '+00:00')) if isinstance(receipt.date, str) else receipt.date
        except:
            pass
    
    receipt_db = ReceiptDB(
        vendor_name=receipt.vendor_name,
        date=receipt_date,
        total_amount=receipt.total,
        tax_amount=receipt.tax or 0.0,
        currency=receipt.currency,
        category=receipt.category
    )
    
    line_items_db = [LineItemDB(description=item.description, amount=item.total_price) for item in receipt.line_items]
    
    session.add(receipt_db)
    session.flush()
    
    for item in line_items_db:
        item.receipt_id = receipt_db.id
        session.add(item)
    
    receipt_db = run_audit(receipt_db, line_items_db, session)
    session.commit()
    session.refresh(receipt_db)
    
    return receipt_db


def _get_audit_flags(receipt: ReceiptDB) -> dict:
    """Get audit flags as dictionary."""
    return {
        "duplicate": receipt.flag_duplicate,
        "suspicious": receipt.flag_suspicious,
        "missing_vat": receipt.flag_missing_vat,
        "math_error": receipt.flag_math_error
    }


def _build_receipt_context(receipts: list, session: Session) -> str:
    """Build context string from receipts for LLM."""
    if not receipts:
        return "Keine passenden Quittungen gefunden."
    
    context_parts = []
    for i, receipt in enumerate(receipts, 1):
        line_items = session.exec(select(LineItemDB).where(LineItemDB.receipt_id == receipt.id)).all()
        items_text = ", ".join([f"{item.description} ({item.amount}€)" for item in line_items[:3]])
        
        context_parts.append(
            f"Quittung {i}: {receipt.vendor_name}, "
            f"{receipt.date.strftime('%d.%m.%Y') if receipt.date else 'unbekannt'}, "
            f"Total: {receipt.total_amount}€ ({receipt.category or 'Sonstiges'})"
        )
    
    return "\n".join(context_parts)


def _add_receipt_to_rag(receipt: ReceiptDB, line_items: list):
    """Add receipt to RAG database."""
    try:
        from models.receipt import Receipt as RAGReceipt, LineItem as RAGLineItem
        rag_receipt = RAGReceipt(
            id=f"db_{receipt.id}",
            vendor_name=receipt.vendor_name,
            date=receipt.date.isoformat() if receipt.date else None,
            total=receipt.total_amount,
            tax=receipt.tax_amount,
            currency=receipt.currency,
            category=receipt.category,
            line_items=[
                RAGLineItem(description=item.description, total_price=item.amount, quantity=1)
                for item in line_items
            ]
        )
        add_receipt_to_rag(rag_receipt, f"db_{receipt.id}")
    except Exception as e:
        print(f"⚠️  RAG storage failed: {e}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=True)
