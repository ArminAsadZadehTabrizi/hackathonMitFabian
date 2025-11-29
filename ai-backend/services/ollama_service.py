"""
Ollama Service - Lokales LLM für Quittungs-Extraktion
"""
import ollama
import base64
import json
import re
from typing import Optional, Dict
from pathlib import Path

from config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_CHAT_MODEL
from models.receipt import Receipt, LineItem
from services.receipt_validator import validate_receipt, fix_receipt


# Ollama Client initialisieren
client = ollama.Client(host=OLLAMA_HOST)


EXTRACTION_PROMPT = """Du bist ein Experte für das Auslesen von Quittungen und Rechnungen.
Analysiere dieses Bild einer Quittung sehr sorgfältig und extrahiere ALLE sichtbaren Informationen.

Antworte NUR mit einem gültigen JSON-Objekt in diesem EXAKTEN Format (keine anderen Texte, keine Erklärungen!):
{
    "vendor_name": "Name des Geschäfts oder Restaurants",
    "vendor_address": "Vollständige Adresse falls sichtbar, sonst null",
    "date": "YYYY-MM-DD Format (z.B. 2024-01-15)",
    "total": 123.45,
    "subtotal": 100.00,
    "tax": 23.45,
    "tax_rate": 19.0,
    "currency": "EUR",
    "payment_method": "Karte/Bar/Kreditkarte/etc oder null",
    "line_items": [
        {
            "description": "Vollständiger Produktname wie auf der Quittung",
            "quantity": 2,
            "unit_price": 5.00,
            "total_price": 10.00,
            "category": "Lebensmittel/Getränke/Alkohol/Essen/Bürobedarf/Elektronik/Möbel/Kraftstoff/Sonstiges"
        }
    ],
    "category": "Restaurant/Supermarkt/Tankstelle/Café/Bürobedarf/Elektronik/Möbel/Online Shopping/Sonstiges"
}

KRITISCHE REGELN:
1. Alle Zahlen müssen als DEZIMALZAHLEN sein (nicht als String, z.B. 12.50 nicht "12,50")
2. Datum MUSS im ISO-Format YYYY-MM-DD sein (z.B. 2024-01-15)
3. quantity ist die ANZAHL der gekauften Einheiten (z.B. 2 Flaschen = quantity: 2)
4. total_price ist der GESAMTPREIS für diese quantity (z.B. 2 Flaschen à 5€ = total_price: 10.00)
5. unit_price ist der EINZELPREIS pro Einheit (z.B. 5.00)
6. Versuche JEDE einzelne Position aufzulisten - nicht zusammenfassen!
7. Falls etwas nicht lesbar ist, setze null (nicht 0 oder leerer String)
8. Kategorien müssen aus der Liste sein: Lebensmittel, Getränke, Alkohol, Essen, Bürobedarf, Elektronik, Möbel, Kraftstoff, Sonstiges
9. Prüfe dass total = Summe aller line_items.total_price (wenn subtotal vorhanden)
10. JSON muss gültig sein - keine Kommentare, keine Trailing Commas!

WICHTIG: Antworte NUR mit dem JSON-Objekt, keine zusätzlichen Texte davor oder danach!
"""


