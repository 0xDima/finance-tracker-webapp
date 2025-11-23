from datetime import date, timedelta
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


from db import Base, engine, SessionLocal
from sqlalchemy.orm import Session
import models
from models import Transaction

# Create database tables (only creates them if they don't exist)
Base.metadata.create_all(bind=engine)


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




def get_db():
    db = SessionLocal()
    try:
        yield db

    finally:
        db.close()









# -- routes




@app.get("/")
def read_root():
    return {"message": "My finance app is running"}

@app.get("/transactions")
def transactions_page(
    request: Request, 
    db: Session = Depends(get_db)
):
    

    # Query all transactions
    transactions = db.query(Transaction).order_by(Transaction.date.desc()).all()
    print (transactions[0].id)
    return templates.TemplateResponse(
        "transactions.html",
        {
            "request": request,
            "transactions": transactions,
        },
    )


@app.post("/add-test-transaction")
def add_test_transaction(db: Session = Depends(get_db)):

    test_tx = Transaction(
        date=date.today(),
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