#!/usr/bin/env python3
"""
🗂️ CORD Dataset Loader - Lädt CORD-v2 von Hugging Face

Dieses Script:
1. Lädt den CORD-v2 Datensatz automatisch von Hugging Face
2. Extrahiert Quittungsdaten und Bilder
3. Speichert sie im ai-backend/data/cord/ Ordner
4. Sendet die Daten an das AI-Backend

Verwendung:
    python load_cord_huggingface.py
    
    # Oder mit Limit:
    python load_cord_huggingface.py --limit 20
"""

import os
import json
import base64
import argparse
import requests
from pathlib import Path
from datetime import datetime

try:
    from datasets import load_dataset
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("⚠️  'datasets' library nicht installiert!")
    print("   Installiere mit: pip install datasets")


# Konfiguration
API_BASE_URL = "http://localhost:8000"
CORD_SAVE_PATH = Path(__file__).parent / "data" / "cord"
DEFAULT_LIMIT = 50


def ensure_dirs():
    """Erstellt notwendige Ordner."""
    (CORD_SAVE_PATH / "images").mkdir(parents=True, exist_ok=True)
    (CORD_SAVE_PATH / "annotations").mkdir(parents=True, exist_ok=True)
    print(f"📁 Ordner erstellt: {CORD_SAVE_PATH}")


