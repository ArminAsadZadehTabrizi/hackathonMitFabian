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
    - POST /api/ingest/db   - Quittung in DB speichern
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Annotated
from sqlmodel import Session, select, func
import base64
import uvicorn
from datetime import datetime
from pathlib import Path
import shutil

from config import API_HOST, API_PORT
from models.receipt import (
    Receipt,
    ReceiptExtractionRequest,
    ChatRequest,
    ChatMessage
)
from models.db_models import ReceiptDB, LineItemDB
from models.db_schemas import ReceiptCreateDB, ReceiptReadDB
from services.ollama_service import (
    extract_receipt_from_image,
    generate_chat_response,
    check_ollama_status
)
from services.rag_service import (
    init_rag,
    add_receipt_to_rag,
    search_receipts,
    get_context_for_query,
    get_collection_stats
)
from services.analytics_service import calculate_precise_answer
from smart_query_handler import parse_query_and_calculate
from services.cord_ingestion import load_demo_data, ingest_cord_to_rag
from services.database import init_db, get_session
from services.audit import run_audit

# Type alias für Dependency Injection
SessionDep = Annotated[Session, Depends(get_session)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & Shutdown Events"""
    print("🚀 AI Backend startet...")
    print("📊 Datenbank wird initialisiert...")
    init_db()
    print("🧠 RAG System wird initialisiert...")
    init_rag()
    print("✅ Alle Systeme bereit!")
    yield
    print("👋 AI Backend wird beendet...")


app = FastAPI(
    title="Finanz AI Backend (Integriert)",
    description="AI-powered Receipt Analysis with Local LLM + Database + Audit System",
    version="2.0.0",
    lifespan=lifespan
)

# CORS für Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In Produktion einschränken!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files für Bilder
UPLOAD_DIR = Path("./data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/api/images", StaticFiles(directory=str(UPLOAD_DIR)), name="images")


# ============== HEALTH & STATUS ==============

@app.get("/api/health")
async def health_check():
    """Health Check - Prüft alle Systeme"""
    ollama_status = check_ollama_status()
    rag_stats = get_collection_stats()
    
    return {
        "status": "healthy",
        "ollama": ollama_status,
        "rag": rag_stats
    }


@app.get("/api/ollama/verify")
def verify_ollama_usage():
    """
    Endpoint um zu verifizieren, dass Ollama verwendet wird.
    Zeigt detaillierte Informationen über die Ollama-Integration.
    """
    from services.ollama_service import OLLAMA_HOST, OLLAMA_CHAT_MODEL, OLLAMA_MODEL
    
    ollama_status = check_ollama_status()
    
    # Test-Request an Ollama
    test_success = False
    test_error = None
    try:
        import requests
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": OLLAMA_CHAT_MODEL,
                "prompt": "Test",
                "stream": False
            },
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
        "status": ollama_status,
        "test_request": {
            "success": test_success,
            "error": test_error
        },
        "usage_info": {
            "message": "✅ Ollama wird für alle Chat-Anfragen verwendet",
            "endpoint": "/api/chat/query",
            "model": OLLAMA_CHAT_MODEL,
            "local": True,
            "no_cloud": True,
            "how_to_verify": "Schau in die Backend-Logs wenn du /api/chat/query aufrufst - dort siehst du '🤖 Ollama Request'"
        }
    }


@app.get("/")
async def root():
    """Root Endpoint"""
    return {
        "message": "🧠 Finanz AI Backend läuft!",
        "docs": "/docs",
        "endpoints": [
            "POST /api/extract - Quittung analysieren",
            "POST /api/chat - Mit Daten chatten",
            "GET /api/search - Quittungen suchen",
            "POST /api/ingest/demo - Demo-Daten laden"
        ]
    }


# ============== EXTRACTION ==============

@app.post("/api/extract", response_model=Receipt)
async def extract_receipt(request: ReceiptExtractionRequest):
    """
    Extrahiert strukturierte Daten aus einem Quittungsbild.
    
    Sendet entweder:
    - image_base64: Base64-kodiertes Bild
    - image_path: Pfad zu einer lokalen Bilddatei
    """
    try:
        receipt = await extract_receipt_from_image(
            image_path=request.image_path,
            image_base64=request.image_base64
        )
        return receipt
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@app.post("/api/extract/upload")
async def extract_receipt_upload(file: UploadFile = File(...), session: Session = Depends(get_session)):
    """
    Extrahiert Daten aus einem hochgeladenen Quittungsbild.
    Speichert die Daten sowohl in RAG als auch in der SQL-Datenbank.
    """
    try:
        # Datei lesen und zu Base64 konvertieren
        contents = await file.read()
        image_base64 = base64.b64encode(contents).decode()
        
        receipt = await extract_receipt_from_image(image_base64=image_base64)
        
        # Validierung (optional - für Debugging)
        from services.receipt_validator import validate_receipt
        validation = validate_receipt(receipt)
        if validation["status"] != "valid":
            print(f"⚠️  Quittung hat {len(validation['warnings'])} Warnungen")
        
        # 1. Zur RAG-DB hinzufügen (für semantische Suche)
        receipt_id = f"upload_{file.filename}"
        add_receipt_to_rag(receipt, receipt_id)
        receipt.id = receipt_id
        
        # 2. Zur SQL-Datenbank hinzufügen (für strukturierte Queries & Audit)
        try:
            # Datum parsen (falls als String vorhanden)
            receipt_date = datetime.now()
            if receipt.date:
                try:
                    if isinstance(receipt.date, str):
                        receipt_date = datetime.fromisoformat(receipt.date.replace('Z', '+00:00'))
                    else:
                        receipt_date = receipt.date
                except:
                    print(f"⚠️  Konnte Datum nicht parsen: {receipt.date}")
            
            # ReceiptDB erstellen
            receipt_db = ReceiptDB(
                vendor_name=receipt.vendor_name,
                date=receipt_date,
                total_amount=receipt.total,
                tax_amount=receipt.tax or 0.0,
                currency=receipt.currency,
                category=receipt.category
            )
            
            # Line Items erstellen
            line_items_db = [
                LineItemDB(
                    description=item.description,
                    amount=item.total_price
                )
                for item in receipt.line_items
            ]
            
            # Zur Datenbank hinzufügen
            session.add(receipt_db)
            session.flush()
            
            # Line Items verknüpfen
            for item in line_items_db:
                item.receipt_id = receipt_db.id
                session.add(item)
            
            # Audit durchführen
            receipt_db = run_audit(receipt_db, line_items_db, session)
            
            session.commit()
            session.refresh(receipt_db)
            
            print(f"✅ Quittung in Datenbank gespeichert (ID: {receipt_db.id})")
            
            # Response mit Validierungs-Info und DB-ID erweitern
            response_data = receipt.dict()
            response_data["validation"] = {
                "status": validation["status"],
                "warnings_count": len(validation["warnings"])
            }
            response_data["db_id"] = receipt_db.id
            response_data["audit_flags"] = {
                "duplicate": receipt_db.flag_duplicate,
                "suspicious": receipt_db.flag_suspicious,
                "missing_vat": receipt_db.flag_missing_vat,
                "math_error": receipt_db.flag_math_error
            }
            
            return response_data
            
        except Exception as db_error:
            print(f"⚠️  Fehler beim Speichern in DB: {db_error}")
            # Trotzdem die Quittung zurückgeben (RAG ist ja gespeichert)
            response_data = receipt.dict()
            response_data["validation"] = {
                "status": validation["status"],
                "warnings_count": len(validation["warnings"])
            }
            response_data["db_error"] = str(db_error)
            return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


# ============== CHAT / RAG ==============

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Chatbot mit RAG - Beantwortet Fragen zu den Quittungen.
    
    Hybrid-Ansatz:
    - Python berechnet Zahlen präzise (deterministisch)
    - LLM formuliert Antwort natürlich
    
    Beispiel-Fragen:
    - "Wie viel habe ich für Alkohol ausgegeben?" → Präzise Berechnung
    - "Was waren meine Top 3 Ausgaben?" → Präzise Sortierung
    - "Zeige mir alle Tankstellen-Belege" → Semantische Suche
    """
    try:
        # Relevante Quittungen suchen
        receipts_data = search_receipts(request.message, n_results=100)
        context = get_context_for_query(request.message)
        
        # Präzise Berechnungen machen (Python)
        calculations = calculate_precise_answer(request.message, receipts_data)
        
        # Antwort generieren (LLM formuliert, nutzt präzise Zahlen)
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
    Chat-Query Endpoint für Frontend - nutzt lokales Ollama LLM.
    
    Erwartet: {"query": "Frage"}
    Returns: {"answer": "...", "receipts": [...], "receiptIds": [...], "totalAmount": ..., "count": ...}
    """
    try:
        query = request.get("query", "")
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # 1. PRÄZISE BERECHNUNG mit SQL (nicht LLM!)
        calculations, filtered_receipts, filter_desc = parse_query_and_calculate(query, session)
        
        print(f"\n{'='*60}")
        print(f"🔍 Query Analyse:")
        print(f"{'='*60}")
        print(f"Query: {query}")
        print(f"Filter: {filter_desc}")
        print(f"Gefundene Receipts: {len(filtered_receipts)}")
        print(f"Berechnete Summe: {calculations['result']['total']}€")
        print(f"{'='*60}\n")
        
        # 2. Erstelle Context aus gefilterten Receipts
        context_parts = []
        receipts_data = []
        
        for i, receipt in enumerate(filtered_receipts[:20], 1):
            line_items = session.exec(
                select(LineItemDB).where(LineItemDB.receipt_id == receipt.id)
            ).all()
            items_text = ", ".join([f"{item.description} ({item.amount}€)" for item in line_items[:3]])
            
            context_parts.append(
                f"Quittung {i}: {receipt.vendor_name}, {receipt.date.strftime('%d.%m.%Y') if receipt.date else 'unbekannt'}, "
                f"Total: {receipt.total_amount}€ ({receipt.category or 'Sonstiges'})"
            )
            
            receipts_data.append({
                "id": str(receipt.id),  # Use numeric ID without prefix for frontend links
                "receiptNumber": f"RCP-{receipt.id:04d}",
                "metadata": {
                    "vendor_name": receipt.vendor_name,
                    "date": receipt.date.isoformat() if receipt.date else "",
                    "total": receipt.total_amount,
                    "category": receipt.category or "Sonstiges"
                }
            })
        
        context = "\n".join(context_parts) if context_parts else "Keine passenden Quittungen gefunden."
        
        # 3. Fallback falls keine gefunden
        if not filtered_receipts:
            print("⚠️  Keine passenden Receipts gefunden")
            context = "Keine passenden Quittungen gefunden."
            receipts_data = []
        
        # 4. LLM-Antwort generieren (mit Ollama)
        print(f"\n{'='*60}")
        print(f"🤖 AI AUDITOR - Ollama Request (LOCAL LLM)")
        print(f"{'='*60}")
        print(f"Query: {query}")
        print(f"Filter: {filter_desc}")
        print(f"Gefilterte Receipts: {len(filtered_receipts)}")
        print(f"Berechnete Summe: {calculations['result']['total']}€")
        print(f"Using Ollama Model: llama3.2 (LOCAL, no cloud)")
        print(f"{'='*60}\n")
        
        response_text = await generate_chat_response(
            question=query,
            context=context,
            history=[],
            calculations=calculations
        )
        
        print(f"\n{'='*60}")
        print(f"✅ Ollama Response ({len(response_text)} Zeichen)")
        print(f"{'='*60}\n")
        
        # 5. Receipt IDs extrahieren
        receipt_ids = [r["id"] for r in receipts_data]
        
        # 6. Total Amount aus calculations
        total_amount = calculations['result']['total']
        
        # 7. Receipt-Objekte für Response
        receipts_list = []
        for r in receipts_data:
            receipts_list.append({
                "id": r["id"],
                "receiptNumber": r.get("receiptNumber", f"RCP-{r['id']}"),
                "vendor": r["metadata"].get("vendor_name", "Unknown"),
                "date": r["metadata"].get("date", ""),
                "total": r["metadata"].get("total", 0),
                "category": r["metadata"].get("category", "Sonstiges")
            })
        
        return {
            "answer": response_text,
            "receipts": receipts_list,
            "receiptIds": receipt_ids,
            "totalAmount": round(total_amount, 2),
            "count": len(receipts_list)
        }
    except Exception as e:
        import traceback
        print(f"❌ Chat Query Fehler: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Chat query failed: {str(e)}")


@app.get("/api/search")
async def search(query: str, limit: int = 10, category: str = None):
    """
    Semantische Suche in den Quittungen.
    
    Args:
        query: Suchanfrage in natürlicher Sprache
        limit: Max. Anzahl Ergebnisse
        category: Optional - Filter nach Kategorie
    """
    results = search_receipts(query, n_results=limit, category_filter=category)
    return {
        "query": query,
        "results": results,
        "total": len(results)
    }


# ============== DATA INGESTION ==============

@app.post("/api/ingest/demo")
async def ingest_demo():
    """Lädt Demo-Daten in die RAG-Datenbank."""
    try:
        load_demo_data()
        stats = get_collection_stats()
        return {
            "message": "Demo-Daten geladen!",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.post("/api/ingest/cord")
async def ingest_cord(cord_path: str, limit: int = 100):
    """
    Lädt CORD Dataset in die RAG-Datenbank.
    
    Args:
        cord_path: Pfad zum CORD Dataset Ordner
        limit: Max. Anzahl zu ladender Quittungen
    """
    try:
        ingest_cord_to_rag(cord_path, limit=limit)
        stats = get_collection_stats()
        return {
            "message": f"CORD Daten aus {cord_path} geladen!",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.post("/api/receipt")
async def add_receipt(receipt: Receipt):
    """
    Fügt eine manuell erstellte Quittung zur Datenbank hinzu.
    (Für Person 2 - Backend Integration)
    """
    try:
        receipt_id = receipt.id or f"manual_{hash(receipt.vendor_name + str(receipt.total))}"
        add_receipt_to_rag(receipt, receipt_id)
        receipt.id = receipt_id
        return {"message": "Quittung hinzugefügt!", "receipt": receipt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add receipt: {str(e)}")


# ============== ANALYTICS HELPER ==============

@app.get("/api/analytics/categories")
async def get_spending_by_category(session: SessionDep):
    """
    Gibt Ausgaben pro Kategorie zurück.
    Nutzt SQL-Aggregationen für präzise Berechnungen.
    """
    statement = (
        select(
            ReceiptDB.category,
            func.sum(ReceiptDB.total_amount).label("total")
        )
        .where(ReceiptDB.category.is_not(None))
        .group_by(ReceiptDB.category)
        .order_by(func.sum(ReceiptDB.total_amount).desc())
    )
    
    results = session.exec(statement).all()
    
    return {
        "category_totals": [
            {"category": category, "total": round(float(total), 2)}
            for category, total in results
        ]
    }


@app.get("/api/analytics/monthly")
def get_monthly_analytics(session: SessionDep):
    """
    Monatliche Analytics: Gesamtbetrag pro Monat (YYYY-MM).
    
    Returns:
        Liste mit {month: "YYYY-MM", total: float}
    """
    # SQLite verwendet strftime für Datumsformatierung
    # %Y-%m gibt uns YYYY-MM Format
    statement = (
        select(
            func.strftime("%Y-%m", ReceiptDB.date).label("month"),
            func.sum(ReceiptDB.total_amount).label("total")
        )
        .group_by(func.strftime("%Y-%m", ReceiptDB.date))
        .order_by(func.strftime("%Y-%m", ReceiptDB.date))
    )
    
    results = session.exec(statement).all()
    
    return {
        "monthly_totals": [
            {"month": month, "total": round(float(total), 2)}
            for month, total in results
        ]
    }


@app.get("/api/analytics/summary")
def get_analytics_summary(session: SessionDep):
    """
    Analytics-Zusammenfassung für Dashboard.
    
    Returns:
        summary, monthly, categories, vendors
    """
    # Gesamtstatistik
    total_receipts = session.exec(select(func.count(ReceiptDB.id))).one()
    total_spending = session.exec(select(func.sum(ReceiptDB.total_amount))).one() or 0.0
    total_vat = session.exec(select(func.sum(ReceiptDB.tax_amount))).one() or 0.0
    avg_receipt = total_spending / total_receipts if total_receipts > 0 else 0.0
    
    # Monatliche Daten
    monthly_statement = (
        select(
            func.strftime("%Y-%m", ReceiptDB.date).label("month"),
            func.sum(ReceiptDB.total_amount).label("amount"),
            func.count(ReceiptDB.id).label("count")
        )
        .group_by(func.strftime("%Y-%m", ReceiptDB.date))
        .order_by(func.strftime("%Y-%m", ReceiptDB.date))
    )
    monthly_results = session.exec(monthly_statement).all()
    
    # Kategorien
    categories_statement = (
        select(
            ReceiptDB.category,
            func.sum(ReceiptDB.total_amount).label("amount"),
            func.count(ReceiptDB.id).label("count")
        )
        .where(ReceiptDB.category.is_not(None))
        .group_by(ReceiptDB.category)
        .order_by(func.sum(ReceiptDB.total_amount).desc())
    )
    categories_results = session.exec(categories_statement).all()
    
    # Vendors
    vendors_statement = (
        select(
            ReceiptDB.vendor_name,
            func.sum(ReceiptDB.total_amount).label("amount"),
            func.count(ReceiptDB.id).label("count")
        )
        .group_by(ReceiptDB.vendor_name)
        .order_by(func.sum(ReceiptDB.total_amount).desc())
        .limit(10)
    )
    vendors_results = session.exec(vendors_statement).all()
    
    return {
        "summary": {
            "totalSpending": round(float(total_spending), 2),
            "totalReceipts": total_receipts,
            "totalVAT": round(float(total_vat), 2),
            "avgReceiptValue": round(float(avg_receipt), 2)
        },
        "monthly": [
            {
                "month": month,
                "amount": round(float(amount), 2),
                "count": count
            }
            for month, amount, count in monthly_results
        ],
        "categories": [
            {
                "category": category,
                "amount": round(float(amount), 2),
                "count": count
            }
            for category, amount, count in categories_results
        ],
        "vendors": [
            {
                "vendor": vendor,
                "amount": round(float(amount), 2),
                "count": count
            }
            for vendor, amount, count in vendors_results
        ]
    }


@app.get("/api/analytics/category")
def get_category_analytics(session: SessionDep):
    """
    Kategorie-Statistiken.
    
    Returns:
        Liste der Kategorien mit Beträgen und Anzahl
    """
    statement = (
        select(
            ReceiptDB.category,
            func.sum(ReceiptDB.total_amount).label("amount"),
            func.count(ReceiptDB.id).label("count")
        )
        .where(ReceiptDB.category.is_not(None))
        .group_by(ReceiptDB.category)
        .order_by(func.sum(ReceiptDB.total_amount).desc())
    )
    
    results = session.exec(statement).all()
    
    return {
        "category_totals": [
            {
                "category": category,
                "amount": round(float(amount), 2),
                "count": count
            }
            for category, amount, count in results
        ]
    }


@app.get("/api/analytics/vendors")
def get_vendor_analytics(session: SessionDep):
    """
    Vendor-Statistiken.
    
    Returns:
        Liste der Top Vendors mit Beträgen und Anzahl
    """
    statement = (
        select(
            ReceiptDB.vendor_name,
            func.sum(ReceiptDB.total_amount).label("amount"),
            func.count(ReceiptDB.id).label("count")
        )
        .group_by(ReceiptDB.vendor_name)
        .order_by(func.sum(ReceiptDB.total_amount).desc())
    )
    
    results = session.exec(statement).all()
    
    return {
        "vendors": [
            {
                "vendor": vendor,
                "amount": round(float(amount), 2),
                "count": count
            }
            for vendor, amount, count in results
        ]
    }


# ============== DATABASE RECEIPTS (von Partner 2) ==============

@app.get("/api/receipts")
def get_receipts(session: SessionDep, receiptId: str = None):
    """
    Holt alle Quittungen oder eine einzelne Quittung.
    
    Args:
        receiptId: Optional - ID einer spezifischen Quittung
    """
    if receiptId:
        # Einzelne Quittung
        receipt = session.get(ReceiptDB, int(receiptId))
        if not receipt:
            raise HTTPException(status_code=404, detail="Receipt not found")
        
        # Line Items laden
        line_items = session.exec(
            select(LineItemDB).where(LineItemDB.receipt_id == receipt.id)
        ).all()
        
        # Bild-URL erstellen
        image_url = f"http://localhost:8000/api/images/{receipt.image_path}" if receipt.image_path else None
        
        # Format für Frontend
        return {
            "receipt": {
                "id": str(receipt.id),
                "receiptNumber": f"RCP-{receipt.id:04d}",
                "vendor": receipt.vendor_name,
                "vendorVAT": None,
                "date": receipt.date.isoformat() if receipt.date else None,
                "total": receipt.total_amount,
                "subtotal": receipt.total_amount - receipt.tax_amount,
                "vat": receipt.tax_amount,
                "vatRate": None,
                "paymentMethod": None,
                "category": receipt.category or "Sonstiges",
                "currency": receipt.currency,
                "imageUrl": image_url,
                "lineItems": [
                    {
                        "id": str(item.id),
                        "description": item.description,
                        "quantity": 1,
                        "unitPrice": item.amount,
                        "total": item.amount,
                        "vat": 0
                    }
                    for item in line_items
                ],
                "status": "duplicate" if receipt.flag_duplicate else ("flagged" if any([receipt.flag_suspicious, receipt.flag_missing_vat, receipt.flag_math_error]) else "verified"),
                "tags": [],
                "notes": None,
                "createdAt": receipt.date.isoformat() if receipt.date else None,
                "updatedAt": receipt.date.isoformat() if receipt.date else None,
                "auditFlags": {
                    "isDuplicate": receipt.flag_duplicate,
                    "hasTotalMismatch": receipt.flag_math_error,
                    "missingVAT": receipt.flag_missing_vat,
                    "suspiciousCategory": "Alkohol" if receipt.flag_suspicious else None
                }
            }
        }
    
    # Alle Quittungen - Format für Frontend
    statement = select(ReceiptDB)
    receipts = session.exec(statement).all()
    
    formatted_receipts = []
    for receipt in receipts:
        # Line Items laden
        line_items = session.exec(
            select(LineItemDB).where(LineItemDB.receipt_id == receipt.id)
        ).all()
        
        # Bild-URL erstellen
        image_url = f"http://localhost:8000/api/images/{receipt.image_path}" if receipt.image_path else None
        
        # Format für Frontend
        formatted_receipt = {
            "id": str(receipt.id),
            "receiptNumber": f"RCP-{receipt.id:04d}",
            "vendor": receipt.vendor_name,
            "vendorVAT": None,
            "date": receipt.date.isoformat() if receipt.date else None,
            "total": float(receipt.total_amount),
            "subtotal": float(receipt.total_amount - receipt.tax_amount),
            "vat": float(receipt.tax_amount) if receipt.tax_amount else None,
            "vatRate": None,
            "paymentMethod": None,
            "category": receipt.category or "Sonstiges",
            "currency": receipt.currency,
            "imageUrl": image_url,
            "lineItems": [
                {
                    "id": str(item.id),
                    "description": item.description,
                    "quantity": 1,
                    "unitPrice": float(item.amount),
                    "total": float(item.amount),
                    "vat": 0
                }
                for item in line_items
            ],
            "status": "duplicate" if receipt.flag_duplicate else ("flagged" if any([receipt.flag_suspicious, receipt.flag_missing_vat, receipt.flag_math_error]) else "verified"),
            "tags": [],
            "notes": None,
            "createdAt": receipt.date.isoformat() if receipt.date else None,
            "updatedAt": receipt.date.isoformat() if receipt.date else None,
            "auditFlags": {
                "isDuplicate": receipt.flag_duplicate,
                "hasTotalMismatch": receipt.flag_math_error,
                "missingVAT": receipt.flag_missing_vat,
                "suspiciousCategory": "Alkohol" if receipt.flag_suspicious else None
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
    Audit-Findings im Frontend-Format.
    
    Returns:
        duplicates, mismatches, missingVAT, suspicious, summary
    """
    # Duplikate
    duplicates = session.exec(
        select(ReceiptDB).where(ReceiptDB.flag_duplicate == True)
    ).all()
    
    # Rechenfehler
    mismatches = session.exec(
        select(ReceiptDB).where(ReceiptDB.flag_math_error == True)
    ).all()
    
    # Fehlende MwSt
    missing_vat = session.exec(
        select(ReceiptDB).where(ReceiptDB.flag_missing_vat == True)
    ).all()
    
    # Verdächtige
    suspicious = session.exec(
        select(ReceiptDB).where(ReceiptDB.flag_suspicious == True)
    ).all()
    
    def format_finding(receipt: ReceiptDB) -> dict:
        """Formatiert Receipt für Audit-Finding."""
        # Line Items für Total-Berechnung
        line_items = session.exec(
            select(LineItemDB).where(LineItemDB.receipt_id == receipt.id)
        ).all()
        items_sum = sum(item.amount for item in line_items)
        
        return {
            "receiptId": str(receipt.id),
            "receiptNumber": f"RCP-{receipt.id:04d}",
            "vendor": receipt.vendor_name,
            "date": receipt.date.isoformat() if receipt.date else None,
            "total": receipt.total_amount,
            "expectedTotal": items_sum if receipt.flag_math_error else None,
            "actualTotal": receipt.total_amount if receipt.flag_math_error else None,
            "difference": abs(items_sum - receipt.total_amount) if receipt.flag_math_error else None,
            "category": receipt.category or "Sonstiges",
            "issue": (
                "Duplicate receipt" if receipt.flag_duplicate else
                "Math error" if receipt.flag_math_error else
                "Missing VAT" if receipt.flag_missing_vat else
                "Suspicious category" if receipt.flag_suspicious else None
            )
        }
    
    return {
        "duplicates": [format_finding(r) for r in duplicates],
        "mismatches": [format_finding(r) for r in mismatches],
        "missingVAT": [format_finding(r) for r in missing_vat],
        "suspicious": [format_finding(r) for r in suspicious],
        "summary": {
            "totalDuplicates": len(duplicates),
            "totalMismatches": len(mismatches),
            "totalMissingVAT": len(missing_vat),
            "totalSuspicious": len(suspicious)
        }
    }


@app.post("/api/ingest")
def ingest_receipt(receipt_data: ReceiptCreateDB, session: SessionDep):
    """
    🎯 Hauptendpoint für LLM-Outputs von CORD-Analyse.
    
    Erwartet JSON im Format:
    {
        "vendor_name": "Saturn",
        "date": "2023-11-29T10:00:00",
        "total_amount": 150.00,
        "tax_amount": 28.50,
        "currency": "EUR",
        "category": "Hardware",
        "items": [
            {"description": "Monitor", "amount": 150.00}
        ]
    }
    
    Speichert in DB + RAG und führt Audit-Checks durch.
    """
    # Receipt-Objekt erstellen
    receipt = ReceiptDB(
        vendor_name=receipt_data.vendor_name,
        date=receipt_data.date,
        total_amount=receipt_data.total_amount,
        tax_amount=receipt_data.tax_amount,
        currency=receipt_data.currency,
        category=receipt_data.category
    )
    
    # Line Items erstellen
    line_items = [
        LineItemDB(
            description=item.description,
            amount=item.amount
        )
        for item in receipt_data.items
    ]
    
    # Receipt zur Session hinzufügen
    session.add(receipt)
    session.flush()
    
    # Line Items verknüpfen
    for item in line_items:
        item.receipt_id = receipt.id
        session.add(item)
    
    # Audit-Checks durchführen
    receipt = run_audit(receipt, line_items, session)
    
    # Auch zur RAG-DB hinzufügen (für semantische Suche)
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
                RAGLineItem(
                    description=item.description,
                    total_price=item.amount,
                    quantity=1
                )
                for item in line_items
            ]
        )
        add_receipt_to_rag(rag_receipt, f"db_{receipt.id}")
    except Exception as e:
        print(f"⚠️  RAG-Speicherung fehlgeschlagen: {e}")
    
    session.commit()
    session.refresh(receipt)
    
    return {
        "status": "success",
        "message": f"Quittung von {receipt.vendor_name} gespeichert",
        "receipt_id": receipt.id,
        "audit_flags": {
            "duplicate": receipt.flag_duplicate,
            "suspicious": receipt.flag_suspicious,
            "missing_vat": receipt.flag_missing_vat,
            "math_error": receipt.flag_math_error
        }
    }


