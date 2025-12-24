# app/routes_dashboard.py

from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import date

from .deps import templates, get_db
from models import Transaction

router = APIRouter()


@router.get("/dashboard")
def dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
):
    today = date.today()

    # Previous month range: [month_start, next_month_start)
    if today.month == 1:
        month_start = date(today.year - 1, 12, 1)
        next_month_start = date(today.year, 1, 1)
    else:
        month_start = date(today.year, today.month - 1, 1)
        next_month_start = date(today.year, today.month, 1)

    month_label = month_start.strftime("%B %Y")

    # Import indicator: any tx exist in previous month
    tx_count_month = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.date >= month_start, Transaction.date < next_month_start)
        .scalar()
        or 0
    )
    previous_month_imported = tx_count_month > 0

    # Monthly totals
    income_eur, expenses_eur = (
        db.query(
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.amount_eur > 0, Transaction.amount_eur),
                        else_=0.0,
                    )
                ),
                0.0,
            ).label("income_eur"),
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.amount_eur < 0, Transaction.amount_eur),
                        else_=0.0,
                    )
                ),
                0.0,
            ).label("expenses_eur"),
        )
        .filter(Transaction.date >= month_start, Transaction.date < next_month_start)
        .one()
    )

    income_eur = float(income_eur)
    expenses_eur = float(expenses_eur)  # negative
    net_eur = income_eur + expenses_eur

    # Spending by category (expenses only)
    category_key = func.coalesce(Transaction.category, "Uncategorized")

    rows = (
        db.query(
            category_key.label("category"),
            func.coalesce(func.sum(func.abs(Transaction.amount_eur)), 0.0).label("spent"),
        )
        .filter(
            Transaction.date >= month_start,
            Transaction.date < next_month_start,
            Transaction.amount_eur < 0,
        )
        .group_by(category_key)
        .order_by(func.sum(func.abs(Transaction.amount_eur)).desc())
        .all()
    )

    spending_by_category = [{"label": r.category, "value": float(r.spent)} for r in rows]
    total_spent_eur = sum(item["value"] for item in spending_by_category)

    # ✅ Recent transactions: 10 biggest by absolute value in the month
    recent_transactions = (
        db.query(Transaction)
        .filter(Transaction.date >= month_start, Transaction.date < next_month_start)
        .order_by(func.abs(Transaction.amount_eur).desc(), Transaction.date.desc())
        .limit(10)
        .all()
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "today": today,
            "month_label": month_label,
            "income_eur": income_eur,
            "expenses_eur": expenses_eur,
            "net_eur": net_eur,
            "spending_by_category": spending_by_category,
            "total_spent_eur": float(total_spent_eur),
            "previous_month_imported": previous_month_imported,
            "tx_count_month": int(tx_count_month),
            "month_start_iso": month_start.isoformat(),
            "next_month_start_iso": next_month_start.isoformat(),
            "recent_transactions": recent_transactions,
        },
    )