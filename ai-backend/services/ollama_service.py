"""
Ollama Service - Lokales LLM für Quittungs-Extraktion
"""
import ollama
import base64
import json
import re
from typing import Optional
from pathlib import Path

from config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_CHAT_MODEL
from models.receipt import Receipt, LineItem


# Ollama Client initialisieren
client = ollama.Client(host=OLLAMA_HOST)


EXTRACTION_PROMPT = """Du bist ein Experte für das Auslesen von Quittungen und Rechnungen.
Analysiere dieses Bild einer Quittung und extrahiere ALLE Informationen.

Antworte NUR mit einem JSON-Objekt in diesem Format (keine andere Text!):
{
    "vendor_name": "Name des Geschäfts",
    "vendor_address": "Adresse falls sichtbar",
    "date": "YYYY-MM-DD Format",
    "total": 123.45,
    "subtotal": 100.00,
    "tax": 23.45,
    "tax_rate": 19.0,
    "currency": "EUR",
    "payment_method": "Karte/Bar/etc",
    "line_items": [
        {
            "description": "Produktname",
            "quantity": 1,
            "unit_price": 10.00,
            "total_price": 10.00,
            "category": "Lebensmittel/Getränke/Büro/etc"
        }
    ],
    "category": "Restaurant/Supermarkt/Tankstelle/etc"
}

WICHTIG:
- Alle Zahlen als Dezimalzahlen (nicht als String)
- Datum im ISO-Format YYYY-MM-DD
- Falls etwas nicht lesbar ist, setze null
- Versuche JEDE Position einzeln aufzulisten
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
    
    # Ollama Vision Model aufrufen
    response = client.chat(
        model=OLLAMA_MODEL,
        messages=[
            {
                "role": "user",
                "content": EXTRACTION_PROMPT,
                "images": [image_data]
            }
        ]
    )
    
    # Response parsen
    response_text = response["message"]["content"]
    
    # JSON aus Response extrahieren (manchmal mit Markdown Code Blocks)
    json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Versuche direkt als JSON zu parsen
        json_str = response_text
    
    try:
        data = json.loads(json_str)
        
        # LineItems konvertieren
        line_items = []
        for item in data.get("line_items", []):
            line_items.append(LineItem(**item))
        
        return Receipt(
            vendor_name=data.get("vendor_name", "Unbekannt"),
            vendor_address=data.get("vendor_address"),
            date=data.get("date"),
            total=float(data.get("total", 0)),
            subtotal=data.get("subtotal"),
            tax=data.get("tax"),
            tax_rate=data.get("tax_rate"),
            currency=data.get("currency", "EUR"),
            payment_method=data.get("payment_method"),
            line_items=line_items,
            category=data.get("category"),
            image_path=image_path,
            raw_text=response_text
        )
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        print(f"Response was: {response_text}")
        # Fallback: Leere Quittung mit raw text
        return Receipt(
            vendor_name="Parse Error",
            total=0,
            raw_text=response_text,
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
        calc_text = "\n\n═══════════════════════════════════════════════════\n"
        calc_text += "⚠️  WICHTIG: PRÄZISE BEREICHNUNGEN (bereits berechnet in Python):\n"
        calc_text += "═══════════════════════════════════════════════════\n"
        calc_text += "Nutze diese Zahlen EXAKT! Rechne NICHT selbst nach!\n\n"
        
        for key, value in calculations.items():
            if isinstance(value, dict):
                if "total" in value:
                    calc_text += f"📊 {key.replace('total_', '').upper()}:\n"
                    calc_text += f"   GESAMT: {value['total']}€\n"
                    if "items" in value and value["items"]:
                        calc_text += f"   Anzahl Items: {len(value['items'])}\n"
                        if "vendors" in value:
                            calc_text += f"   Aufgeteilt auf:\n"
                            for vendor, amount in value["vendors"].items():
                                calc_text += f"     - {vendor}: {amount}€\n"
                    calc_text += "\n"
                elif "by_category" in key:
                    calc_text += f"📊 Ausgaben nach Kategorie:\n"
                    for cat, total in sorted(value.items(), key=lambda x: x[1], reverse=True):
                        calc_text += f"   {cat}: {total}€\n"
                    calc_text += "\n"
            elif isinstance(value, list):
                calc_text += f"📊 {key.replace('_', ' ').upper()}:\n"
                for i, item in enumerate(value, 1):
                    if isinstance(item, dict):
                        calc_text += f"   {i}. {item.get('vendor', 'Unbekannt')}: {item.get('total', 0)}€ ({item.get('category', '')})\n"
                calc_text += "\n"
        
        calc_text += "═══════════════════════════════════════════════════\n"
        calc_text += "⚠️  KRITISCH: Die Zahl nach 'GESAMT:' ist die FINALE ANTWORT!\n"
        calc_text += "⚠️  Kopiere diese Zahl EXAKT in deine Antwort - rechne NICHT!\n"
        calc_text += "═══════════════════════════════════════════════════\n"
    else:
        calc_text = ""
    
    system_prompt = f"""Du bist ein hilfreicher Assistent für Finanz-Analysen.
Du beantwortest Fragen zu Quittungen und Ausgaben basierend auf den folgenden Daten.

VERFÜGBARE DATEN (Rohdaten):
{context}
{calc_text}

REGELN:
- Antworte auf Deutsch
- ⚠️  KRITISCH: Wenn du "GESAMT: X€" in den PRÄZISEN BEREICHNUNGEN siehst, ist das die FINALE ANTWORT!
- ⚠️  Kopiere diese Zahl EXAKT - rechne NICHT selbst nach!
- ⚠️  Die Zahl ist bereits korrekt berechnet in Python - vertraue darauf!
- Formatiere Geldbeträge mit € Symbol
- Sei freundlich und hilfreich
- Erkläre die Ergebnisse klar und strukturiert
- Wenn präzise Berechnungen vorhanden sind, beginne deine Antwort IMMER mit: "Basierend auf den präzisen Berechnungen beträgt der Gesamtbetrag [HIER DIE ZAHL AUS GESAMT EINFÜGEN]€"
- Beispiel: Wenn "GESAMT: 43.98€" steht, dann schreibe: "Basierend auf den präzisen Berechnungen beträgt der Gesamtbetrag 43.98€"
"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # History hinzufügen
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    
    # Aktuelle Frage
    messages.append({"role": "user", "content": question})
    
    response = client.chat(
        model=OLLAMA_CHAT_MODEL,
        messages=messages
    )
    
    return response["message"]["content"]


def check_ollama_status() -> dict:
    """Prüft ob Ollama läuft und welche Modelle verfügbar sind."""
    try:
        models = client.list()
        model_list = []
        if isinstance(models, dict) and "models" in models:
            for m in models["models"]:
                if isinstance(m, dict) and "name" in m:
                    model_list.append(m["name"])
                elif isinstance(m, str):
                    model_list.append(m)
        return {
            "status": "online",
            "models": model_list
        }
    except Exception as e:
        return {
            "status": "offline",
            "error": str(e)
        }

