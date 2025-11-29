"""
Quittungen aus der Datenbank extrahieren und analysieren.

Dieses Script kann:
1. Quittungen direkt aus der SQLite-Datenbank lesen
2. Quittungen über die API abrufen
3. Statistik-Report generieren
4. Daten als JSON/CSV exportieren
"""

import json
import csv
from datetime import datetime
from typing import List, Dict, Optional
import sys
from pathlib import Path

# Datenbank-Importe
from sqlmodel import Session, select, func
from services.database import engine, init_db
from models.db_models import ReceiptDB, LineItemDB

# Für API-Aufrufe
try:
    import requests
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    print("⚠️  requests nicht installiert - API-Modus nicht verfügbar")


def get_receipts_from_db() -> List[ReceiptDB]:
    """Holt alle Quittungen direkt aus der Datenbank."""
    init_db()
    with Session(engine) as session:
        statement = select(ReceiptDB)
        receipts = session.exec(statement).all()
        return list(receipts)


def get_receipts_from_api(base_url: str = "http://localhost:8000") -> List[Dict]:
    """Holt Quittungen über die API."""
    if not API_AVAILABLE:
        raise ImportError("requests library nicht installiert. Installiere mit: pip install requests")
    
    try:
        response = requests.get(f"{base_url}/api/receipts")
        response.raise_for_status()
        data = response.json()
        return data.get("receipts", [])
    except requests.exceptions.ConnectionError:
        print(f"❌ Verbindung zu {base_url} fehlgeschlagen. Nutze direkten DB-Zugriff.")
        return []


def get_line_items_for_receipt(receipt_id: int) -> List[LineItemDB]:
    """Holt alle Line Items für eine Quittung."""
    with Session(engine) as session:
        statement = select(LineItemDB).where(LineItemDB.receipt_id == receipt_id)
        items = session.exec(statement).all()
        return list(items)


def analyze_receipts(receipts: List[ReceiptDB]) -> Dict:
    """Analysiert Quittungen und erstellt Statistiken."""
    total_count = len(receipts)
    
    if total_count == 0:
        return {"error": "Keine Quittungen gefunden"}
    
    # Grundstatistiken
    total_amount = sum(r.total_amount for r in receipts)
    total_tax = sum(r.tax_amount for r in receipts)
    
    # Audit-Flags zählen
    flagged_duplicate = sum(1 for r in receipts if r.flag_duplicate)
    flagged_suspicious = sum(1 for r in receipts if r.flag_suspicious)
    flagged_missing_vat = sum(1 for r in receipts if r.flag_missing_vat)
    flagged_math_error = sum(1 for r in receipts if r.flag_math_error)
    flagged_any = sum(1 for r in receipts if any([
        r.flag_duplicate, r.flag_suspicious, r.flag_missing_vat, r.flag_math_error
    ]))
    
    # Kategorien
    categories = {}
    for r in receipts:
        cat = r.category or "Keine Kategorie"
        categories[cat] = categories.get(cat, 0) + 1
    
    # Vendors
    vendors = {}
    for r in receipts:
        vendors[r.vendor_name] = vendors.get(r.vendor_name, 0) + 1
    
    # Datum-Statistiken
    dates = [r.date for r in receipts if r.date]
    min_date = min(dates) if dates else None
    max_date = max(dates) if dates else None
    
    # Durchschnittswerte
    avg_amount = total_amount / total_count if total_count > 0 else 0
    avg_tax = total_tax / total_count if total_count > 0 else 0
    
    return {
        "statistics": {
            "total_receipts": total_count,
            "total_amount": round(total_amount, 2),
            "total_tax": round(total_tax, 2),
            "average_amount": round(avg_amount, 2),
            "average_tax": round(avg_tax, 2),
            "date_range": {
                "from": min_date.isoformat() if min_date else None,
                "to": max_date.isoformat() if max_date else None
            }
        },
        "audit_flags": {
            "duplicate": flagged_duplicate,
            "suspicious": flagged_suspicious,
            "missing_vat": flagged_missing_vat,
            "math_error": flagged_math_error,
            "any_flag": flagged_any,
            "clean_receipts": total_count - flagged_any
        },
        "by_category": dict(sorted(categories.items(), key=lambda x: x[1], reverse=True)),
        "by_vendor": dict(sorted(vendors.items(), key=lambda x: x[1], reverse=True)),
        "flagged_receipts_count": flagged_any
    }


def export_to_json(receipts: List[ReceiptDB], output_file: str = "receipts_export.json"):
    """Exportiert Quittungen als JSON."""
    data = []
    with Session(engine) as session:
        for receipt in receipts:
            items = get_line_items_for_receipt(receipt.id)
            receipt_dict = {
                "id": receipt.id,
                "vendor_name": receipt.vendor_name,
                "date": receipt.date.isoformat() if receipt.date else None,
                "total_amount": receipt.total_amount,
                "tax_amount": receipt.tax_amount,
                "currency": receipt.currency,
                "category": receipt.category,
                "audit_flags": {
                    "duplicate": receipt.flag_duplicate,
                    "suspicious": receipt.flag_suspicious,
                    "missing_vat": receipt.flag_missing_vat,
                    "math_error": receipt.flag_math_error
                },
                "line_items": [
                    {
                        "id": item.id,
                        "description": item.description,
                        "amount": item.amount
                    }
                    for item in items
                ]
            }
            data.append(receipt_dict)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ {len(data)} Quittungen nach {output_file} exportiert")


