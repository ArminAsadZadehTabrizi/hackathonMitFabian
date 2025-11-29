from sqlmodel import Session, select
from models import Receipt, LineItem


def run_audit(receipt: Receipt, items: list[LineItem], db: Session) -> Receipt:
    """
    Run audit checks on a receipt and its line items.
    
    Updates audit flags:
    - flag_missing_vat: True if tax_amount is None or 0
    - flag_math_error: True if sum of line items != total_amount (tolerance 0.01)
    - flag_suspicious: True if line items contain alcohol/tobacco keywords
    - flag_duplicate: True if receipt with same vendor, date, and amount exists
    
    Args:
        receipt: Receipt object to audit
        items: List of LineItem objects belonging to the receipt
        db: Database session
        
    Returns:
        Updated receipt object with audit flags set
    """
    
    # 1. Check for missing VAT
    if receipt.tax_amount is None or receipt.tax_amount == 0:
        receipt.flag_missing_vat = True
    
    # 2. Check for math errors
    items_total = sum(item.amount for item in items)
    if abs(items_total - receipt.total_amount) > 0.01:
        receipt.flag_math_error = True
    
    # 3. Check for suspicious items (alcohol/tobacco)
    suspicious_keywords = ["alcohol", "beer", "wine", "tobacco", "cigarettes", "vodka", "whiskey", "rum"]
    for item in items:
        if any(keyword in item.description.lower() for keyword in suspicious_keywords):
            receipt.flag_suspicious = True
            break
    
    # 4. Check for duplicates
    statement = select(Receipt).where(
        Receipt.vendor_name == receipt.vendor_name,
        Receipt.date == receipt.date,
        Receipt.total_amount == receipt.total_amount,
        Receipt.id != receipt.id  # Exclude current receipt
    )
    existing_receipt = db.exec(statement).first()
    if existing_receipt:
        receipt.flag_duplicate = True
    
    return receipt
