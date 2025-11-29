#!/usr/bin/env python3
"""
🧾 CORD Quittungen mit lokalem LLM analysieren

Lädt CORD-Bilder von Hugging Face, analysiert sie mit Ollama (llama3.2-vision),
und sendet die Ergebnisse an http://localhost:8000/api/ingest

Verwendung:
    python analyze_cord_receipts.py --limit 5
"""

import os
import io
import json
import base64
import argparse
import requests
from datetime import datetime
from pathlib import Path

# Hugging Face datasets
from datasets import load_dataset

# Ollama
import ollama

# Konfiguration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = "llama3.2-vision"
API_INGEST_URL = "http://localhost:8000/api/ingest"
SAVE_PATH = Path(__file__).parent / "data" / "cord"


EXTRACTION_PROMPT = """Du bist ein Experte für das Auslesen von Quittungen und Rechnungen.
Analysiere dieses Bild einer Quittung sehr sorgfältig und extrahiere ALLE sichtbaren Informationen.

Antworte NUR mit einem gültigen JSON-Objekt in diesem EXAKTEN Format (keine anderen Texte!):
{
    "vendor_name": "Name des Geschäfts",
    "date": "2023-11-29T10:00:00",
    "total_amount": 123.45,
    "tax_amount": 19.50,
    "currency": "EUR",
    "category": "Restaurant/Supermarkt/Tankstelle/Café/Hardware/Sonstiges",
    "items": [
        {"description": "Produktname", "amount": 10.00}
    ]
}

REGELN:
1. Alle Zahlen als DEZIMALZAHLEN (z.B. 12.50, nicht "12,50")
2. Datum im ISO-Format: YYYY-MM-DDTHH:MM:SS
3. Falls Datum nicht lesbar: aktuelles Datum verwenden
4. Falls MwSt nicht erkennbar: tax_amount = 0
5. currency = "EUR" oder "USD" je nach Quittung
6. Jede Position als separates Item in "items"
7. NUR das JSON ausgeben, keine Erklärungen!
"""


def ensure_dirs():
    """Erstellt notwendige Ordner."""
    (SAVE_PATH / "images").mkdir(parents=True, exist_ok=True)
    (SAVE_PATH / "results").mkdir(parents=True, exist_ok=True)


