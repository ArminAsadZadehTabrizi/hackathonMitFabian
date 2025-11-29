"""
Smart Query Handler - Verarbeitet Anfragen präzise mit SQL und gibt klare Anweisungen an Ollama

Dieser Handler:
1. Parst die User-Frage (Deutsch + Englisch)
2. Erkennt Filter: Vendor, Kategorie, Betrag, Datum, Audit-Flags
3. Führt SQL-Queries aus
4. Berechnet präzise Summen in Python
5. Gibt strukturierte Daten an das LLM

Das LLM formuliert dann nur die Antwort - es rechnet NICHT selbst!
"""
from sqlmodel import Session, select
from models.db_models import ReceiptDB, LineItemDB
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta


def parse_query_and_calculate(query: str, session: Session) -> Tuple[Dict, List[ReceiptDB], str]:
    """
    Analysiert die Query und macht präzise SQL-Berechnungen.
    
    Unterstützte Filter:
    - Vendor: "von Saturn", "from Amazon"
    - Kategorie: "für Elektronik", "for electronics"
    - Betrag: "unter 100€", "über 200", "above 100", "below 50"
    - Datum: "letzte Woche", "letzter Monat", "last month", "last week"
    - Audit: "suspicious", "duplicate", "missing VAT", "verdächtig"
    
    Returns:
        (calculations, filtered_receipts, filter_description)
    """
    query_lower = query.lower()
    
    # Hole ALLE Receipts
    all_receipts = session.exec(select(ReceiptDB)).all()
    filtered_receipts = list(all_receipts)
    filters_applied = []
    
    # ═══════════════════════════════════════════════════════════════
    # 1. BETRAG-FILTER (Deutsch + Englisch)
    # ═══════════════════════════════════════════════════════════════
    
    # Unter/Below
    under_match = re.search(r'(?:unter|below|less than|unter)\s+(\d+(?:[.,]\d+)?)', query_lower)
    if under_match:
        limit = float(under_match.group(1).replace(',', '.'))
        filtered_receipts = [r for r in filtered_receipts if r.total_amount < limit]
        filters_applied.append(f"unter {limit}€")
    
    # Über/Above
    over_match = re.search(r'(?:über|ueber|above|over|more than|greater than)\s+(\d+(?:[.,]\d+)?)', query_lower)
    if over_match:
        limit = float(over_match.group(1).replace(',', '.'))
        filtered_receipts = [r for r in filtered_receipts if r.total_amount > limit]
        filters_applied.append(f"über {limit}€")
    
    # Zwischen/Between
    between_match = re.search(r'(?:zwischen|between)\s+(\d+(?:[.,]\d+)?)\s+(?:und|and)\s+(\d+(?:[.,]\d+)?)', query_lower)
    if between_match:
        min_val = float(between_match.group(1).replace(',', '.'))
        max_val = float(between_match.group(2).replace(',', '.'))
        filtered_receipts = [r for r in filtered_receipts if min_val <= r.total_amount <= max_val]
        filters_applied.append(f"zwischen {min_val}€ und {max_val}€")
    
    # ═══════════════════════════════════════════════════════════════
    # 2. VENDOR-FILTER
    # ═══════════════════════════════════════════════════════════════
    all_vendors = list(set([r.vendor_name for r in all_receipts]))
    for vendor in all_vendors:
        if vendor.lower() in query_lower:
            filtered_receipts = [r for r in filtered_receipts if r.vendor_name == vendor]
            filters_applied.append(f"Vendor: {vendor}")
            break
    
    # ═══════════════════════════════════════════════════════════════
    # 3. KATEGORIE-FILTER
    # ═══════════════════════════════════════════════════════════════
    all_categories = list(set([r.category for r in all_receipts if r.category]))
    for cat in all_categories:
        if cat.lower() in query_lower:
            filtered_receipts = [r for r in filtered_receipts if r.category == cat]
            filters_applied.append(f"Kategorie: {cat}")
            break
    
    # ═══════════════════════════════════════════════════════════════
    # 4. DATUM-FILTER
    # ═══════════════════════════════════════════════════════════════
    today = datetime.now()
    
    # Letzte Woche / Last week
    if any(kw in query_lower for kw in ['letzte woche', 'letzten woche', 'last week', 'this week']):
        week_ago = today - timedelta(days=7)
        filtered_receipts = [r for r in filtered_receipts if r.date and r.date >= week_ago]
        filters_applied.append("letzte Woche")
    
    # Letzter Monat / Last month
    elif any(kw in query_lower for kw in ['letzter monat', 'letzten monat', 'last month', 'this month']):
        month_ago = today - timedelta(days=30)
        filtered_receipts = [r for r in filtered_receipts if r.date and r.date >= month_ago]
        filters_applied.append("letzter Monat")
    
    # Letztes Jahr / Last year
    elif any(kw in query_lower for kw in ['letztes jahr', 'last year', 'this year']):
        year_ago = today - timedelta(days=365)
        filtered_receipts = [r for r in filtered_receipts if r.date and r.date >= year_ago]
        filters_applied.append("letztes Jahr")
    
    # ═══════════════════════════════════════════════════════════════
    # 5. AUDIT-FLAGS FILTER
    # ═══════════════════════════════════════════════════════════════
    
    # Duplikate
    if any(kw in query_lower for kw in ['duplicate', 'duplikat', 'doppelt']):
        filtered_receipts = [r for r in filtered_receipts if r.flag_duplicate]
        filters_applied.append("Duplikate")
    
    # Verdächtig / Suspicious
    if any(kw in query_lower for kw in ['suspicious', 'verdächtig', 'verdaechtig', 'alkohol', 'alcohol', 'tabak', 'tobacco']):
        filtered_receipts = [r for r in filtered_receipts if r.flag_suspicious]
        filters_applied.append("Verdächtig")
    
    # Fehlende MwSt / Missing VAT
    if any(kw in query_lower for kw in ['missing vat', 'fehlende mwst', 'ohne mwst', 'no vat', 'keine mwst']):
        filtered_receipts = [r for r in filtered_receipts if r.flag_missing_vat]
        filters_applied.append("Fehlende MwSt")
    
    # Rechenfehler / Math error
    if any(kw in query_lower for kw in ['math error', 'rechenfehler', 'mismatch', 'falsch berechnet']):
        filtered_receipts = [r for r in filtered_receipts if r.flag_math_error]
        filters_applied.append("Rechenfehler")
    
    # Alle Probleme / All issues
    if any(kw in query_lower for kw in ['problem', 'issue', 'fehler', 'flag', 'audit']):
        filtered_receipts = [r for r in filtered_receipts if r.flag_duplicate or r.flag_suspicious or r.flag_missing_vat or r.flag_math_error]
        filters_applied.append("Alle Audit-Probleme")
    
    # ═══════════════════════════════════════════════════════════════
    # 6. BERECHNE STATISTIKEN
    # ═══════════════════════════════════════════════════════════════
    
    total = sum(r.total_amount for r in filtered_receipts)
    count = len(filtered_receipts)
    avg = total / count if count > 0 else 0
    
    # Min/Max
    min_receipt = min(filtered_receipts, key=lambda r: r.total_amount) if filtered_receipts else None
    max_receipt = max(filtered_receipts, key=lambda r: r.total_amount) if filtered_receipts else None
    
    # Top Vendors
    vendor_totals = {}
    for r in filtered_receipts:
        vendor_totals[r.vendor_name] = vendor_totals.get(r.vendor_name, 0) + r.total_amount
    top_vendors = sorted(vendor_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Top Categories
    category_totals = {}
    for r in filtered_receipts:
        cat = r.category or "Sonstiges"
        category_totals[cat] = category_totals.get(cat, 0) + r.total_amount
    top_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # ═══════════════════════════════════════════════════════════════
    # 7. ERSTELLE FILTER-BESCHREIBUNG
    # ═══════════════════════════════════════════════════════════════
    
    if filters_applied:
        filter_desc = " + ".join(filters_applied)
    else:
        filter_desc = "alle Quittungen"
    
    # ═══════════════════════════════════════════════════════════════
    # 8. ERSTELLE CALCULATIONS-OBJEKT
    # ═══════════════════════════════════════════════════════════════
    
    calculations = {
        "result": {
            "total": round(total, 2),
            "count": count,
            "average": round(avg, 2),
            "filter": filter_desc,
            "min": {
                "vendor": min_receipt.vendor_name if min_receipt else None,
                "total": min_receipt.total_amount if min_receipt else None
            },
            "max": {
                "vendor": max_receipt.vendor_name if max_receipt else None,
                "total": max_receipt.total_amount if max_receipt else None
            },
            "top_vendors": [{"vendor": v, "total": round(t, 2)} for v, t in top_vendors],
            "top_categories": [{"category": c, "total": round(t, 2)} for c, t in top_categories],
            "receipts": [
                {
                    "id": r.id,
                    "vendor": r.vendor_name,
                    "date": r.date.strftime('%Y-%m-%d') if r.date else "",
                    "total": r.total_amount,
                    "category": r.category or "Sonstiges",
                    "flags": {
                        "duplicate": r.flag_duplicate,
                        "suspicious": r.flag_suspicious,
                        "missing_vat": r.flag_missing_vat,
                        "math_error": r.flag_math_error
                    }
                }
                for r in filtered_receipts[:20]  # Max 20 für Details
            ]
        }
    }
    
    return calculations, filtered_receipts, filter_desc


def get_query_insights(query: str, calculations: Dict) -> str:
    """
    Generiert zusätzliche Insights basierend auf der Anfrage.
    Diese werden dem LLM als Kontext mitgegeben.
    """
    result = calculations.get("result", {})
    insights = []
    
    # Insights zu Gesamtsumme
    total = result.get("total", 0)
    count = result.get("count", 0)
    
    if count == 0:
        insights.append("⚠️ Keine Quittungen gefunden, die den Kriterien entsprechen.")
    else:
        insights.append(f"📊 Gefunden: {count} Quittungen mit Gesamtsumme {total}€")
        
        # Durchschnitt
        avg = result.get("average", 0)
        if avg > 0:
            insights.append(f"📈 Durchschnitt pro Quittung: {avg}€")
        
        # Min/Max
        min_data = result.get("min", {})
        max_data = result.get("max", {})
        if min_data.get("vendor") and max_data.get("vendor"):
            insights.append(f"📉 Kleinste: {min_data['total']}€ ({min_data['vendor']})")
            insights.append(f"📈 Größte: {max_data['total']}€ ({max_data['vendor']})")
        
        # Top Vendor
        top_vendors = result.get("top_vendors", [])
        if top_vendors:
            top = top_vendors[0]
            insights.append(f"🏪 Top Vendor: {top['vendor']} ({top['total']}€)")
        
        # Top Category
        top_cats = result.get("top_categories", [])
        if top_cats:
            top = top_cats[0]
            insights.append(f"📁 Top Kategorie: {top['category']} ({top['total']}€)")
    
    return "\n".join(insights)
