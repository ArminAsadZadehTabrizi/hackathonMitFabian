"""
Smart Query Handler - Precise SQL-based query processing for AI Auditor.

This handler:
1. Parses user questions (German + English)
2. Detects filters: Vendor, Category, Amount, Date, Audit Flags
3. Executes SQL queries
4. Calculates precise sums in Python
5. Returns structured data for LLM

The LLM only formulates the response - it does NOT calculate!
"""
from sqlmodel import Session, select
from models.db_models import ReceiptDB
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import re

from constants import (
    CATEGORY_TRANSLATIONS,
    AMOUNT_PATTERNS,
    DATE_KEYWORDS,
    AUDIT_KEYWORDS,
    find_category_in_query
)


def parse_query_and_calculate(query: str, session: Session) -> Tuple[Dict, List[ReceiptDB], str]:
    """
    Analyze query and perform precise SQL calculations.
    
    Supported filters:
    - Vendor: "von Saturn", "from Amazon"
    - Category: "für Elektronik", "for electronics"
    - Amount: "unter 100€", "über 200", "above 100", "below 50"
    - Date: "letzte Woche", "letzter Monat", "last month", "last week"
    - Audit: "suspicious", "duplicate", "missing VAT", "verdächtig"
    
    Returns:
        (calculations, filtered_receipts, filter_description)
    """
    query_lower = query.lower()
    
    # Get all receipts
    all_receipts = list(session.exec(select(ReceiptDB)).all())
    filtered_receipts = all_receipts.copy()
    filters_applied = []
    
    # Apply filters
    filtered_receipts, filters_applied = _apply_amount_filters(query_lower, filtered_receipts, filters_applied)
    filtered_receipts, filters_applied = _apply_vendor_filter(query_lower, all_receipts, filtered_receipts, filters_applied)
    filtered_receipts, filters_applied = _apply_category_filter(query_lower, filtered_receipts, filters_applied)
    filtered_receipts, filters_applied = _apply_date_filters(query_lower, filtered_receipts, filters_applied)
    filtered_receipts, filters_applied = _apply_audit_filters(query_lower, filtered_receipts, filters_applied)
    
    # Calculate statistics
    calculations = _calculate_statistics(filtered_receipts, filters_applied)
    filter_desc = " + ".join(filters_applied) if filters_applied else "alle Quittungen"
    
    return calculations, filtered_receipts, filter_desc


# =============================================================================
# FILTER FUNCTIONS
# =============================================================================

def _apply_amount_filters(query: str, receipts: List[ReceiptDB], filters: List[str]) -> Tuple[List[ReceiptDB], List[str]]:
    """Apply amount-based filters (under, over, between)."""
    # Under/Below
    if match := re.search(AMOUNT_PATTERNS["under"], query):
        limit = float(match.group(1).replace(',', '.'))
        receipts = [r for r in receipts if r.total_amount < limit]
        filters.append(f"unter {limit}€")
    
    # Over/Above
    if match := re.search(AMOUNT_PATTERNS["over"], query):
        limit = float(match.group(1).replace(',', '.'))
        receipts = [r for r in receipts if r.total_amount > limit]
        filters.append(f"über {limit}€")
    
    # Between
    if match := re.search(AMOUNT_PATTERNS["between"], query):
        min_val = float(match.group(1).replace(',', '.'))
        max_val = float(match.group(2).replace(',', '.'))
        receipts = [r for r in receipts if min_val <= r.total_amount <= max_val]
        filters.append(f"zwischen {min_val}€ und {max_val}€")
    
    return receipts, filters


def _apply_vendor_filter(query: str, all_receipts: List[ReceiptDB], receipts: List[ReceiptDB], filters: List[str]) -> Tuple[List[ReceiptDB], List[str]]:
    """Apply vendor filter."""
    vendors = list(set(r.vendor_name for r in all_receipts))
    for vendor in vendors:
        if vendor.lower() in query:
            receipts = [r for r in receipts if r.vendor_name == vendor]
            filters.append(f"Vendor: {vendor}")
            break
    return receipts, filters