async def extract_receipt_from_image(
    image_path: Optional[str] = None,
    image_base64: Optional[str] = None
) -> Receipt:
    """
    Extrahiert Quittungsdaten aus einem Bild mit Ollama Vision Model.
    
    Args:
        image_path: Pfad zum Bild
        image_base64: Base64-kodiertes Bild
    
    Returns:
        Receipt: Strukturierte Quittungsdaten
    """
    # Bild vorbereiten
    if image_path:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
    elif image_base64:
        image_data = image_base64
    else:
        raise ValueError("Entweder image_path oder image_base64 muss angegeben werden")
    
    # Ollama Vision Model aufrufen (mit Retry-Logik)
    max_retries = 3
    data = None
    response_text = None
    
    for attempt in range(max_retries):
        try:
            response = client.chat(
                model=OLLAMA_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": EXTRACTION_PROMPT,
                        "images": [image_data]
                    }
                ],
                options={
                    "temperature": 0.1,  # Niedrige Temperatur für präzisere Ergebnisse
                    "num_predict": 2000  # Genug Tokens für vollständige Antwort
                }
            )
            
            # Response parsen
            response_text = response["message"]["content"]
            
            # JSON aus Response extrahieren (verschiedene Formate)
            json_str = None
            
            # Versuche 1: Markdown Code Block
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Versuche 2: Code Block ohne "json"
                json_match = re.search(r'```\s*(.*?)\s*```', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Versuche 3: Direktes JSON (finde erste { bis letzte })
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                    else:
                        json_str = response_text
            
            # Bereinige JSON-String
            json_str = json_str.strip()
            # Entferne mögliche Kommentare
            json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
            json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
            
            data = json.loads(json_str)
            break  # Erfolgreich geparst
            
        except json.JSONDecodeError as e:
            if attempt < max_retries - 1:
                print(f"⚠️  JSON Parse Fehler (Versuch {attempt + 1}/{max_retries}): {e}")
                print(f"   Versuche erneut...")
                continue
            else:
                print(f"❌ JSON Parse Fehler nach {max_retries} Versuchen: {e}")
                print(f"   Response war: {response_text[:500]}...")
                raise
    
    if data is None:
        raise ValueError("Konnte JSON nicht parsen nach mehreren Versuchen")
    
    try:
        
        # LineItems konvertieren
        line_items = []
        for item in data.get("line_items", []):
            line_items.append(LineItem(**item))
        
        receipt = Receipt(
            vendor_name=data.get("vendor_name", "Unbekannt"),
            vendor_address=data.get("vendor_address"),
            date=data.get("date"),
            total=float(data.get("total", 0)) if data.get("total") else None,
            subtotal=float(data.get("subtotal")) if data.get("subtotal") else None,
            tax=float(data.get("tax")) if data.get("tax") else None,
            tax_rate=float(data.get("tax_rate")) if data.get("tax_rate") else None,
            currency=data.get("currency", "EUR"),
            payment_method=data.get("payment_method"),
            line_items=line_items,
            category=data.get("category"),
            image_path=image_path,
            raw_text=response_text
        )
        
        # Validierung und Auto-Korrektur
        validation = validate_receipt(receipt)
        if validation["warnings"]:
            print(f"⚠️  Validierungswarnungen: {len(validation['warnings'])}")
            for warning in validation["warnings"][:3]:  # Zeige max 3 Warnungen
                print(f"   - {warning}")
        
        # Auto-Fix anwenden
        receipt = fix_receipt(receipt, apply_corrections=True)
        
        return receipt
        
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"❌ Fehler beim Verarbeiten der Quittung: {e}")
        print(f"   Response war: {response_text[:500] if response_text else 'Keine Response'}...")
        # Fallback: Leere Quittung mit raw text
        return Receipt(
            vendor_name="Parse Error",
            total=0,
            raw_text=response_text or "Keine Response vom LLM",
            image_path=image_path
        )