def image_to_base64(image):
    """Konvertiert PIL Image zu Base64."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def analyze_with_ollama(image_base64: str) -> dict:
    """
    Analysiert ein Bild mit dem lokalen Ollama LLM.
    
    Returns:
        dict: Extrahierte Quittungsdaten
    """
    client = ollama.Client(host=OLLAMA_HOST)
    
    try:
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT,
                    "images": [image_base64]
                }
            ],
            options={
                "temperature": 0.1,
                "num_predict": 2000
            }
        )
        
        response_text = response["message"]["content"]
        
        # JSON extrahieren
        import re
        
        # Versuche verschiedene Formate
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'```\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = response_text
        
        # Bereinigen
        json_str = json_str.strip()
        json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
        
        data = json.loads(json_str)
        return data
        
    except json.JSONDecodeError as e:
        print(f"    ⚠️  JSON Parse Fehler: {e}")
        return None
    except Exception as e:
        print(f"    ❌ Ollama Fehler: {e}")
        return None


def send_to_api(receipt_data: dict) -> bool:
    """
    Sendet Quittungsdaten an /api/ingest/db
    
    Args:
        receipt_data: Dict im Format für /api/ingest/db
    
    Returns:
        bool: True wenn erfolgreich
    """
    try:
        response = requests.post(
            API_INGEST_URL,
            json=receipt_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            return True
        else:
            print(f"    ⚠️  API Error {response.status_code}: {response.text[:100]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"    ❌ Keine Verbindung zu {API_INGEST_URL}")
        return False
    except Exception as e:
        print(f"    ❌ Request Fehler: {e}")
        return False


def process_cord_receipts(limit: int = 5):
    """
    Hauptfunktion: Lädt CORD, analysiert mit LLM, sendet an API.
    """
    print("=" * 60)
    print("🧾 CORD Quittungen mit lokalem LLM analysieren")
    print("=" * 60)
    print()
    
    ensure_dirs()
    
    # 1. Ollama prüfen
    print("🔍 Prüfe Ollama-Verbindung...")
    try:
        import requests as req
        resp = req.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        models_data = resp.json()
        model_names = [m.get('name', '') for m in models_data.get('models', [])]
        
        if not any(OLLAMA_MODEL in name for name in model_names):
            print(f"❌ Model '{OLLAMA_MODEL}' nicht gefunden!")
            print(f"   Verfügbare Models: {model_names}")
            print(f"   Installiere mit: ollama pull {OLLAMA_MODEL}")
            return
        print(f"✅ Ollama läuft, Model '{OLLAMA_MODEL}' verfügbar")
    except Exception as e:
        print(f"❌ Ollama nicht erreichbar: {e}")
        print("   Starte Ollama mit: ollama serve")
        return
    
    # 2. API prüfen
    print("🔍 Prüfe API-Verbindung...")
    try:
        health = requests.get("http://localhost:8000/api/health", timeout=5)
        if health.status_code == 200:
            print("✅ API läuft auf http://localhost:8000")
            api_available = True
        else:
            print("⚠️  API antwortet nicht korrekt")
            api_available = False
    except:
        print("⚠️  API nicht erreichbar - Ergebnisse werden nur lokal gespeichert")
        api_available = False
    
    print()
    
    # 3. CORD Dataset laden
    print("📥 Lade CORD-v2 Dataset von Hugging Face...")
    print("   (Beim ersten Mal wird heruntergeladen)")
    
    try:
        dataset = load_dataset("naver-clova-ix/cord-v2", split="train")
        print(f"✅ {len(dataset)} Quittungen verfügbar")
    except Exception as e:
        print(f"❌ Fehler beim Laden: {e}")
        return
    
    print()
    print(f"🔄 Analysiere {limit} Quittungen mit {OLLAMA_MODEL}...")
    print()
    
    # 4. Quittungen verarbeiten
    success_count = 0
    api_success = 0
    results = []
    
    for idx in range(min(limit, len(dataset))):
        entry = dataset[idx]
        print(f"[{idx + 1}/{limit}] Analysiere Quittung...")
        
        # Bild zu Base64
        image = entry.get('image')
        if not image:
            print("    ⚠️  Kein Bild vorhanden, überspringe")
            continue
        
        image_base64 = image_to_base64(image)
        
        # Bild speichern
        image_path = SAVE_PATH / "images" / f"cord_{idx}.png"
        image.save(str(image_path))
        
        # Mit Ollama analysieren
        print(f"    🧠 LLM analysiert...", end=" ", flush=True)
        receipt_data = analyze_with_ollama(image_base64)
        
        if not receipt_data:
            print("❌ Fehlgeschlagen")
            continue
        
        print("✅")
        
        # Daten validieren und normalisieren
        vendor = receipt_data.get("vendor_name", "Unknown")
        
        # Datum formatieren
        date_str = receipt_data.get("date", "")
        if not date_str or date_str == "null":
            date_str = datetime.now().isoformat()
        elif "T" not in date_str:
            date_str = f"{date_str}T00:00:00"
        
        # Payload für API erstellen
        api_payload = {
            "vendor_name": vendor,
            "date": date_str,
            "total_amount": float(receipt_data.get("total_amount", 0) or 0),
            "tax_amount": float(receipt_data.get("tax_amount", 0) or 0),
            "currency": receipt_data.get("currency", "EUR"),
            "category": receipt_data.get("category", "Sonstiges"),
            "items": [
                {
                    "description": item.get("description", "Item"),
                    "amount": float(item.get("amount", 0) or 0)
                }
                for item in receipt_data.get("items", [])
                if item.get("description")
            ]
        }
        
        # Fallback: Wenn keine Items, aber Total vorhanden
        if not api_payload["items"] and api_payload["total_amount"] > 0:
            api_payload["items"] = [
                {"description": "Gesamtbetrag", "amount": api_payload["total_amount"]}
            ]
        
        print(f"    📝 Vendor: {vendor[:40]}")
        print(f"    💰 Total: {api_payload['total_amount']:.2f} {api_payload['currency']}")
        print(f"    📦 Items: {len(api_payload['items'])}")
        
        # Ergebnis speichern
        result_path = SAVE_PATH / "results" / f"cord_{idx}.json"
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(api_payload, f, ensure_ascii=False, indent=2)
        
        results.append(api_payload)
        success_count += 1
        
        # An API senden
        if api_available:
            print(f"    📤 Sende an API...", end=" ", flush=True)
            if send_to_api(api_payload):
                print("✅")
                api_success += 1
            else:
                print("❌")
        
        print()
    
    # 5. Zusammenfassung
    print("=" * 60)
    print("📊 ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"   Analysiert:        {limit}")
    print(f"   Erfolgreich:       {success_count}")
    print(f"   An API gesendet:   {api_success}")
    print()
    print(f"📁 Ergebnisse in: {SAVE_PATH}")
    print(f"   └── images/    {success_count} Bilder")
    print(f"   └── results/   {success_count} JSON-Dateien")
    print()
    
    # Beispiel-Output zeigen
    if results:
        print("📋 Beispiel JSON (letzte Quittung):")
        print("-" * 40)
        print(json.dumps(results[-1], indent=2, ensure_ascii=False))
    
    print()
    print("✅ Fertig!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CORD Receipts mit LLM analysieren")
    parser.add_argument("--limit", type=int, default=5,
                        help="Anzahl der zu analysierenden Quittungen (default: 5)")
    args = parser.parse_args()
    
    process_cord_receipts(limit=args.limit)

