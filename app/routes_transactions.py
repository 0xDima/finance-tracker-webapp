# routes_transactions.py
"""
Routes related to transactions list and simple debug helpers.
"""

from datetime import date, datetime
from typing import List

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

from models import Transaction
from app.deps import get_db, templates

from app.services.import_helpers import get_month_range

router = APIRouter()


@router.get("/transactions", response_class=HTMLResponse)
def transactions_page(
    request: Request,
    month: str | None = Query(None),  
    search: str | None = Query(None), 
    category: List[str] = Query(default=[]), 
    db: Session = Depends(get_db),
):
    
    start_date, end_date_exclusive, normalized_month = get_month_range(month)

    query = (
        db.query(Transaction)
        .filter(
            Transaction.date >= start_date,
            Transaction.date < end_date_exclusive,
        )
        .order_by(Transaction.date.desc())
    )

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Transaction.description.ilike(pattern),
                Transaction.notes.ilike(pattern),
            )
        )    

    if category:  # list is non-empty
        query = query.filter(Transaction.category.in_(category))

    all_categories_rows = (
        db.query(Transaction.category)
        .filter(Transaction.category.isnot(None))
        .distinct()
        .order_by(Transaction.category)
        .all()
    )
    all_categories = [row[0] for row in all_categories_rows]

    transactions = query.all()

    return templates.TemplateResponse(
        "transactions.html",
        {
            "request": request,
            "transactions": transactions,
            "current_month": normalized_month,
            "search": search or "",
            "all_categories": all_categories,
            "selected_categories": category,   # <-- NEW
        },
    )


@router.post("/add-test-transaction")
def add_test_transaction(db: Session = Depends(get_db)):
    """
    Debug endpoint: insert one hard-coded test transaction into the DB.
    Useful to test that DB + models + /transactions page are working.
    """
    test_tx = Transaction(
        date = date.today(),
        description="Test transaction",
        currency_original="EUR",
        amount_original=-10.0,
        amount_eur=-10.0,
        account_name="Test Account",
        category=None,
        notes=None,
    )

    db.add(test_tx)
    db.commit()
    db.refresh(test_tx)

    return {"message": "Test transaction added", "id": test_tx.id}