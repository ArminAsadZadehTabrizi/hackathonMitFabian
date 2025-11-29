"""
RAG Service - Vector Search mit ChromaDB für den Chatbot
Fallback auf einfache In-Memory Suche wenn ChromaDB nicht verfügbar
"""
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("⚠️  ChromaDB nicht verfügbar - verwende In-Memory Fallback")

from sentence_transformers import SentenceTransformer
from typing import List, Optional, Dict, Tuple
import json

from config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME, EMBEDDING_MODEL
from models.receipt import Receipt


# Globale Variablen (werden bei Modul-Import initialisiert)
embedding_model = None
chroma_client = None
collection = None
# Fallback: In-Memory Storage
_memory_storage: List[Tuple[str, str, Dict]] = []  # [(id, document, metadata), ...]
_receipt_objects: Dict[str, Receipt] = {}  # {id: Receipt} - Original Receipt-Objekte für präzise Berechnungen
# Caching für Embeddings (Performance-Optimierung)
_embedding_cache: Dict[str, List[float]] = {}  # {text: embedding}


def init_rag():
    """Initialisiert ChromaDB (oder Fallback) und das Embedding Model."""
    global embedding_model, chroma_client, collection
    
    print("🔄 Lade Embedding Model...")
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    
    if CHROMADB_AVAILABLE:
        try:
            print("🔄 Initialisiere ChromaDB...")
            chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            collection = chroma_client.get_or_create_collection(
                name=CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"✅ RAG initialisiert (ChromaDB). {collection.count()} Dokumente.")
            return collection
        except Exception as e:
            print(f"⚠️  ChromaDB Fehler: {e} - verwende Fallback")
    
    print("✅ RAG initialisiert (In-Memory Fallback).")
    return None


def receipt_to_document(receipt: Receipt) -> str:
    """
    Konvertiert eine Quittung in ein durchsuchbares Dokument.
    """
    items_text = ""
    for item in receipt.line_items:
        items_text += f"\n  - {item.description}: {item.total_price}€"
        if item.category:
            items_text += f" (Kategorie: {item.category})"
    
    doc = f"""
Quittung von {receipt.vendor_name}
Datum: {receipt.date or 'unbekannt'}
Gesamtbetrag: {receipt.total}€
Kategorie: {receipt.category or 'unbekannt'}
MwSt: {receipt.tax or 0}€ ({receipt.tax_rate or 0}%)
Zahlungsart: {receipt.payment_method or 'unbekannt'}
Positionen:{items_text if items_text else ' keine Details'}
"""
    return doc.strip()


def add_receipt_to_rag(receipt: Receipt, receipt_id: str):
    """
    Fügt eine Quittung zur RAG-Datenbank hinzu.
    """
    global _receipt_objects
    
    if embedding_model is None:
        init_rag()
    
    # Dokument erstellen
    document = receipt_to_document(receipt)
    
    # Metadata für Filtering
    metadata = {
        "vendor_name": receipt.vendor_name,
        "date": receipt.date or "",
        "total": receipt.total,
        "category": receipt.category or "unknown",
        "currency": receipt.currency
    }
    
    if collection is not None:
        # Zu ChromaDB hinzufügen (mit Cache)
        embedding = _get_embedding(document)
        collection.upsert(
            ids=[receipt_id],
            embeddings=[embedding],
            documents=[document],
            metadatas=[metadata]
        )
    else:
        # Fallback: In-Memory
        _memory_storage.append((receipt_id, document, metadata))
    
    # Original Receipt-Objekt speichern für präzise Berechnungen
    _receipt_objects[receipt_id] = receipt
    
    print(f"✅ Quittung {receipt_id} zur RAG-DB hinzugefügt")


def add_receipts_batch(receipts: List[tuple]):
    """
    Fügt mehrere Quittungen auf einmal hinzu (schneller).
    
    Args:
        receipts: Liste von (receipt_id, Receipt) Tupeln
    """
    global _receipt_objects
    
    if embedding_model is None:
        init_rag()
    
    if collection is not None:
        # ChromaDB Batch
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        for receipt_id, receipt in receipts:
            doc = receipt_to_document(receipt)
            ids.append(receipt_id)
            documents.append(doc)
            embeddings.append(_get_embedding(doc))
            metadatas.append({
                "vendor_name": receipt.vendor_name,
                "date": receipt.date or "",
                "total": receipt.total,
                "category": receipt.category or "unknown",
                "currency": receipt.currency
            })
            # Original Receipt speichern
            _receipt_objects[receipt_id] = receipt
        
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
    else:
        # Fallback: In-Memory
        for receipt_id, receipt in receipts:
            doc = receipt_to_document(receipt)
            metadata = {
                "vendor_name": receipt.vendor_name,
                "date": receipt.date or "",
                "total": receipt.total,
                "category": receipt.category or "unknown",
                "currency": receipt.currency
            }
            _memory_storage.append((receipt_id, doc, metadata))
            # Original Receipt speichern
            _receipt_objects[receipt_id] = receipt
    
    print(f"✅ {len(receipts)} Quittungen zur RAG-DB hinzugefügt")