def parse_date(date_str):
    """Parst Datum aus CORD-Format."""
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
    
    formats = [
        "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", 
        "%d/%m/%Y", "%m/%d/%Y", "%Y.%m.%d", "%d.%m.%Y"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            continue
    
    return datetime.now().strftime("%Y-%m-%d")


def extract_receipt_data(entry, idx):
    """
    Extrahiert Quittungsdaten aus einem CORD-Eintrag.
    
    Returns:
        dict: Receipt-Daten im API-Format
    """
    try:
        # Ground Truth parsen
        gt = entry.get('ground_truth', {})
        if isinstance(gt, str):
            gt = json.loads(gt)
        
        gt_parse = gt.get('gt_parse', {})
        
        # Vendor Name
        vendor_name = "Unknown Vendor"
        store_info = gt_parse.get('store_info', {})
        if 'name' in store_info and isinstance(store_info['name'], dict):
            vendor_name = store_info['name'].get('text', vendor_name)
        
        # Datum
        date = None
        payment_info = gt_parse.get('payment_info', {})
        if 'date' in payment_info and isinstance(payment_info['date'], dict):
            date = payment_info['date'].get('text')
        if not date and 'date' in store_info and isinstance(store_info['date'], dict):
            date = store_info['date'].get('text')
        date = parse_date(date)
        
        # Total
        total_amount = 0.0
        total_info = gt_parse.get('total', {})
        if 'total_price' in total_info and isinstance(total_info['total_price'], dict):
            try:
                price_str = total_info['total_price'].get('price', '0')
                total_amount = float(str(price_str).replace(',', '.'))
            except (ValueError, TypeError):
                pass
        
        # Tax
        tax_amount = 0.0
        if 'tax' in total_info and isinstance(total_info['tax'], dict):
            try:
                tax_str = total_info['tax'].get('price', '0')
                tax_amount = float(str(tax_str).replace(',', '.'))
            except (ValueError, TypeError):
                pass
        
        # Line Items
        items = []
        menu_items = gt_parse.get('menu', [])
        for menu_item in menu_items:
            if not isinstance(menu_item, dict):
                continue
                
            description = "Unknown Item"
            amount = 0.0
            
            if 'nm' in menu_item and isinstance(menu_item['nm'], dict):
                description = menu_item['nm'].get('text', description)
            
            if 'price' in menu_item and isinstance(menu_item['price'], dict):
                try:
                    price_str = menu_item['price'].get('price', '0')
                    amount = float(str(price_str).replace(',', '.'))
                except (ValueError, TypeError):
                    pass
            
            if description and amount > 0:
                items.append({
                    "description": description,
                    "quantity": 1,
                    "total_price": amount,
                    "unit_price": amount,
                    "category": "Sonstiges"
                })
        
        # Fallback: Wenn keine Items, aber Total vorhanden
        if not items and total_amount > 0:
            items.append({
                "description": "Total Purchase",
                "quantity": 1,
                "total_price": total_amount,
                "unit_price": total_amount,
                "category": "Sonstiges"
            })
        
        return {
            "id": f"cord_{idx}",
            "vendor_name": vendor_name,
            "date": date,
            "total": total_amount,
            "subtotal": total_amount - tax_amount if tax_amount else None,
            "tax": tax_amount if tax_amount > 0 else None,
            "tax_rate": 19.0 if tax_amount > 0 else None,
            "currency": "EUR",
            "payment_method": None,
            "line_items": items,
            "category": guess_category(vendor_name),
            "raw_text": json.dumps(gt_parse, ensure_ascii=False)[:500]
        }
        
    except Exception as e:
        print(f"  ⚠️  Fehler beim Parsen: {e}")
        return None


def guess_category(vendor_name):
    """Rät die Kategorie basierend auf Vendor-Name."""
    vendor_lower = vendor_name.lower()
    
    if any(kw in vendor_lower for kw in ["restaurant", "cafe", "coffee", "pizza", "burger", "sushi", "bar"]):
        return "Restaurant"
    if any(kw in vendor_lower for kw in ["market", "grocery", "mart", "store"]):
        return "Supermarkt"
    if any(kw in vendor_lower for kw in ["gas", "fuel", "shell", "esso"]):
        return "Tankstelle"
    
    return "Sonstiges"


def save_image(entry, idx):
    """Speichert das Bild lokal."""
    try:
        image = entry.get('image')
        if image:
            image_path = CORD_SAVE_PATH / "images" / f"cord_{idx}.png"
            image.save(str(image_path))
            return str(image_path)
    except Exception as e:
        print(f"  ⚠️  Bild speichern fehlgeschlagen: {e}")
    return None


def save_annotation(receipt_data, idx):
    """Speichert die Annotation als JSON."""
    try:
        json_path = CORD_SAVE_PATH / "annotations" / f"cord_{idx}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(receipt_data, f, ensure_ascii=False, indent=2)
        return str(json_path)
    except Exception as e:
        print(f"  ⚠️  Annotation speichern fehlgeschlagen: {e}")
    return None


def send_to_api(receipt_data):
    """Sendet Quittung an das AI-Backend."""
    try:
        # An RAG-Endpoint senden
        response = requests.post(
            f"{API_BASE_URL}/api/receipt",
            json=receipt_data,
            timeout=10
        )
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False
    except Exception as e:
        print(f"  ⚠️  API-Fehler: {e}")
        return False


def load_cord_dataset(limit=DEFAULT_LIMIT):
    """
    Hauptfunktion: Lädt CORD von Hugging Face und verarbeitet es.
    """
    if not HF_AVAILABLE:
        print("❌ 'datasets' library nicht verfügbar!")
        print("   Installiere mit: pip install datasets")
        return
    
    print("=" * 60)
    print("🗂️  CORD-v2 Dataset Loader")
    print("=" * 60)
    print()
    
    # Ordner erstellen
    ensure_dirs()
    
    # Dataset laden
    print("📥 Lade CORD-v2 von Hugging Face...")
    print("   (Beim ersten Mal wird heruntergeladen, kann dauern...)")
    print()
    
    try:
        dataset = load_dataset("naver-clova-ix/cord-v2", split="train")
        print(f"✅ Dataset geladen: {len(dataset)} Quittungen verfügbar")
        print()
    except Exception as e:
        print(f"❌ Fehler beim Laden: {e}")
        return
    
    # API-Verbindung prüfen
    try:
        health = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
        api_available = health.status_code == 200
        print(f"🔗 API-Verbindung: {'✅ OK' if api_available else '❌ Nicht erreichbar'}")
    except:
        api_available = False
        print("🔗 API-Verbindung: ⚠️  Backend nicht gestartet")
    print()
    
    # Verarbeitung
    success_count = 0
    saved_images = 0
    saved_annotations = 0
    
    actual_limit = min(limit, len(dataset))
    print(f"📊 Verarbeite {actual_limit} von {len(dataset)} Quittungen...")
    print()
    
    for idx, entry in enumerate(dataset):
        if idx >= actual_limit:
            break
        
        print(f"[{idx + 1}/{actual_limit}] Verarbeite...", end=" ")
        
        # Daten extrahieren
        receipt_data = extract_receipt_data(entry, idx)
        
        if not receipt_data:
            print("❌ Fehler")
            continue
        
        # Bild speichern
        image_path = save_image(entry, idx)
        if image_path:
            receipt_data["image_path"] = image_path
            saved_images += 1
        
        # Annotation speichern
        if save_annotation(receipt_data, idx):
            saved_annotations += 1
        
        # An API senden (falls verfügbar)
        if api_available:
            if send_to_api(receipt_data):
                success_count += 1
                print(f"✅ {receipt_data['vendor_name'][:30]}")
            else:
                print(f"⚠️  {receipt_data['vendor_name'][:30]} (nur lokal)")
        else:
            print(f"💾 {receipt_data['vendor_name'][:30]} (lokal gespeichert)")
            success_count += 1
    
    # Zusammenfassung
    print()
    print("=" * 60)
    print("📊 ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"   Verarbeitet:     {actual_limit}")
    print(f"   Erfolgreich:     {success_count}")
    print(f"   Bilder:          {saved_images}")
    print(f"   Annotationen:    {saved_annotations}")
    print()
    print(f"📁 Gespeichert in:  {CORD_SAVE_PATH}")
    print(f"   └── images/      {saved_images} PNG-Dateien")
    print(f"   └── annotations/ {saved_annotations} JSON-Dateien")
    print()
    
    if api_available:
        print("🚀 Daten wurden auch an das AI-Backend gesendet!")
        print("   Teste mit: curl http://localhost:8000/api/search?query=restaurant")
    else:
        print("⚠️  Backend war nicht erreichbar.")
        print("   Starte es mit: cd ai-backend && python main.py")
        print("   Dann nochmal: python load_cord_huggingface.py")
    
    print()
    print("✅ Fertig!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CORD-v2 Dataset Loader")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help=f"Anzahl der zu ladenden Quittungen (default: {DEFAULT_LIMIT})")
    args = parser.parse_args()
    
    load_cord_dataset(limit=args.limit)

