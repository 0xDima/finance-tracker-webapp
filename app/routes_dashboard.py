# app/routes_dashboard.py

from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from datetime import date

from .deps import templates, get_db
from models import Transaction  

router = APIRouter()


@router.get("/dashboard")
def dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Minimal dashboard page: 
    - shows today's date
    - placeholder cards for stocks/crypto
    - placeholder for recent transactions
    """

    today = date.today()

    # In the next steps we'll calculate:
    # - current month total income/expenses
    # - previous month status
    # - last 10 transactions
    # But for now: placeholders.

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "today": today,
        },
    )