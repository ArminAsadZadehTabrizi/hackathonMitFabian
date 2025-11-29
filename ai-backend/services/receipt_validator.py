"""
Receipt Validator - Validiert und korrigiert extrahierte Quittungsdaten
"""
from typing import List, Optional, Dict
from models.receipt import Receipt, LineItem


def validate_receipt(receipt: Receipt) -> Dict:
    """
    Validiert eine Quittung und gibt Warnungen/Korrekturen zurück.
    
    Returns:
        Dict mit validation_status, warnings, corrections
    """
    warnings = []
    corrections = {}
    
    # 1. Prüfe ob Total = Summe der Items
    items_sum = sum(item.total_price * (item.quantity if item.quantity > 0 else 1) 
                   for item in receipt.line_items)
    
    if receipt.total and abs(items_sum - receipt.total) > 0.01:
        diff = abs(items_sum - receipt.total)
        warnings.append(f"Total ({receipt.total}€) stimmt nicht mit Summe der Items ({items_sum:.2f}€) überein. Differenz: {diff:.2f}€")
        # Korrektur vorschlagen
        if items_sum > 0:
            corrections["total"] = items_sum
    
    # 2. Prüfe ob MwSt konsistent ist
    if receipt.tax and receipt.tax_rate and receipt.subtotal:
        expected_tax = receipt.subtotal * (receipt.tax_rate / 100)
        if abs(receipt.tax - expected_tax) > 0.01:
            warnings.append(f"MwSt ({receipt.tax}€) stimmt nicht mit berechneter MwSt ({expected_tax:.2f}€) überein")
    
    # 3. Prüfe ob Items leer sind
    if not receipt.line_items:
        warnings.append("Keine Line Items gefunden - Quittung könnte unvollständig sein")
    
    # 4. Prüfe ob Vendor-Name vorhanden ist
    if not receipt.vendor_name or receipt.vendor_name.lower() in ["unbekannt", "unknown", "parse error"]:
        warnings.append("Vendor-Name fehlt oder konnte nicht extrahiert werden")
    
    # 5. Prüfe ob Datum vorhanden ist
    if not receipt.date:
        warnings.append("Datum fehlt - könnte wichtig für Analysen sein")
    
    # 6. Prüfe ob Kategorien fehlen
    missing_categories = [item for item in receipt.line_items if not item.category]
    if missing_categories:
        warnings.append(f"{len(missing_categories)} Items ohne Kategorie - Auto-Klassifizierung könnte helfen")
    
    # Status bestimmen
    if not warnings:
        status = "valid"
    elif len(warnings) <= 2:
        status = "warning"
    else:
        status = "error"
    
    return {
        "status": status,
        "warnings": warnings,
        "corrections": corrections,
        "items_sum": items_sum,
        "total": receipt.total
    }


def auto_classify_category(receipt: Receipt) -> str:
    """
    Klassifiziert automatisch die Kategorie einer Quittung basierend auf Vendor-Name und Items.
    """
    vendor_lower = (receipt.vendor_name or "").lower()
    items_text = " ".join([item.description.lower() for item in receipt.line_items])
    combined_text = f"{vendor_lower} {items_text}"
    
    # Restaurant-Keywords
    if any(kw in combined_text for kw in ["restaurant", "cafe", "coffee", "pizza", "pasta", "burger", "sushi", "bar", "bistro"]):
        return "Restaurant"
    
    # Supermarkt
    if any(kw in combined_text for kw in ["rewe", "aldi", "lidl", "edeka", "kaufland", "supermarkt", "market", "grocery"]):
        return "Supermarkt"
    
    # Tankstelle
    if any(kw in combined_text for kw in ["shell", "aral", "esso", "total", "tankstelle", "gas", "fuel", "benzin", "diesel"]):
        return "Tankstelle"
    
    # Büro
    if any(kw in combined_text for kw in ["office", "büro", "staples", "paper", "drucker", "tinte"]):
        return "Bürobedarf"
    
    # Elektronik
    if any(kw in combined_text for kw in ["amazon", "mediamarkt", "saturn", "elektronik", "computer", "laptop", "handy"]):
        return "Elektronik"
    
    # Möbel
    if any(kw in combined_text for kw in ["ikea", "möbel", "furniture", "regal", "tisch", "stuhl"]):
        return "Möbel"
    
    # Café
    if any(kw in combined_text for kw in ["starbucks", "café", "cafe", "latte", "cappuccino"]):
        return "Café"
    
    return "Sonstiges"


def auto_classify_item_category(item: LineItem, vendor_name: str = "") -> str:
    """
    Klassifiziert automatisch die Kategorie eines Items.
    """
    desc_lower = item.description.lower()
    vendor_lower = vendor_name.lower()
    combined = f"{desc_lower} {vendor_lower}"
    
    # Alkohol
    if any(kw in combined for kw in ["wein", "bier", "schnaps", "alkohol", "spirituosen", "champagner", "prosecco"]):
        return "Alkohol"
    
    # Getränke
    if any(kw in combined for kw in ["wasser", "cola", "saft", "limo", "kaffee", "tee", "getränk", "drink"]):
        return "Getränke"
    
    # Lebensmittel
    if any(kw in combined for kw in ["milch", "brot", "käse", "wurst", "fleisch", "obst", "gemüse", "lebensmittel", "food"]):
        return "Lebensmittel"
    
    # Essen (Restaurant)
    if any(kw in combined for kw in ["pizza", "pasta", "burger", "salat", "schnitzel", "essen", "gericht"]):
        return "Essen"
    
    # Kraftstoff
    if any(kw in combined for kw in ["benzin", "diesel", "e10", "super", "kraftstoff", "tank"]):
        return "Kraftstoff"
    
    # Elektronik
    if any(kw in combined for kw in ["laptop", "handy", "tablet", "kamera", "kopfhörer", "ladekabel", "elektronik"]):
        return "Elektronik"
    
    # Bürobedarf
    if any(kw in combined for kw in ["stift", "papier", "ordner", "maus", "tastatur", "büro"]):
        return "Bürobedarf"
    
    # Möbel
    if any(kw in combined for kw in ["tisch", "stuhl", "regal", "schrank", "möbel"]):
        return "Möbel"
    
    return "Sonstiges"


def fix_receipt(receipt: Receipt, apply_corrections: bool = True) -> Receipt:
    """
    Korrigiert eine Quittung basierend auf Validierung.
    
    Args:
        receipt: Die zu korrigierende Quittung
        apply_corrections: Ob Korrekturen automatisch angewendet werden sollen
    
    Returns:
        Korrigierte Quittung
    """
    validation = validate_receipt(receipt)
    
    # Auto-Klassifizierung für fehlende Kategorien
    if not receipt.category:
        receipt.category = auto_classify_category(receipt)
    
    # Auto-Klassifizierung für Items ohne Kategorie
    for item in receipt.line_items:
        if not item.category:
            item.category = auto_classify_item_category(item, receipt.vendor_name)
    
    # Korrekturen anwenden
    if apply_corrections and validation["corrections"]:
        if "total" in validation["corrections"]:
            receipt.total = validation["corrections"]["total"]
    
    return receipt

