# routes_transactions.py
"""
Routes related to transactions list and simple debug helpers.
"""

from datetime import date, datetime, timedelta
from typing import List

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy import func, case
from urllib.parse import urlencode

from models import Transaction
from app.deps import get_db, templates

from app.services.import_helpers import get_month_range

router = APIRouter()


# Convert amount filters safely
def parse_optional_float(value: str) -> float | None:
    value = value.strip()
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_optional_date(s: str | None) -> date | None:
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").date()




@router.get("/transactions", response_class=HTMLResponse)
def transactions_page(
    request: Request,
    month: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    search: str | None = Query(None),
    category: List[str] = Query(default=[]),
    account: List[str] = Query(default=[]),
    min_amount: str = Query(""),
    max_amount: str = Query(""),
    sort: str = Query("date"),
    dir: str = Query("desc"),
    db: Session = Depends(get_db),
):

    if start_date and end_date:
        range_start = start_date
        range_end_exclusive = end_date + timedelta(days=1)
        normalized_month = None
    elif month:
        range_start, range_end_exclusive, normalized_month = get_month_range(month)
    else:
        range_start, range_end_exclusive, normalized_month = get_month_range(None)

    # Base query (NO order_by here)
    query = db.query(Transaction).filter(
        Transaction.date >= range_start,
        Transaction.date < range_end_exclusive,
    )

    # Search
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Transaction.description.ilike(pattern),
                Transaction.notes.ilike(pattern),
            )
        )

    # Category filter (supports "None")
    if category:
        cat_conditions = []
        for cat in category:
            if cat == "None":
                cat_conditions.append(Transaction.category.is_(None))
            else:
                cat_conditions.append(Transaction.category == cat)
        query = query.filter(or_(*cat_conditions))

    # Categories for dropdown (includes None)
    all_categories_rows = (
        db.query(Transaction.category)
        .distinct()
        .order_by(Transaction.category.is_(None), Transaction.category)
        .all()
    )
    all_categories = [row[0] if row[0] is not None else "None" for row in all_categories_rows]

    # Account filter (supports "None")
    if account:
        acc_conditions = []
        for acc in account:
            if acc == "None":
                acc_conditions.append(Transaction.account_name.is_(None))
            else:
                acc_conditions.append(Transaction.account_name == acc)
        query = query.filter(or_(*acc_conditions))

    # Accounts for dropdown (includes None)
    all_accounts_rows = (
        db.query(Transaction.account_name)
        .distinct()
        .order_by(Transaction.account_name.is_(None), Transaction.account_name)
        .all()
    )
    all_accounts = [row[0] if row[0] is not None else "None" for row in all_accounts_rows]

    # Amount parsing + filters
    min_amount_val = parse_optional_float(min_amount)
    max_amount_val = parse_optional_float(max_amount)

    if min_amount_val is not None:
        query = query.filter(Transaction.amount_eur >= min_amount_val)

    if max_amount_val is not None:
        query = query.filter(Transaction.amount_eur <= max_amount_val)

    # Totals for filtered view (before sorting/pagination)
    income_sum, expense_sum, net_sum = db.query(
        func.coalesce(func.sum(case((Transaction.amount_eur > 0, Transaction.amount_eur), else_=0.0)), 0.0),
        func.coalesce(func.sum(case((Transaction.amount_eur < 0, Transaction.amount_eur), else_=0.0)), 0.0),
        func.coalesce(func.sum(Transaction.amount_eur), 0.0),
    ).select_from(Transaction).filter(*query._where_criteria).one()

    # Sorting (single order_by applied once)
    sort_key = sort if sort in {"date", "amount"} else "date"
    sort_dir = dir if dir in {"asc", "desc"} else "desc"
    sort_col = Transaction.amount_eur if sort_key == "amount" else Transaction.date
    query = query.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())

    def build_sort_url(column: str) -> str:
        next_dir = "asc" if (sort_key == column and sort_dir == "desc") else "desc"

        # ✅ Keep ALL existing params, including repeated ones (category/account)
        items = list(request.query_params.multi_items())

        # Remove old sort/dir if present (could exist multiple times)
        items = [(k, v) for (k, v) in items if k not in ("sort", "dir")]

        # Add new sort/dir
        items.append(("sort", column))
        items.append(("dir", next_dir))

        # ✅ Properly URL-encode + keep repeated params
        return "/transactions?" + urlencode(items, doseq=True)

    transactions = query.all()

    return templates.TemplateResponse(
        "transactions.html",
        {
            "request": request,
            "transactions": transactions,
            "current_month": normalized_month,
            "search": search or "",
            "all_categories": all_categories,
            "selected_categories": category,
            "all_accounts": all_accounts,
            "selected_accounts": account,
            "min_amount": min_amount,
            "max_amount": max_amount,
            "income_sum": float(income_sum),
            "expense_sum": float(expense_sum),
            "net_sum": float(net_sum),
            "sort": sort_key,
            "dir": sort_dir,
            "date_sort_url": build_sort_url("date"),
            "amount_sort_url": build_sort_url("amount"),
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