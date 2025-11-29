"""
Analytics Service - Präzise Berechnungen für Quittungen
Nutzt Python für deterministische Mathematik statt LLM
"""
from typing import List, Dict, Optional
from models.receipt import Receipt, LineItem
from services.rag_service import search_receipts, get_receipt_objects_by_ids


def calculate_total_by_category(
    category_filter: str,
    receipts_data: Optional[List[Dict]] = None
) -> Dict:
    """
    Berechnet präzise Summe nach Kategorie.
    Nutzt Receipt-Objekte für präzise Berechnungen.
    
    Args:
        category_filter: Kategorie (z.B. "Alkohol", "Getränke", "Essen")
        receipts_data: Optional - bereits gefundene Quittungen
    
    Returns:
        Dict mit total, items, breakdown
    """
    if receipts_data is None:
        # Suche relevante Quittungen
        receipts_data = search_receipts(category_filter, n_results=100)
    
    # Hole Receipt-Objekte für präzise Berechnungen
    receipt_ids = [r["id"] for r in receipts_data]
    receipt_objects = get_receipt_objects_by_ids(receipt_ids)
    
    total = 0.0
    items = []
    vendors = {}
    
    # Normalisiere Filter
    filter_lower = category_filter.lower().strip()
    # Mapping für verschiedene Formulierungen
    category_mapping = {
        "alkohol": ["alkohol"],
        "getränke": ["getränke", "getraenke", "drinks"],
        "getraenke": ["getränke", "getraenke", "drinks"],
        "essen": ["essen", "food"],  # Nur Essen, nicht Lebensmittel
        "lebensmittel": ["lebensmittel"]  # Nur echte Lebensmittel, nicht Essen aus Restaurants
    }
    
    # Erweitere Filter wenn Mapping vorhanden
    search_categories = [filter_lower]
    if filter_lower in category_mapping:
        search_categories.extend(category_mapping[filter_lower])
    
    # Nutze Receipt-Objekte für präzise Berechnung
    for receipt in receipt_objects:
        if receipt is None:
            continue
        
        for line_item in receipt.line_items:
            # Prüfe Kategorie des Items
            item_cat = (line_item.category or "").lower()
            desc_lower = line_item.description.lower()
            
            # Prüfe ob Kategorie passt
            matches_category = False
            for search_cat in search_categories:
                if search_cat in item_cat or item_cat in search_cat:
                    matches_category = True
                    break
                # Auch in Beschreibung suchen
                if search_cat in desc_lower:
                    matches_category = True
                    break
            
            if matches_category:
                # total_price ist der Einzelpreis pro Item
                # Wir multiplizieren mit quantity um den Gesamtpreis zu erhalten
                # z.B. 2 Flaschen Wein à 15.98€ = 31.96€
                item_total = line_item.total_price * (line_item.quantity if line_item.quantity > 0 else 1)
                total += item_total
                items.append({
                    "description": line_item.description,
                    "price": item_total,
                    "unit_price": line_item.total_price,
                    "quantity": line_item.quantity,
                    "vendor": receipt.vendor_name,
                    "date": receipt.date or "",
                    "category": line_item.category or "Unbekannt"
                })
                
                # Vendor-Statistik
                vendors[receipt.vendor_name] = vendors.get(receipt.vendor_name, 0) + item_total
    
    return {
        "total": round(total, 2),
        "items": items,
        "vendors": vendors,
        "count": len(items)
    }


def calculate_total_by_keyword(
    keyword: str,
    receipts_data: Optional[List[Dict]] = None
) -> Dict:
    """
    Berechnet Summe für Items die ein Keyword enthalten.
    Nutzt semantische Suche + präzise Berechnung.
    """
    if receipts_data is None:
        receipts_data = search_receipts(keyword, n_results=100)
    
    total = 0.0
    items = []
    
    for result in receipts_data:
        doc = result["document"]
        metadata = result["metadata"]
        
        # Suche nach Items die Keyword enthalten
        import re
        pattern = r'-\s+([^:]+):\s+([\d,]+\.?\d*)\s*€'
        matches = re.findall(pattern, doc)
        
        keyword_lower = keyword.lower()
        
        for desc, price_str in matches:
            if keyword_lower in desc.lower():
                try:
                    price = float(price_str.replace(",", "."))
                    total += price
                    items.append({
                        "description": desc.strip(),
                        "price": price,
                        "vendor": metadata.get("vendor_name", "Unbekannt")
                    })
                except ValueError:
                    pass
    
    return {
        "total": round(total, 2),
        "items": items,
        "count": len(items)
    }


def calculate_top_expenses(
    n: int = 5,
    receipts_data: Optional[List[Dict]] = None
) -> List[Dict]:
    """
    Findet die Top N Ausgaben.
    Nutzt Receipt-Objekte für präzise Daten.
    """
    if receipts_data is None:
        receipts_data = search_receipts("höchste Ausgaben", n_results=100)
    
    # Hole Receipt-Objekte
    receipt_ids = [r["id"] for r in receipts_data]
    receipt_objects = get_receipt_objects_by_ids(receipt_ids)
    
    expenses = []
    
    for receipt in receipt_objects:
        if receipt is None:
            continue
        
        expenses.append({
            "vendor": receipt.vendor_name,
            "date": receipt.date or "",
            "total": receipt.total,
            "category": receipt.category or "Unbekannt"
        })
    
    # Sortiere nach total (höchste zuerst)
    expenses.sort(key=lambda x: x["total"], reverse=True)
    
    return expenses[:n]