@app.post("/api/ingest/db", response_model=ReceiptReadDB)
def ingest_receipt_to_db(receipt_data: ReceiptCreateDB, session: SessionDep):
    """
    Speichert eine neue Quittung mit Line Items in der Datenbank.
    
    Führt automatisch Audit-Checks durch:
    - Fehlende MwSt.-Erkennung
    - Rechenfehler-Erkennung (Summe der Line Items vs. Gesamt)
    - Verdächtige Items-Erkennung (Alkohol/Tabak)
    - Duplikats-Erkennung
    
    Args:
        receipt_data: Quittungsdaten mit Line Items
        session: Datenbank-Session
        
    Returns:
        Erstellte Quittung mit Audit-Flags und Line Items
    """
    # Receipt-Objekt erstellen (ohne Line Items zuerst)
    receipt = ReceiptDB(
        vendor_name=receipt_data.vendor_name,
        date=receipt_data.date,
        total_amount=receipt_data.total_amount,
        tax_amount=receipt_data.tax_amount,
        currency=receipt_data.currency,
        category=receipt_data.category
    )
    
    # Line Items erstellen
    line_items = [
        LineItemDB(
            description=item.description,
            amount=item.amount
        )
        for item in receipt_data.items
    ]
    
    # Receipt zur Session hinzufügen um ID zu bekommen (für Duplikats-Check)
    session.add(receipt)
    session.flush()  # ID holen ohne zu committen
    
    # Line Items mit Receipt verknüpfen
    for item in line_items:
        item.receipt_id = receipt.id
        session.add(item)
    
    # Audit-Checks durchführen
    receipt = run_audit(receipt, line_items, session)
    
    # Alles committen
    session.commit()
    session.refresh(receipt)
    
    return receipt


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    )

