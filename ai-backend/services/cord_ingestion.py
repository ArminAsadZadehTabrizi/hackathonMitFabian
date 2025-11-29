"""
CORD Dataset Ingestion - Lädt den CORD Datensatz in die RAG-Datenbank

Der CORD (Consolidated Receipt Dataset) enthält:
- Bilder von Quittungen
- JSON-Annotationen mit extrahierten Daten

Download: https://github.com/clovaai/cord
"""
import json
import os
from pathlib import Path
from typing import List, Tuple, Optional
import random

from models.receipt import Receipt, LineItem
from services.rag_service import add_receipts_batch, init_rag


def parse_cord_annotation(json_path: str) -> Optional[Receipt]:
    """
    Parst eine CORD JSON-Annotation zu einem Receipt-Objekt.
    
    CORD Format:
    {
        "valid_line": [...],
        "meta": {...},
        "roi": {...}
    }
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # CORD hat verschiedene Felder
        # Wir extrahieren was wir können
        
        vendor_name = "Unbekannt"
        date = None
        total = 0.0
        subtotal = None
        tax = None
        line_items = []
        
        # Durch valid_line iterieren
        for line in data.get("valid_line", []):
            words = line.get("words", [])
            category = line.get("category", "")
            
            # Text aus words zusammenbauen
            text = " ".join([w.get("text", "") for w in words])
            
            # Je nach Kategorie zuordnen
            if category == "menu.nm":  # Produktname
                line_items.append({
                    "description": text,
                    "total_price": 0  # Wird später gefüllt
                })
            elif category == "menu.price":  # Produktpreis
                try:
                    price = float(text.replace(",", ".").replace("€", "").replace("$", "").strip())
                    if line_items:
                        line_items[-1]["total_price"] = price
                except:
                    pass
            elif category == "menu.cnt":  # Menge
                try:
                    qty = float(text)
                    if line_items:
                        line_items[-1]["quantity"] = qty
                except:
                    pass
            elif category == "store.name" or category == "store_name":
                vendor_name = text
            elif category == "total.total_price" or category == "total":
                try:
                    total = float(text.replace(",", ".").replace("€", "").replace("$", "").strip())
                except:
                    pass
            elif category == "subtotal.subtotal_price":
                try:
                    subtotal = float(text.replace(",", ".").replace("€", "").replace("$", "").strip())
                except:
                    pass
            elif category == "total.tax_price":
                try:
                    tax = float(text.replace(",", ".").replace("€", "").replace("$", "").strip())
                except:
                    pass
            elif "date" in category.lower():
                date = text
        
        # LineItems erstellen
        receipt_items = []
        for item in line_items:
            if item.get("description"):
                receipt_items.append(LineItem(
                    description=item["description"],
                    quantity=item.get("quantity", 1),
                    total_price=item.get("total_price", 0)
                ))
        
        return Receipt(
            vendor_name=vendor_name,
            date=date,
            total=total,
            subtotal=subtotal,
            tax=tax,
            line_items=receipt_items,
            category=guess_category(vendor_name, receipt_items)
        )
        
    except Exception as e:
        print(f"Fehler beim Parsen von {json_path}: {e}")
        return None


def guess_category(vendor_name: str, items: List[LineItem]) -> str:
    """
    Rät die Kategorie basierend auf Vendor-Name und Items.
    """
    vendor_lower = vendor_name.lower()
    
    # Restaurant-Keywords
    if any(kw in vendor_lower for kw in ["restaurant", "cafe", "coffee", "pizza", "burger", "sushi", "bar"]):
        return "Restaurant"
    
    # Supermarkt
    if any(kw in vendor_lower for kw in ["market", "grocery", "rewe", "aldi", "lidl", "edeka", "supermarket"]):
        return "Supermarkt"
    
    # Tankstelle
    if any(kw in vendor_lower for kw in ["gas", "fuel", "shell", "aral", "esso", "tank"]):
        return "Tankstelle"
    
    # Büro
    if any(kw in vendor_lower for kw in ["office", "büro", "staples", "paperwork"]):
        return "Bürobedarf"
    
    return "Sonstiges"


def load_cord_dataset(
    cord_path: str,
    limit: Optional[int] = None,
    random_sample: bool = True
) -> List[Tuple[str, Receipt]]:
    """
    Lädt CORD Daten aus einem Verzeichnis.
    
    Args:
        cord_path: Pfad zum CORD Dataset (z.B. cord/train)
        limit: Maximale Anzahl zu ladender Quittungen
        random_sample: Zufällige Auswahl statt erste N
    
    Returns:
        Liste von (id, Receipt) Tupeln
    """
    cord_path = Path(cord_path)
    
    # Suche nach JSON-Dateien
    json_files = list(cord_path.rglob("*.json"))
    
    if not json_files:
        print(f"⚠️ Keine JSON-Dateien in {cord_path} gefunden!")
        return []
    
    print(f"📂 {len(json_files)} JSON-Dateien gefunden")
    
    # Sampling
    if random_sample and limit and len(json_files) > limit:
        json_files = random.sample(json_files, limit)
    elif limit:
        json_files = json_files[:limit]
    
    receipts = []
    for json_file in json_files:
        receipt = parse_cord_annotation(str(json_file))
        if receipt:
            receipt_id = json_file.stem  # Dateiname ohne Extension
            receipts.append((receipt_id, receipt))
    
    print(f"✅ {len(receipts)} Quittungen erfolgreich geparst")
    return receipts


def ingest_cord_to_rag(cord_path: str, limit: int = 100):
    """
    Hauptfunktion: Lädt CORD Daten und fügt sie zur RAG-DB hinzu.
    
    Args:
        cord_path: Pfad zum CORD Dataset
        limit: Anzahl der zu ladenden Quittungen
    """
    print(f"🚀 Starte CORD Ingestion aus {cord_path}")
    
    # RAG initialisieren
    init_rag()
    
    # Daten laden
    receipts = load_cord_dataset(cord_path, limit=limit)
    
    if not receipts:
        print("❌ Keine Quittungen geladen!")
        return
    
    # In Batches zur DB hinzufügen
    batch_size = 50
    for i in range(0, len(receipts), batch_size):
        batch = receipts[i:i+batch_size]
        add_receipts_batch(batch)
        print(f"📦 Batch {i//batch_size + 1} verarbeitet...")
    
    print(f"🎉 Ingestion abgeschlossen! {len(receipts)} Quittungen in der RAG-DB")


# Dummy-Daten für Demo (falls kein CORD verfügbar)
DEMO_RECEIPTS = [
    Receipt(
        vendor_name="REWE Supermarkt",
        date="2024-01-15",
        total=47.89,
        tax=7.65,
        tax_rate=19.0,
        category="Supermarkt",
        line_items=[
            LineItem(description="Bio Milch 1L", quantity=2, total_price=2.58, category="Lebensmittel"),
            LineItem(description="Vollkornbrot", quantity=1, total_price=3.49, category="Lebensmittel"),
            LineItem(description="Bananen 1kg", quantity=1, total_price=1.99, category="Lebensmittel"),
            LineItem(description="Mineralwasser 6x1.5L", quantity=1, total_price=4.99, category="Getränke"),
            LineItem(description="Kaffee Bohnen 500g", quantity=1, total_price=8.99, category="Getränke"),
            LineItem(description="Wein Rot 0.75L", quantity=2, total_price=15.98, category="Alkohol"),
        ]
    ),
    Receipt(
        vendor_name="Shell Tankstelle",
        date="2024-01-14",
        total=72.50,
        tax=11.58,
        tax_rate=19.0,
        category="Tankstelle",
        line_items=[
            LineItem(description="Super E10 45L", quantity=45, total_price=72.50, category="Kraftstoff"),
        ]
    ),
    Receipt(
        vendor_name="Restaurant La Piazza",
        date="2024-01-12",
        total=89.50,
        tax=14.30,
        tax_rate=19.0,
        category="Restaurant",
        payment_method="Kreditkarte",
        line_items=[
            LineItem(description="Pizza Margherita", quantity=1, total_price=12.90, category="Essen"),
            LineItem(description="Pasta Carbonara", quantity=1, total_price=15.90, category="Essen"),
            LineItem(description="Tiramisu", quantity=2, total_price=14.00, category="Dessert"),
            LineItem(description="Rotwein Flasche", quantity=1, total_price=28.00, category="Alkohol"),
            LineItem(description="Espresso", quantity=2, total_price=5.80, category="Getränke"),
            LineItem(description="Trinkgeld", quantity=1, total_price=12.90, category="Sonstiges"),
        ]
    ),
    Receipt(
        vendor_name="Amazon",
        date="2024-01-10",
        total=159.97,
        tax=25.55,
        tax_rate=19.0,
        category="Online Shopping",
        line_items=[
            LineItem(description="USB-C Ladekabel 3er Pack", quantity=1, total_price=12.99, category="Elektronik"),
            LineItem(description="Wireless Mouse", quantity=1, total_price=29.99, category="Bürobedarf"),
            LineItem(description="Laptop Stand", quantity=1, total_price=45.99, category="Bürobedarf"),
            LineItem(description="Kopfhörer Bluetooth", quantity=1, total_price=69.00, category="Elektronik"),
        ]
    ),
    Receipt(
        vendor_name="Starbucks Coffee",
        date="2024-01-11",
        total=12.40,
        tax=1.98,
        tax_rate=19.0,
        category="Café",
        line_items=[
            LineItem(description="Caramel Macchiato Grande", quantity=1, total_price=5.20, category="Getränke"),
            LineItem(description="Chocolate Muffin", quantity=1, total_price=3.50, category="Snack"),
            LineItem(description="Espresso Doppio", quantity=1, total_price=3.70, category="Getränke"),
        ]
    ),
    Receipt(
        vendor_name="IKEA",
        date="2024-01-08",
        total=234.90,
        tax=37.53,
        tax_rate=19.0,
        category="Möbel",
        line_items=[
            LineItem(description="KALLAX Regal", quantity=1, total_price=69.99, category="Möbel"),
            LineItem(description="MALM Schreibtisch", quantity=1, total_price=129.00, category="Möbel"),
            LineItem(description="LED Schreibtischlampe", quantity=1, total_price=24.99, category="Elektronik"),
            LineItem(description="Hotdog + Cola", quantity=1, total_price=1.50, category="Essen"),
        ]
    ),
]


def load_demo_data():
    """Lädt Demo-Daten in die RAG-DB."""
    print("🎭 Lade Demo-Daten...")
    init_rag()
    
    receipts = [(f"demo_{i}", r) for i, r in enumerate(DEMO_RECEIPTS)]
    add_receipts_batch(receipts)
    
    print(f"✅ {len(DEMO_RECEIPTS)} Demo-Quittungen geladen!")


if __name__ == "__main__":
    # Wenn direkt ausgeführt: Demo-Daten laden
    load_demo_data()

