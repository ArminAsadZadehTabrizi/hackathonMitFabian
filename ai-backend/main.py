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
from contextlib import asynccontextmanager
from typing import Annotated
from sqlmodel import Session, select, func
import base64
import uvicorn
from datetime import datetime

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


# ============== DATABASE RECEIPTS (von Partner 2) ==============

@app.get("/api/receipts")
def get_receipts(session: SessionDep):
    """Holt alle Quittungen mit ihren Audit-Flags."""
    statement = select(ReceiptDB)
    receipts = session.exec(statement).all()
    return {
        "count": len(receipts),
        "receipts": receipts
    }


@app.get("/api/audit")
def get_audit_receipts(session: SessionDep):
    """
    Holt alle Quittungen, die mindestens ein Audit-Flag gesetzt haben.
    
    Nützlich für die Anzeige geflaggter Quittungen auf der Audit-Seite.
    
    Returns:
        Liste der Quittungen mit mindestens einem gesetzten Audit-Flag
    """
    statement = select(ReceiptDB).where(
        (ReceiptDB.flag_duplicate == True) |
        (ReceiptDB.flag_suspicious == True) |
        (ReceiptDB.flag_missing_vat == True) |
        (ReceiptDB.flag_math_error == True)
    )
    flagged_receipts = session.exec(statement).all()
    return {
        "count": len(flagged_receipts),
        "flagged_receipts": flagged_receipts
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

