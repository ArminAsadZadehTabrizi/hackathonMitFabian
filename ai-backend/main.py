"""
🧠 AI Backend für Quittungs-Analyse
FastAPI Server mit Ollama LLM + ChromaDB RAG

Endpoints:
    - POST /api/extract     - Extrahiert Daten aus Quittungsbild
    - POST /api/chat        - Chatbot mit RAG
    - GET  /api/search      - Semantische Suche in Quittungen
    - GET  /api/health      - Health Check
    - POST /api/ingest      - Daten in RAG laden
"""
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import base64
import uvicorn

from config import API_HOST, API_PORT
from models.receipt import (
    Receipt,
    ReceiptExtractionRequest,
    ChatRequest,
    ChatMessage
)
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & Shutdown Events"""
    print("🚀 AI Backend startet...")
    init_rag()
    print("✅ RAG System bereit!")
    yield
    print("👋 AI Backend wird beendet...")


app = FastAPI(
    title="Finanz AI Backend",
    description="AI-powered Receipt Analysis with Local LLM",
    version="1.0.0",
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


@app.post("/api/extract/upload", response_model=Receipt)
async def extract_receipt_upload(file: UploadFile = File(...)):
    """
    Extrahiert Daten aus einem hochgeladenen Quittungsbild.
    """
    try:
        # Datei lesen und zu Base64 konvertieren
        contents = await file.read()
        image_base64 = base64.b64encode(contents).decode()
        
        receipt = await extract_receipt_from_image(image_base64=image_base64)
        
        # Zur RAG-DB hinzufügen
        receipt_id = f"upload_{file.filename}"
        add_receipt_to_rag(receipt, receipt_id)
        receipt.id = receipt_id
        
        return receipt
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
async def get_spending_by_category():
    """
    Gibt Ausgaben pro Kategorie zurück.
    (Einfache Implementierung - Person 2 macht die echte Logik in SQL)
    """
    # Das hier ist ein Placeholder - die echte Logik macht Person 2
    # mit SQL Aggregationen in der Haupt-DB
    results = search_receipts("alle Ausgaben", n_results=100)
    
    categories = {}
    for r in results:
        cat = r["metadata"].get("category", "Sonstiges")
        total = r["metadata"].get("total", 0)
        categories[cat] = categories.get(cat, 0) + total
    
    return {"spending_by_category": categories}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    )

