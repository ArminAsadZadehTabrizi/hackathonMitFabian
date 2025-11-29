from fastapi import APIRouter
from sqlmodel import Session, select, func
from typing import Annotated
from fastapi import Depends

from database import get_session
from models import Receipt

# Type alias for dependency injection
SessionDep = Annotated[Session, Depends(get_session)]

# Create router for analytics endpoints
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
def get_analytics_summary(session: SessionDep):
    """
    Get comprehensive analytics summary for the frontend.
    
    Returns:
        Summary with total spending, receipts, VAT, averages, monthly data, categories, and vendors
    """
    # Get all receipts
    all_receipts = session.exec(select(Receipt)).all()
    
    # Calculate summary statistics
    total_spending = sum(r.total_amount for r in all_receipts)
    total_receipts = len(all_receipts)
    total_vat = sum(r.tax_amount for r in all_receipts if r.tax_amount)
    avg_receipt_value = total_spending / total_receipts if total_receipts > 0 else 0
    
    # Monthly analytics
    monthly_statement = (
        select(
            func.strftime("%Y-%m", Receipt.date).label("month"),
            func.sum(Receipt.total_amount).label("total"),
            func.count(Receipt.id).label("count")
        )
        .group_by(func.strftime("%Y-%m", Receipt.date))
        .order_by(func.strftime("%Y-%m", Receipt.date))
    )
    monthly_results = session.exec(monthly_statement).all()
    
    # Category analytics
    category_statement = (
        select(
            Receipt.category,
            func.sum(Receipt.total_amount).label("total"),
            func.count(Receipt.id).label("count")
        )
        .where(Receipt.category.is_not(None))
        .group_by(Receipt.category)
        .order_by(func.sum(Receipt.total_amount).desc())
    )
    category_results = session.exec(category_statement).all()
    
    # Vendor analytics
    vendor_statement = (
        select(
            Receipt.vendor_name,
            func.sum(Receipt.total_amount).label("total"),
            func.count(Receipt.id).label("count")
        )
        .group_by(Receipt.vendor_name)
        .order_by(func.sum(Receipt.total_amount).desc())
        .limit(10)  # Top 10 vendors
    )
    vendor_results = session.exec(vendor_statement).all()
    
    return {
        "summary": {
            "totalSpending": round(float(total_spending), 2),
            "totalReceipts": total_receipts,
            "totalVAT": round(float(total_vat), 2),
            "avgReceiptValue": round(float(avg_receipt_value), 2)
        },
        "monthly": [
            {
                "month": month,
                "amount": round(float(total), 2),
                "count": count
            }
            for month, total, count in monthly_results
        ],
        "categories": [
            {
                "category": category,
                "amount": round(float(total), 2),
                "count": count
            }
            for category, total, count in category_results
        ],
        "vendors": [
            {
                "vendor": vendor,
                "amount": round(float(total), 2),
                "count": count
            }
            for vendor, total, count in vendor_results
        ]
    }


@router.get("/monthly")
def get_monthly_analytics(session: SessionDep):
    """
    Get monthly analytics: total amount per month (YYYY-MM).
    
    Returns:
        List of {month: "YYYY-MM", total: float}
    """
    # SQLite uses strftime for date formatting
    # %Y-%m gives us YYYY-MM format
    statement = (
        select(
            func.strftime("%Y-%m", Receipt.date).label("month"),
            func.sum(Receipt.total_amount).label("total")
        )
        .group_by(func.strftime("%Y-%m", Receipt.date))
        .order_by(func.strftime("%Y-%m", Receipt.date))
    )
    
    results = session.exec(statement).all()
    
    return {
        "monthly_totals": [
            {"month": month, "total": round(float(total), 2)}
            for month, total in results
        ]
    }


@router.get("/category")
def get_category_analytics(session: SessionDep):
    """
    Get category analytics: total amount per category.
    
    Returns:
        List of {category: str, total: float}
    """
    statement = (
        select(
            Receipt.category,
            func.sum(Receipt.total_amount).label("total")
        )
        .where(Receipt.category.is_not(None))
        .group_by(Receipt.category)
        .order_by(func.sum(Receipt.total_amount).desc())
    )
    
    results = session.exec(statement).all()
    
    return {
        "category_totals": [
            {"category": category, "total": round(float(total), 2)}
            for category, total in results
        ]
    }