def _apply_category_filter(query: str, receipts: List[ReceiptDB], filters: List[str]) -> Tuple[List[ReceiptDB], List[str]]:
    """Apply category filter (supports German and English)."""
    if category := find_category_in_query(query):
        receipts = [r for r in receipts if r.category == category]
        filters.append(f"Kategorie: {category}")
    return receipts, filters


def _apply_date_filters(query: str, receipts: List[ReceiptDB], filters: List[str]) -> Tuple[List[ReceiptDB], List[str]]:
    """Apply date-based filters."""
    today = datetime.now()
    
    # Last week
    if any(kw in query for kw in DATE_KEYWORDS["week"]):
        cutoff = today - timedelta(days=7)
        receipts = [r for r in receipts if r.date and r.date >= cutoff]
        filters.append("letzte Woche")
    
    # Last month
    elif any(kw in query for kw in DATE_KEYWORDS["month"]):
        cutoff = today - timedelta(days=30)
        receipts = [r for r in receipts if r.date and r.date >= cutoff]
        filters.append("letzter Monat")
    
    # Last year
    elif any(kw in query for kw in DATE_KEYWORDS["year"]):
        cutoff = today - timedelta(days=365)
        receipts = [r for r in receipts if r.date and r.date >= cutoff]
        filters.append("letztes Jahr")
    
    return receipts, filters


def _apply_audit_filters(query: str, receipts: List[ReceiptDB], filters: List[str]) -> Tuple[List[ReceiptDB], List[str]]:
    """Apply audit flag filters."""
    # Duplicates
    if any(kw in query for kw in AUDIT_KEYWORDS["duplicate"]):
        receipts = [r for r in receipts if r.flag_duplicate]
        filters.append("Duplikate")
    
    # Suspicious
    if any(kw in query for kw in AUDIT_KEYWORDS["suspicious"]):
        receipts = [r for r in receipts if r.flag_suspicious]
        filters.append("Verdächtig")
    
    # Missing VAT
    if any(kw in query for kw in AUDIT_KEYWORDS["missing_vat"]):
        receipts = [r for r in receipts if r.flag_missing_vat]
        filters.append("Fehlende MwSt")
    
    # Math error
    if any(kw in query for kw in AUDIT_KEYWORDS["math_error"]):
        receipts = [r for r in receipts if r.flag_math_error]
        filters.append("Rechenfehler")
    
    # All issues
    if any(kw in query for kw in AUDIT_KEYWORDS["all_issues"]):
        receipts = [r for r in receipts if any([
            r.flag_duplicate, r.flag_suspicious, r.flag_missing_vat, r.flag_math_error
        ])]
        filters.append("Alle Audit-Probleme")
    
    return receipts, filters


# =============================================================================
# STATISTICS
# =============================================================================

def _calculate_statistics(receipts: List[ReceiptDB], filters: List[str]) -> Dict:
    """Calculate statistics from filtered receipts."""
    total = sum(r.total_amount for r in receipts)
    count = len(receipts)
    avg = total / count if count > 0 else 0
    
    # Min/Max
    min_receipt = min(receipts, key=lambda r: r.total_amount) if receipts else None
    max_receipt = max(receipts, key=lambda r: r.total_amount) if receipts else None
    
    # Top vendors
    vendor_totals = {}
    for r in receipts:
        vendor_totals[r.vendor_name] = vendor_totals.get(r.vendor_name, 0) + r.total_amount
    top_vendors = sorted(vendor_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Top categories
    category_totals = {}
    for r in receipts:
        cat = r.category or "Sonstiges"
        category_totals[cat] = category_totals.get(cat, 0) + r.total_amount
    top_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "result": {
            "total": round(total, 2),
            "count": count,
            "average": round(avg, 2),
            "filter": " + ".join(filters) if filters else "alle Quittungen",
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
                for r in receipts[:20]
            ]
        }
    }
