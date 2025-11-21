from datetime import date, timedelta
from fastapi import FastAPI
from fastapi import Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")



fake_transactions = [
    {
        "id": 1,
        "date": "2025-01-02",
        "account": "Revolut",
        "description": "Coffee shop",
        "amount_original": -3.50,
        "currency_original": "EUR",
        "amount_eur": -3.50,
        "category": "Food & Drinks",
        "notes": "latte"
    },
    {
        "id": 2,
        "date": "2025-01-03",
        "account": "Erste Bank",
        "description": "Salary",
        "amount_original": 950.00,
        "currency_original": "EUR",
        "amount_eur": 950.00,
        "category": "Income",
        "notes": ""
    },
    {
        "id": 3,
        "date": "2025-01-05",
        "account": "Cash",
        "description": "Groceries",
        "amount_original": -28.40,
        "currency_original": "EUR",
        "amount_eur": -28.40,
        "category": "Groceries",
        "notes": ""
    },
    {
        "id": 4,
        "date": "2025-01-07",
        "account": "Revolut",
        "description": "Netflix subscription",
        "amount_original": -9.99,
        "currency_original": "EUR",
        "amount_eur": -9.99,
        "category": "Entertainment",
        "notes": ""
    },
    {
        "id": 5,
        "date": "2025-01-10",
        "account": "PBZ",
        "description": "Student scholarship",
        "amount_original": 300.00,
        "currency_original": "EUR",
        "amount_eur": 300.00,
        "category": "Income",
        "notes": ""
    },
    {
        "id": 6,
        "date": "2025-01-12",
        "account": "Revolut",
        "description": "Fuel",
        "amount_original": -45.00,
        "currency_original": "EUR",
        "amount_eur": -45.00,
        "category": "Transport",
        "notes": ""
    },
    {
        "id": 7,
        "date": "2025-01-15",
        "account": "Cash",
        "description": "Dinner out",
        "amount_original": -18.70,
        "currency_original": "EUR",
        "amount_eur": -18.70,
        "category": "Food & Drinks",
        "notes": ""
    },
    {
        "id": 8,
        "date": "2025-01-18",
        "account": "Erste Bank",
        "description": "Gym membership",
        "amount_original": -27.00,
        "currency_original": "EUR",
        "amount_eur": -27.00,
        "category": "Health",
        "notes": ""
    },
    {
        "id": 9,
        "date": "2025-01-22",
        "account": "Revolut",
        "description": "Electricity bill",
        "amount_original": -55.30,
        "currency_original": "EUR",
        "amount_eur": -55.30,
        "category": "Utilities",
        "notes": ""
    },
    {
        "id": 10,
        "date": "2025-01-28",
        "account": "Erste Bank",
        "description": "Freelance payment",
        "amount_original": 120.00,
        "currency_original": "EUR",
        "amount_eur": 120.00,
        "category": "Income",
        "notes": ""
    },
]




@app.get("/")
def read_root():
    return {"message": "My finance app is running"}

@app.get("/transactions")
def transactions_page(
    request: Request,
    start_date: str | None = None,
    end_date: str | None = None,
):
    # If user didn't pass dates, default to previous month
    if not start_date or not end_date:
        today = date.today()
        first_of_this_month = today.replace(day=1)
        last_of_prev_month = first_of_this_month - timedelta(days=1)
        first_of_prev_month = last_of_prev_month.replace(day=1)

        start_date = first_of_prev_month.isoformat()  # YYYY-MM-DD
        end_date = last_of_prev_month.isoformat()     # YYYY-MM-DD

    # TODO: load all transactions from DB or list
    all_transactions = fake_transactions

    # Filter by date range
    filtered = [
        tx for tx in all_transactions
        if start_date <= tx["date"] <= end_date   # assuming tx["date"] is "YYYY-MM-DD"
    ]

    return templates.TemplateResponse(
        "transactions_new.html",
        {
            "request": request,
            "transactions": all_transactions,
            "start_date": start_date,
            "end_date": end_date,
        },
    )