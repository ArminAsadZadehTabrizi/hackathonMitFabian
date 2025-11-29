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
    # System Prompt mit präzisen Berechnungen
    if calculations:
        calc_text = "\n\n" + "="*60 + "\n"
        calc_text += "⚠️  KRITISCH: PRÄZISE BERECHNUNGEN (Python - 100% korrekt!)\n"
        calc_text += "="*60 + "\n\n"
        
        # Extrahiere die EINE relevante Zahl
        main_total = None
        main_count = None
        main_filter = None
        
        for key, value in calculations.items():
            if isinstance(value, dict) and "total" in value:
                main_total = value['total']
                main_count = value.get('count', 0)
                main_filter = value.get('filter', key.replace('total_', '').replace('_', ' ').title())
                
                # Zeige die EINE wichtige Zahl ganz klar
                calc_text += f"🎯 FINALE ANTWORT (nutze EXAKT diese Zahl!):\n"
                calc_text += f"   Gesamtbetrag: {main_total}€\n"
                calc_text += f"   Anzahl Quittungen: {main_count}\n"
                calc_text += f"   Filter: {main_filter}\n\n"
                
                # Details (falls vorhanden)
                if "receipts" in value and len(value["receipts"]) > 0:
                    calc_text += f"Details der ersten 5 Quittungen:\n"
                    for i, item in enumerate(value["receipts"][:5], 1):
                        calc_text += f"  {i}. {item.get('vendor', 'Unknown')}: {item.get('total', 0)}€\n"
                    calc_text += "\n"
                
                break  # Nur die erste (wichtigste) Berechnung
        
        calc_text += "="*60 + "\n"
        calc_text += "⚠️  DIE ZAHL NACH 'Gesamtbetrag:' IST DIE ANTWORT!\n"
        calc_text += "⚠️  KOPIERE SIE EXAKT - RECHNE NICHT SELBST!\n"
        calc_text += "="*60 + "\n"
        
        # Debug: Zeige Berechnungen
        print(f"📊 Präzise Berechnungen für Ollama:")
        print(f"   result: {main_total}€")
    else:
        calc_text = ""
    
    system_prompt = f"""Du bist ein professioneller Finanz-Auditor und Buchhalter-Assistent.
Du analysierst Quittungen und beantwortest Fragen zu Ausgaben basierend auf den folgenden Daten.

VERFÜGBARE QUITTUNGSDATEN:
{context}
{calc_text}

⚠️  KRITISCHE REGELN - BITTE GENAU BEFOLGEN:
1. Antworte IMMER auf Deutsch in einem professionellen, aber freundlichen Ton
2. ⚠️  ABSOLUT KRITISCH: Wenn du "GESAMT: X€" in den PRÄZISEN BEREICHNUNGEN siehst, ist das die FINALE ANTWORT!
3. ⚠️  Kopiere diese Zahl EXAKT - rechne NICHT selbst nach! Die Zahl ist bereits korrekt berechnet!
4. ⚠️  Wenn du mehrere "GESAMT:" Werte siehst, nutze den Wert der zur Frage passt
5. ⚠️  NIE selbst rechnen - immer die berechneten Zahlen verwenden!
6. Formatiere Geldbeträge immer mit € Symbol und Komma als Dezimaltrennzeichen (z.B. 11.456,97€)
7. Sei präzise und konkret - nenne konkrete Zahlen und Beträge
8. Wenn mehrere Quittungen gefunden wurden, erwähne die Anzahl
9. Wenn präzise Berechnungen vorhanden sind, beginne deine Antwort IMMER mit der Gesamtsumme
10. Strukturiere deine Antwort klar: zuerst die Hauptantwort, dann Details

FORMAT-VORLAGE FÜR ANTWORTEN:
- "Basierend auf den präzisen Berechnungen beträgt der Gesamtbetrag [HIER EXAKT DIE ZAHL AUS GESAMT EINFÜGEN]€. Dies setzt sich zusammen aus [ANZAHL] Quittungen."
- "Ich habe [ANZAHL] Quittungen von [VENDOR] gefunden mit einem Gesamtbetrag von [EXAKT DIE ZAHL AUS GESAMT]€."
- "Die Ausgaben für [KATEGORIE] betragen insgesamt [EXAKT DIE ZAHL AUS GESAMT]€ aus [ANZAHL] Quittungen."

WICHTIG: Wenn du "GESAMT: 11456.97€" siehst, dann schreibe EXAKT: "11.456,97€" (mit Punkt als Tausendertrennzeichen und Komma als Dezimaltrennzeichen).
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
                "temperature": 0.3,  # Niedrigere Temperatur für präzisere Antworten
                "num_predict": 800   # Mehr Tokens für vollständige Antworten
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

