"""
Audit-Service für Quittungs-Validierung
Integriert von Partner 2's Backend
"""
from sqlmodel import Session, select
from models.db_models import ReceiptDB, LineItemDB


def run_audit(receipt: ReceiptDB, items: list[LineItemDB], db: Session) -> ReceiptDB:
    """
    Führt Audit-Checks auf einer Quittung und ihren Line Items durch.
    
    Aktualisiert Audit-Flags:
    - flag_missing_vat: True wenn tax_amount fehlt oder 0 ist
    - flag_math_error: True wenn Summe der Line Items != total_amount (Toleranz 0.01)
    - flag_suspicious: True wenn Line Items Alkohol/Tabak-Keywords enthalten
    - flag_duplicate: True wenn Quittung mit gleichem Vendor, Datum und Betrag existiert
    
    Args:
        receipt: Receipt-Objekt für Audit
        items: Liste der LineItem-Objekte
        db: Datenbank-Session
        
    Returns:
        Aktualisiertes Receipt-Objekt mit gesetzten Audit-Flags
    """
    
    # 1. Check für fehlende MwSt
    if receipt.tax_amount is None or receipt.tax_amount == 0:
        receipt.flag_missing_vat = True
    
    # 2. Check für Rechenfehler
    items_total = sum(item.amount for item in items)
    if abs(items_total - receipt.total_amount) > 0.01:
        receipt.flag_math_error = True
    
    # 3. Check für verdächtige Items (Alkohol/Tabak)
    suspicious_keywords = [
        "alcohol", "beer", "wine", "tobacco", "cigarettes", 
        "vodka", "whiskey", "rum", "alkohol", "bier", "wein",
        "zigaretten", "tabak"
    ]
    for item in items:
        if any(keyword in item.description.lower() for keyword in suspicious_keywords):
            receipt.flag_suspicious = True
            break
    
    # 4. Check für Duplikate
    statement = select(ReceiptDB).where(
        ReceiptDB.vendor_name == receipt.vendor_name,
        ReceiptDB.date == receipt.date,
        ReceiptDB.total_amount == receipt.total_amount,
        ReceiptDB.id != receipt.id  # Exclude current receipt
    )
    existing_receipt = db.exec(statement).first()
    if existing_receipt:
        receipt.flag_duplicate = True
    
    return receipt