def get_receipt_objects_by_ids(receipt_ids: List[str]) -> List[Receipt]:
    """
    Holt Receipt-Objekte anhand ihrer IDs für präzise Berechnungen.
    """
    return [_receipt_objects.get(rid) for rid in receipt_ids if rid in _receipt_objects]


def _get_embedding(text: str) -> List[float]:
    """
    Holt Embedding mit Caching für bessere Performance.
    """
    global _embedding_cache
    
    # Prüfe Cache
    if text in _embedding_cache:
        return _embedding_cache[text]
    
    # Berechne Embedding
    if embedding_model is None:
        init_rag()
    
    embedding = embedding_model.encode(text).tolist()
    
    # Cache speichern (max 1000 Einträge)
    if len(_embedding_cache) < 1000:
        _embedding_cache[text] = embedding
    
    return embedding


def search_receipts(
    query: str,
    n_results: int = 5,
    category_filter: Optional[str] = None
) -> List[dict]:
    """
    Sucht relevante Quittungen basierend auf einer Frage.
    
    Args:
        query: Die Suchanfrage (natürliche Sprache)
        n_results: Anzahl der Ergebnisse
        category_filter: Optional - nur diese Kategorie
    
    Returns:
        Liste von relevanten Dokumenten mit Metadata
    """
    if embedding_model is None:
        init_rag()
    
    # Query embedding berechnen (mit Cache)
    query_embedding_array = _get_embedding(query)
    import numpy as np
    query_embedding = np.array(query_embedding_array)
    
    if collection is not None:
        # ChromaDB verwenden
        where_filter = None
        if category_filter:
            where_filter = {"category": category_filter}
        
        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        formatted = []
        for i in range(len(results["ids"][0])):
            formatted.append({
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "similarity": 1 - results["distances"][0][i]
            })
        return formatted
    else:
        # Fallback: In-Memory Suche
        import numpy as np
        from numpy.linalg import norm
        
        scores = []
        for receipt_id, document, metadata in _memory_storage:
            # Filter
            if category_filter and metadata.get("category") != category_filter:
                continue
            
            # Embedding berechnen (mit Cache)
            doc_embedding = _get_embedding(document)
            
            # Cosine Similarity
            similarity = np.dot(query_embedding, doc_embedding) / (norm(query_embedding) * norm(doc_embedding))
            
            scores.append((receipt_id, document, metadata, float(similarity)))
        
        # Sortieren und Top N
        scores.sort(key=lambda x: x[3], reverse=True)
        
        formatted = []
        for receipt_id, document, metadata, similarity in scores[:n_results]:
            formatted.append({
                "id": receipt_id,
                "document": document,
                "metadata": metadata,
                "similarity": similarity
            })
        
        return formatted


def get_context_for_query(query: str, n_results: int = 5) -> str:
    """
    Holt den Kontext für eine RAG-Anfrage.
    Formatiert die Ergebnisse als String für das LLM.
    """
    results = search_receipts(query, n_results)
    
    if not results:
        return "Keine relevanten Quittungen gefunden."
    
    context_parts = []
    for i, result in enumerate(results, 1):
        context_parts.append(f"--- Quittung {i} (Relevanz: {result['similarity']:.0%}) ---")
        context_parts.append(result["document"])
    
    return "\n\n".join(context_parts)


def get_collection_stats() -> dict:
    """Gibt Statistiken über die RAG-Datenbank zurück."""
    if embedding_model is None:
        init_rag()
    
    if collection is not None:
        return {
            "total_documents": collection.count(),
            "collection_name": CHROMA_COLLECTION_NAME,
            "backend": "chromadb"
        }
    else:
        return {
            "total_documents": len(_memory_storage),
            "collection_name": "in_memory",
            "backend": "in_memory_fallback"
        }

