"""
Smart Query Handler - Verarbeitet Anfragen präzise mit SQL und gibt klare Anweisungen an Ollama
"""
from sqlmodel import Session, select
from models.db_models import ReceiptDB, LineItemDB
import re
from typing import Dict, List, Tuple


def parse_query_and_calculate(query: str, session: Session) -> Tuple[Dict, List[ReceiptDB], str]:
    """
    Analysiert die Query und macht präzise SQL-Berechnungen.
    
    Returns:
        (calculations, filtered_receipts, filter_description)
    """
    query_lower = query.lower()
    
    # Hole ALLE Receipts
    all_receipts = session.exec(select(ReceiptDB)).all()
    filtered_receipts = all_receipts
    filter_desc = "alle Quittungen"
    
    # 1. Betrag-Filter erkennen
    if "unter" in query_lower:
        match = re.search(r'unter\s+(\d+)', query_lower)
        if match:
            limit = float(match.group(1))
            filtered_receipts = [r for r in all_receipts if r.total_amount < limit]
            filter_desc = f"Quittungen unter {limit}€"
    
    elif "über" in query_lower or "ueber" in query_lower:
        match = re.search(r'(?:über|ueber)\s+(\d+)', query_lower)
        if match:
            limit = float(match.group(1))
            filtered_receipts = [r for r in all_receipts if r.total_amount > limit]
            filter_desc = f"Quittungen über {limit}€"
    
    # 2. Vendor-Filter
    all_vendors = list(set([r.vendor_name for r in all_receipts]))
    vendors_in_query = [v for v in all_vendors if v.lower() in query_lower]
    if vendors_in_query:
        vendor = vendors_in_query[0]
        # Kombiniere mit Betrag-Filter falls vorhanden
        if filter_desc == "alle Quittungen":
            filtered_receipts = [r for r in all_receipts if r.vendor_name == vendor]
        else:
            # Behalte Betrag-Filter und füge Vendor hinzu
            filtered_receipts = [r for r in filtered_receipts if r.vendor_name == vendor]
        filter_desc = f"{filter_desc} von {vendor}"
    
    # 3. Kategorie-Filter
    all_categories = list(set([r.category for r in all_receipts if r.category]))
    categories_in_query = [c for c in all_categories if c.lower() in query_lower]
    if categories_in_query:
        cat = categories_in_query[0]
        if "von" not in filter_desc:  # Nur wenn noch kein Vendor-Filter
            filtered_receipts = [r for r in filtered_receipts if r.category == cat]
            filter_desc = f"{filter_desc} - Kategorie: {cat}"
    
    # 4. Berechne Total
    total = sum(r.total_amount for r in filtered_receipts)
    
    # 5. Erstelle Calculations-Objekt
    calculations = {
        "result": {
            "total": round(total, 2),
            "count": len(filtered_receipts),
            "filter": filter_desc,
            "receipts": [
                {
                    "vendor": r.vendor_name,
                    "date": r.date.strftime('%Y-%m-%d') if r.date else "",
                    "total": r.total_amount,
                    "category": r.category or "Sonstiges"
                }
                for r in filtered_receipts[:20]  # Max 20 für Details
            ]
        }
    }
    
    return calculations, filtered_receipts, filter_desc