def export_to_csv(receipts: List[ReceiptDB], output_file: str = "receipts_export.csv"):
    """Exportiert Quittungen als CSV."""
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            "ID", "Vendor", "Datum", "Gesamtbetrag", "MwSt", "Währung",
            "Kategorie", "Duplikat", "Verdächtig", "MwSt fehlt", "Rechenfehler",
            "Anzahl Items"
        ])
        
        # Daten
        with Session(engine) as session:
            for receipt in receipts:
                items = get_line_items_for_receipt(receipt.id)
                writer.writerow([
                    receipt.id,
                    receipt.vendor_name,
                    receipt.date.isoformat() if receipt.date else "",
                    receipt.total_amount,
                    receipt.tax_amount,
                    receipt.currency,
                    receipt.category or "",
                    "✓" if receipt.flag_duplicate else "",
                    "✓" if receipt.flag_suspicious else "",
                    "✓" if receipt.flag_missing_vat else "",
                    "✓" if receipt.flag_math_error else "",
                    len(items)
                ])
    
    print(f"✅ {len(receipts)} Quittungen nach {output_file} exportiert")


def print_statistics(analysis: Dict):
    """Gibt Statistiken formatiert aus."""
    print("\n" + "="*60)
    print("📊 QUITTUNGS-ANALYSE REPORT")
    print("="*60)
    
    stats = analysis.get("statistics", {})
    print(f"\n📈 Grundstatistiken:")
    print(f"   Gesamtanzahl Quittungen: {stats.get('total_receipts', 0)}")
    print(f"   Gesamtbetrag: {stats.get('total_amount', 0):.2f} EUR")
    print(f"   Gesamte MwSt: {stats.get('total_tax', 0):.2f} EUR")
    print(f"   Durchschnitt pro Quittung: {stats.get('average_amount', 0):.2f} EUR")
    
    date_range = stats.get('date_range', {})
    if date_range.get('from'):
        print(f"   Zeitraum: {date_range['from'][:10]} bis {date_range['to'][:10]}")
    
    audit = analysis.get("audit_flags", {})
    print(f"\n✅ Audit-Flags:")
    print(f"   ✓ Saubere Quittungen: {audit.get('clean_receipts', 0)}")
    print(f"   ⚠️  Duplikate: {audit.get('duplicate', 0)}")
    print(f"   🚨 Verdächtige Items: {audit.get('suspicious', 0)}")
    print(f"   📋 Fehlende MwSt: {audit.get('missing_vat', 0)}")
    print(f"   🧮 Rechenfehler: {audit.get('math_error', 0)}")
    print(f"   ⚠️  Mindestens ein Flag: {audit.get('any_flag', 0)}")
    
    categories = analysis.get("by_category", {})
    if categories:
        print(f"\n📂 Top Kategorien:")
        for cat, count in list(categories.items())[:5]:
            print(f"   {cat}: {count} Quittungen")
    
    vendors = analysis.get("by_vendor", {})
    if vendors:
        print(f"\n🏪 Top Vendors:")
        for vendor, count in list(vendors.items())[:5]:
            print(f"   {vendor}: {count} Quittungen")
    
    print("\n" + "="*60 + "\n")


def main():
    """Hauptfunktion."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Quittungen analysieren und exportieren")
    parser.add_argument("--api", action="store_true", help="Nutze API statt direkten DB-Zugriff")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API Base URL")
    parser.add_argument("--export-json", help="Exportiere als JSON zu dieser Datei")
    parser.add_argument("--export-csv", help="Exportiere als CSV zu dieser Datei")
    parser.add_argument("--stats-only", action="store_true", help="Zeige nur Statistiken")
    
    args = parser.parse_args()
    
    print("🔍 Lade Quittungen...")
    
    # Quittungen holen
    if args.api and API_AVAILABLE:
        receipts_data = get_receipts_from_api(args.api_url)
        if not receipts_data:
            print("⚠️  API zurückgefallen auf DB-Zugriff")
            receipts = get_receipts_from_db()
        else:
            # API-Daten konvertieren (falls nötig)
            receipts = get_receipts_from_db()  # Fallback
            print(f"✅ {len(receipts_data)} Quittungen über API geladen")
    else:
        receipts = get_receipts_from_db()
        print(f"✅ {len(receipts)} Quittungen aus Datenbank geladen")
    
    if not receipts:
        print("❌ Keine Quittungen gefunden!")
        print("   Tipp: Führe zuerst backend/seed.py aus um Testdaten zu generieren")
        sys.exit(1)
    
    # Analyse durchführen
    analysis = analyze_receipts(receipts)
    
    # Statistiken anzeigen
    if not args.export_json and not args.export_csv:
        print_statistics(analysis)
    
    # Export
    if args.export_json:
        export_to_json(receipts, args.export_json)
    
    if args.export_csv:
        export_to_csv(receipts, args.export_csv)
    
    # JSON-Output für Machine-Readable
    if args.stats_only:
        print(json.dumps(analysis, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()


