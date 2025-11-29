"""
Interaktives Chat-Script: Quittungen aus DB mit lokalem LLM analysieren

Dieses Script:
1. Lädt Quittungen aus der SQLite-Datenbank
2. Konvertiert sie ins RAG-Format (optional)
3. Ermöglicht interaktive Fragen mit dem lokalen LLM
"""

import asyncio
import sys
from pathlib import Path

# Datenbank-Importe
from sqlmodel import Session, select
from services.database import engine, init_db
from models.db_models import ReceiptDB, LineItemDB

# LLM-Importe
from services.ollama_service import generate_chat_response, check_ollama_status
from services.rag_service import init_rag, add_receipt_to_rag, receipt_to_document, get_context_for_query
from models.receipt import Receipt, LineItem


def convert_db_receipt_to_rag_receipt(db_receipt: ReceiptDB, line_items: list) -> Receipt:
    """Konvertiert ein ReceiptDB zu einem Receipt (für RAG)."""
    # Line Items konvertieren
    rag_line_items = [
        LineItem(
            description=item.description,
            quantity=1.0,  # Standard, da wir das nicht in DB haben
            total_price=item.amount,
            category=None  # Könnten wir aus description ableiten
        )
        for item in line_items
    ]
    
    # Receipt erstellen
    rag_receipt = Receipt(
        vendor_name=db_receipt.vendor_name,
        date=db_receipt.date.isoformat() if db_receipt.date else None,
        total=db_receipt.total_amount,
        tax=db_receipt.tax_amount,
        currency=db_receipt.currency,
        category=db_receipt.category,
        line_items=rag_line_items
    )
    
    return rag_receipt


def load_receipts_from_db() -> list:
    """Lädt alle Quittungen aus der Datenbank."""
    init_db()
    with Session(engine) as session:
        statement = select(ReceiptDB)
        receipts = session.exec(statement).all()
        
        result = []
        for receipt in receipts:
            # Line Items laden
            items_statement = select(LineItemDB).where(LineItemDB.receipt_id == receipt.id)
            items = session.exec(items_statement).all()
            result.append((receipt, list(items)))
        
        return result


def format_receipts_for_context(receipts_data: list) -> str:
    """Formatiert Quittungen als Text-Kontext für das LLM."""
    context_parts = []
    
    for receipt, items in receipts_data:
        items_text = "\n".join([f"  - {item.description}: {item.amount}€" for item in items])
        
        receipt_text = f"""
═══════════════════════════════════════════════════
Quittung #{receipt.id}
Vendor: {receipt.vendor_name}
Datum: {receipt.date.isoformat() if receipt.date else 'unbekannt'}
Gesamtbetrag: {receipt.total_amount}€
MwSt: {receipt.tax_amount}€
Kategorie: {receipt.category or 'unbekannt'}
Währung: {receipt.currency}

Audit-Flags:
  - Duplikat: {'✓' if receipt.flag_duplicate else '✗'}
  - Verdächtig: {'✓' if receipt.flag_suspicious else '✗'}
  - MwSt fehlt: {'✓' if receipt.flag_missing_vat else '✗'}
  - Rechenfehler: {'✓' if receipt.flag_math_error else '✗'}

Positionen:
{items_text}
═══════════════════════════════════════════════════
"""
        context_parts.append(receipt_text)
    
    return "\n".join(context_parts)


async def chat_loop(receipts_data: list):
    """Haupt-Chat-Loop."""
    print("\n" + "="*60)
    print("💬 CHAT MIT LOKALEM LLM")
    print("="*60)
    print(f"📊 {len(receipts_data)} Quittungen geladen")
    print("\n💡 Beispiel-Fragen:")
    print("   - 'Wie viel habe ich insgesamt ausgegeben?'")
    print("   - 'Zeige mir alle verdächtigen Quittungen'")
    print("   - 'Was waren meine Top-Ausgaben?'")
    print("   - 'Wie viel für Alkohol?'")
    print("   - 'Welche Quittungen haben Rechenfehler?'")
    print("\nTipp: Tippe 'exit' zum Beenden\n")
    
    history = []
    
    while True:
        try:
            question = input("❓ Deine Frage: ").strip()
            
            if not question:
                continue
            
            if question.lower() in ['exit', 'quit', 'q', 'beenden']:
                print("\n👋 Auf Wiedersehen!")
                break
            
            print("\n🤔 Denke nach...\n")
            
            # Kontext für LLM erstellen
            context = format_receipts_for_context(receipts_data)
            
            # Antwort generieren
            response = await generate_chat_response(
                question=question,
                context=context,
                history=history
            )
            
            print("🤖 Antwort:")
            print(response)
            print("\n" + "-"*60 + "\n")
            
            # History aktualisieren (optional)
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": response})
            
            # History begrenzen (letzte 10 Nachrichten)
            if len(history) > 10:
                history = history[-10:]
        
        except KeyboardInterrupt:
            print("\n\n👋 Beendet durch Benutzer")
            break
        except Exception as e:
            print(f"\n❌ Fehler: {e}")
            print("Versuche es erneut...\n")


def main():
    """Hauptfunktion."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Chat mit Quittungen aus DB via lokales LLM")
    parser.add_argument("--load-rag", action="store_true", 
                       help="Lade Quittungen auch in RAG-DB (für semantische Suche)")
    parser.add_argument("--limit", type=int, default=None,
                       help="Limit Anzahl Quittungen (für Tests)")
    
    args = parser.parse_args()
    
    print("🔍 Lade Quittungen aus Datenbank...")
    receipts_data = load_receipts_from_db()
    
    if not receipts_data:
        print("❌ Keine Quittungen gefunden!")
        print("   Tipp: Führe zuerst backend/seed.py aus")
        sys.exit(1)
    
    if args.limit:
        receipts_data = receipts_data[:args.limit]
        print(f"📊 Limitiert auf {len(receipts_data)} Quittungen")
    
    print(f"✅ {len(receipts_data)} Quittungen geladen")
    
    # Optional: In RAG-DB laden
    if args.load_rag:
        print("\n🔄 Lade Quittungen in RAG-DB...")
        init_rag()
        
        for receipt, items in receipts_data:
            rag_receipt = convert_db_receipt_to_rag_receipt(receipt, items)
            receipt_id = f"db_{receipt.id}"
            add_receipt_to_rag(rag_receipt, receipt_id)
        
        print(f"✅ {len(receipts_data)} Quittungen in RAG-DB geladen")
        print("   (Semantische Suche jetzt verfügbar)")
    
    # Ollama Status prüfen
    print("\n🔍 Prüfe Ollama...")
    status = check_ollama_status()
    
    if not status.get("available", False):
        print("❌ Ollama ist nicht verfügbar!")
        print("   Stelle sicher, dass Ollama läuft:")
        print("   ollama serve")
        print("\n   Und dass die Modelle installiert sind:")
        print("   ollama pull llama3.2")
        sys.exit(1)
    
    print(f"✅ Ollama läuft - Modell: {status.get('chat_model', 'unbekannt')}")
    
    # Chat starten
    asyncio.run(chat_loop(receipts_data))


if __name__ == "__main__":
    main()


