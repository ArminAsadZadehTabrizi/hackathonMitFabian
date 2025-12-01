"""
Formatters - Helper functions for formatting data for API responses.
"""
from typing import List, Optional
from models.db_models import ReceiptDB, LineItemDB


def format_receipt_for_api(
    receipt: ReceiptDB,
    line_items: List[LineItemDB],
    base_url: str = "http://localhost:8000"
) -> dict:
    """
    Formats a single receipt for API response (frontend format).
    
    Args:
        receipt: The receipt database object
        line_items: List of line items for this receipt
        base_url: Base URL for image paths
    
    Returns:
        Formatted receipt dictionary
    """
    # Build image URL
    image_url = f"{base_url}/api/images/{receipt.image_path}" if receipt.image_path else None
    
    # Determine status based on flags
    if receipt.flag_duplicate:
        status = "duplicate"
    elif any([receipt.flag_suspicious, receipt.flag_missing_vat, receipt.flag_math_error]):
        status = "flagged"
    else:
        status = "verified"
    
    return {
        "id": str(receipt.id),
        "receiptNumber": f"RCP-{receipt.id:04d}",
        "vendor": receipt.vendor_name,
        "vendorVAT": None,
        "date": receipt.date.isoformat() if receipt.date else None,
        "total": float(receipt.total_amount),
        "subtotal": float(receipt.total_amount - (receipt.tax_amount or 0)),
        "vat": float(receipt.tax_amount) if receipt.tax_amount else None,
        "vatRate": None,
        "paymentMethod": None,
        "category": receipt.category or "Sonstiges",
        "currency": receipt.currency,
        "imageUrl": image_url,
        "lineItems": [format_line_item(item) for item in line_items],
        "status": status,
        "tags": [],
        "notes": None,
        "createdAt": receipt.date.isoformat() if receipt.date else None,
        "updatedAt": receipt.date.isoformat() if receipt.date else None,
        "auditFlags": {
            "isDuplicate": receipt.flag_duplicate,
            "hasTotalMismatch": receipt.flag_math_error,
            "missingVAT": receipt.flag_missing_vat,
            "suspiciousCategory": "Alkohol" if receipt.flag_suspicious else None
        }
    }


def format_line_item(item: LineItemDB) -> dict:
    """Formats a single line item for API response."""
    return {
        "id": str(item.id),
        "description": item.description,
        "quantity": 1,
        "unitPrice": float(item.amount),
        "total": float(item.amount),
        "vat": 0
    }


def format_audit_finding(receipt: ReceiptDB, line_items: List[LineItemDB]) -> dict:
    """
    Formats a receipt as an audit finding.
    
    Args:
        receipt: The receipt database object
        line_items: List of line items for this receipt
    
    Returns:
        Formatted audit finding dictionary
    """
    items_sum = sum(item.amount for item in line_items)
    
    # Determine the issue type
    if receipt.flag_duplicate:
        issue = "Duplicate receipt"
    elif receipt.flag_math_error:
        issue = "Math error"
    elif receipt.flag_missing_vat:
        issue = "Missing VAT"
    elif receipt.flag_suspicious:
        issue = "Suspicious category"
    else:
        issue = None
    
    return {
        "receiptId": str(receipt.id),
        "receiptNumber": f"RCP-{receipt.id:04d}",
        "vendor": receipt.vendor_name,
        "date": receipt.date.isoformat() if receipt.date else None,
        "total": receipt.total_amount,
        "expectedTotal": items_sum if receipt.flag_math_error else None,
        "actualTotal": receipt.total_amount if receipt.flag_math_error else None,
        "difference": abs(items_sum - receipt.total_amount) if receipt.flag_math_error else None,
        "category": receipt.category or "Sonstiges",
        "issue": issue
    }


def format_chat_receipt(receipt: ReceiptDB) -> dict:
    """
    Formats a receipt for chat response.
    
    Args:
        receipt: The receipt database object
    
    Returns:
        Formatted receipt dictionary for chat
    """
    return {
        "id": str(receipt.id),
        "receiptNumber": f"RCP-{receipt.id:04d}",
        "vendor": receipt.vendor_name,
        "date": receipt.date.isoformat() if receipt.date else "",
        "total": receipt.total_amount,
        "category": receipt.category or "Sonstiges"
    }


def format_analytics_category(category: str, amount: float, count: int) -> dict:
    """Formats category analytics data."""
    return {
        "category": category,
        "amount": round(float(amount), 2),
        "count": count
    }


def format_analytics_vendor(vendor: str, amount: float, count: int) -> dict:
    """Formats vendor analytics data."""
    return {
        "vendor": vendor,
        "amount": round(float(amount), 2),
        "count": count
    }


def format_analytics_monthly(month: str, amount: float, count: int = None) -> dict:
    """Formats monthly analytics data."""
    result = {
        "month": month,
        "amount": round(float(amount), 2)
    }
    if count is not None:
        result["count"] = count
    return result