async def generate_chat_response(
    question: str,
    context: str,
    history: list = [],
    calculations: Optional[Dict] = None
) -> str:
    """
    Generiert eine Chat-Antwort basierend auf dem Kontext (RAG).
    
    Args:
        question: Die Benutzerfrage
        context: Relevante Quittungsdaten als Kontext
        history: Chat-Verlauf
        calculations: Optional - bereits berechnete präzise Zahlen (Python)
    
    Returns:
        str: Die generierte Antwort
    """
    # System Prompt with precise calculations (bilingual)
    if calculations:
        calc_text = "\n\n" + "="*60 + "\n"
        calc_text += "📊 PRECISE CALCULATIONS (Python - 100% correct!)\n"
        calc_text += "="*60 + "\n\n"
        
        # Extract the main result
        result = calculations.get('result', {})
        main_total = result.get('total', 0)
        main_count = result.get('count', 0)
        main_avg = result.get('average', 0)
        main_filter = result.get('filter', 'all receipts')
        
        # Main numbers - CRITICAL for LLM
        calc_text += f"🎯 MAIN RESULTS (use EXACTLY these numbers!):\n"
        calc_text += f"   Gesamtbetrag/Total: {main_total}€\n"
        calc_text += f"   Anzahl/Count: {main_count} receipts\n"
        calc_text += f"   Durchschnitt/Average: {main_avg}€\n"
        calc_text += f"   Filter: {main_filter}\n\n"
        
        # Min/Max
        min_data = result.get('min', {})
        max_data = result.get('max', {})
        if min_data.get('vendor'):
            calc_text += f"📉 Smallest receipt: {min_data.get('total', 0)}€ ({min_data.get('vendor', 'Unknown')})\n"
        if max_data.get('vendor'):
            calc_text += f"📈 Largest receipt: {max_data.get('total', 0)}€ ({max_data.get('vendor', 'Unknown')})\n"
        calc_text += "\n"
        
        # Top Vendors
        top_vendors = result.get('top_vendors', [])
        if top_vendors:
            calc_text += f"🏪 Top Vendors:\n"
            for i, v in enumerate(top_vendors[:3], 1):
                calc_text += f"   {i}. {v.get('vendor', 'Unknown')}: {v.get('total', 0)}€\n"
            calc_text += "\n"
        
        # Top Categories
        top_cats = result.get('top_categories', [])
        if top_cats:
            calc_text += f"📁 Top Categories:\n"
            for i, c in enumerate(top_cats[:3], 1):
                calc_text += f"   {i}. {c.get('category', 'Unknown')}: {c.get('total', 0)}€\n"
            calc_text += "\n"
        
        # Receipt details
        receipts = result.get('receipts', [])
        if receipts:
            calc_text += f"📄 Receipt Details (first {min(len(receipts), 10)}):\n"
            for i, r in enumerate(receipts[:10], 1):
                flags = []
                if r.get('flags', {}).get('duplicate'): flags.append('⚠️DUP')
                if r.get('flags', {}).get('suspicious'): flags.append('🚨SUS')
                if r.get('flags', {}).get('missing_vat'): flags.append('❌VAT')
                if r.get('flags', {}).get('math_error'): flags.append('🔢ERR')
                flag_str = ' '.join(flags) if flags else ''
                calc_text += f"   {i}. {r.get('vendor', 'Unknown')}: {r.get('total', 0)}€ ({r.get('category', '')}) {flag_str}\n"
            calc_text += "\n"
        
        calc_text += "="*60 + "\n"
        calc_text += "⚠️ USE THE NUMBER AFTER 'Gesamtbetrag/Total:' AS YOUR ANSWER!\n"
        calc_text += "="*60 + "\n"
        
        # Debug: Show calculations
        print(f"📊 Precise calculations for Ollama:")
        print(f"   Total: {main_total}€, Count: {main_count}, Avg: {main_avg}€")
    else:
        calc_text = ""
    
    # Detect language of question - check for German words first (more specific)
    german_words = ['wie', 'viel', 'zeig', 'alle', 'quittungen', 'ausgaben', 'habe', 'ich', 'und', 'von', 'für', 'der', 'die', 'das', 'ein', 'eine', 'über', 'unter', 'euro', 'insgesamt', 'welche', 'wann', 'wo', 'wer', 'warum', 'gib', 'mir', 'finde', 'suche']
    english_words = ['how', 'what', 'which', 'show', 'find', 'spent', 'much', 'many', 'receipts', 'the', 'did', 'does', 'have', 'has', 'where', 'when', 'who', 'why', 'total', 'from', 'all']
    
    question_lower = question.lower()
    german_count = sum(1 for word in german_words if word in question_lower)
    english_count = sum(1 for word in english_words if word in question_lower)
    
    is_english = english_count > german_count
    
    if is_english:
        system_prompt = f"""You are an expert financial auditor AI assistant for a small business bookkeeping system.

YOUR ROLE: Answer questions about receipts and expenses accurately and helpfully.

AVAILABLE DATA:
{context}
{calc_text}

INSTRUCTIONS:
1. LANGUAGE: Respond in English
2. USE PRE-CALCULATED NUMBERS: The "Gesamtbetrag/Total" value is already calculated by Python and is 100% accurate. USE IT DIRECTLY.
3. FORMAT: Start with the main answer (total amount), then provide details
4. CURRENCY: Format as €X,XXX.XX (e.g., €11,456.97)
5. BE SPECIFIC: Always mention the exact count and amounts

EXAMPLE RESPONSES:
- "The total spending is €11,456.97 across 50 receipts."
- "I found 6 receipts from Saturn totaling €1,694.20."
- "Electronics expenses amount to €2,340.00 from 8 receipts."

If you see "Gesamtbetrag/Total: 1234.56€" in the calculations, your answer should include "€1,234.56" - do not recalculate!
"""
    else:
        system_prompt = f"""Du bist ein Experte für Finanz-Auditing und ein KI-Assistent für ein Buchhaltungssystem.

DEINE ROLLE: Beantworte Fragen zu Quittungen und Ausgaben präzise und hilfreich.

VERFÜGBARE DATEN:
{context}
{calc_text}

ANWEISUNGEN:
1. SPRACHE: Antworte auf Deutsch
2. NUTZE VORBERECHNETE ZAHLEN: Der "Gesamtbetrag/Total" Wert wurde bereits von Python berechnet und ist 100% korrekt. NUTZE IHN DIREKT.
3. FORMAT: Beginne mit der Hauptantwort (Gesamtbetrag), dann Details
4. WÄHRUNG: Formatiere als X.XXX,XX€ (z.B. 11.456,97€)
5. SEI SPEZIFISCH: Nenne immer die genaue Anzahl und Beträge

BEISPIEL-ANTWORTEN:
- "Die Gesamtausgaben betragen 11.456,97€ aus 50 Quittungen."
- "Ich habe 6 Quittungen von Saturn gefunden mit einem Gesamtbetrag von 1.694,20€."
- "Die Ausgaben für Elektronik belaufen sich auf 2.340,00€ aus 8 Quittungen."

Wenn du "Gesamtbetrag/Total: 1234.56€" in den Berechnungen siehst, sollte deine Antwort "1.234,56€" enthalten - nicht selbst rechnen!
"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # History hinzufügen
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    
    # Aktuelle Frage
    messages.append({"role": "user", "content": question})
    
    # Chat mit optimierten Parametern
    print(f"🤖 Ollama Request:")
    print(f"   Model: {OLLAMA_CHAT_MODEL}")
    print(f"   Host: {OLLAMA_HOST}")
    print(f"   Question: {question[:100]}...")
    print(f"   Context length: {len(context)} chars")
    print(f"   Has calculations: {calculations is not None}")
    
    try:
        response = client.chat(
            model=OLLAMA_CHAT_MODEL,
            messages=messages,
            options={
                "temperature": 0.1,      # Sehr niedrig für konsistente, präzise Antworten
                "num_predict": 1200,     # Mehr Tokens für vollständige Antworten
                "top_p": 0.9,            # Nucleus sampling für bessere Qualität
                "repeat_penalty": 1.1,   # Verhindert Wiederholungen
                "num_ctx": 4096,         # Größerer Context-Window
            }
        )
        
        answer = response["message"]["content"]
        print(f"✅ Ollama Response received ({len(answer)} chars)")
        print(f"   Response preview: {answer[:150]}...")
        
        return answer
    except Exception as e:
        print(f"❌ Ollama Error: {e}")
        raise


def check_ollama_status() -> dict:
    """Prüft ob Ollama läuft und welche Modelle verfügbar sind."""
    try:
        # Prüfe ob Ollama erreichbar ist
        import requests
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
        if response.status_code == 200:
            data = response.json()
            model_list = []
            if "models" in data:
                for m in data["models"]:
                    if isinstance(m, dict) and "name" in m:
                        model_list.append(m["name"])
                    elif isinstance(m, str):
                        model_list.append(m)
            
            return {
                "status": "online",
                "models": model_list,
                "host": OLLAMA_HOST,
                "chat_model": OLLAMA_CHAT_MODEL,
                "vision_model": OLLAMA_MODEL
            }
        else:
            return {
                "status": "error",
                "error": f"HTTP {response.status_code}"
            }
    except Exception as e:
        return {
            "status": "offline",
            "error": str(e),
            "host": OLLAMA_HOST
        }