def calculate_spending_by_category_all(
    receipts_data: Optional[List[Dict]] = None
) -> Dict[str, float]:
    """
    Berechnet Ausgaben für alle Kategorien.
    Nutzt Receipt-Objekte für präzise Daten.
    """
    if receipts_data is None:
        receipts_data = search_receipts("alle Ausgaben", n_results=100)
    
    # Hole Receipt-Objekte
    receipt_ids = [r["id"] for r in receipts_data]
    receipt_objects = get_receipt_objects_by_ids(receipt_ids)
    
    categories = {}
    
    for receipt in receipt_objects:
        if receipt is None:
            continue
        
        category = receipt.category or "Sonstiges"
        categories[category] = categories.get(category, 0) + receipt.total
    
    # Runde alle Werte
    return {k: round(v, 2) for k, v in categories.items()}


def extract_items_from_receipts(
    receipts_data: List[Dict],
    category_filter: Optional[str] = None
) -> List[Dict]:
    """
    Extrahiert alle Items aus Quittungen, optional gefiltert nach Kategorie.
    """
    all_items = []
    
    for result in receipts_data:
        doc = result["document"]
        metadata = result["metadata"]
        
        import re
        # Finde alle Items
        pattern = r'-\s+([^:]+):\s+([\d,]+\.?\d*)\s*€(?:\s*\([^)]*Kategorie:\s*([^)]+)\))?'
        matches = re.findall(pattern, doc)
        
        for desc, price_str, cat in matches:
            # Filter nach Kategorie
            if category_filter:
                cat_lower = (cat or "").lower()
                filter_lower = category_filter.lower()
                if filter_lower not in cat_lower and cat_lower not in filter_lower:
                    continue
            
            try:
                price = float(price_str.replace(",", "."))
                all_items.append({
                    "description": desc.strip(),
                    "price": price,
                    "category": cat.strip() if cat else "Unbekannt",
                    "vendor": metadata.get("vendor_name", "Unbekannt"),
                    "date": metadata.get("date", "")
                })
            except ValueError:
                pass
    
    return all_items


def calculate_precise_answer(
    question: str,
    receipts_data: Optional[List[Dict]] = None
) -> Optional[Dict]:
    """
    Analysiert die Frage und macht präzise Berechnungen.
    Gibt None zurück wenn keine Berechnung möglich/nötig ist.
    """
    question_lower = question.lower()
    
    # Erkenne verschiedene Frage-Typen
    calculations = {}
    
    # 1. "Wie viel für X?" - Kategorie-Summe
    if "wie viel" in question_lower or "wieviel" in question_lower or "wie viel" in question_lower:
        # Suche nach Kategorien
        categories_to_check = [
            ("alkohol", ["alkohol", "wein", "bier", "spirituosen"]),
            ("getränke", ["getränke", "getraenke", "drinks", "kaffee", "tee", "saft"]),
            ("getraenke", ["getränke", "getraenke", "drinks"]),
            ("essen", ["essen", "lebensmittel", "food", "pizza", "pasta"]),
            ("lebensmittel", ["essen", "lebensmittel", "food"]),
            ("tankstelle", ["tankstelle", "kraftstoff", "benzin", "diesel"]),
            ("kraftstoff", ["kraftstoff", "benzin", "diesel"]),
            ("restaurant", ["restaurant", "essen"]),
            ("supermarkt", ["supermarkt", "lebensmittel"]),
            ("elektronik", ["elektronik", "elektro"]),
            ("bürobedarf", ["bürobedarf", "büro", "office"]),
            ("möbel", ["möbel", "furniture"]),
            ("café", ["café", "cafe", "coffee"]),
        ]
        
        for cat_name, keywords in categories_to_check:
            # Prüfe ob eines der Keywords in der Frage ist
            if any(kw in question_lower for kw in keywords):
                if receipts_data is None:
                    receipts_data = search_receipts(cat_name, n_results=100)
                
                # Berechne präzise
                result = calculate_total_by_category(cat_name, receipts_data)
                calculations[f"total_{cat_name}"] = result
                break
        
        # Falls kein spezifisches Keyword: versuche alle Items zu finden
        if not calculations:
            # Suche nach Items die in der Frage erwähnt werden
            keywords = ["wein", "bier", "kaffee", "pizza", "pasta", "benzin", "diesel", "milch", "brot"]
            for keyword in keywords:
                if keyword in question_lower:
                    if receipts_data is None:
                        receipts_data = search_receipts(keyword, n_results=100)
                    result = calculate_total_by_keyword(keyword, receipts_data)
                    if result["total"] > 0:
                        calculations[f"total_{keyword}"] = result
                        break
    
    # 2. "Top X Ausgaben" oder "höchste Ausgaben"
    if "top" in question_lower or "höchste" in question_lower or "höchsten" in question_lower:
        n = 3  # Default
        # Extrahiere Zahl falls vorhanden
        import re
        num_match = re.search(r'(\d+)', question)
        if num_match:
            n = int(num_match.group(1))
        
        if receipts_data is None:
            receipts_data = search_receipts("höchste Ausgaben", n_results=100)
        
        top = calculate_top_expenses(n, receipts_data)
        if top:
            calculations["top_expenses"] = top
    
    # 3. "Nach Kategorie" oder "Kategorien"
    if "kategorie" in question_lower or "kategorien" in question_lower:
        if receipts_data is None:
            receipts_data = search_receipts("alle Ausgaben", n_results=100)
        
        by_cat = calculate_spending_by_category_all(receipts_data)
        if by_cat:
            calculations["by_category"] = by_cat
    
    return calculations if calculations else None

