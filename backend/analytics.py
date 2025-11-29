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
