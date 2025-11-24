# main.py

from datetime import date, timedelta
from fastapi import FastAPI, Request, Depends, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from db import Base, engine, SessionLocal
from sqlalchemy.orm import Session
import models
from models import Transaction

from typing import List




# Create database tables (only creates them if they don't exist)
Base.metadata.create_all(bind=engine)


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")




# get database session
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


@app.get("/upload")
def upload_page(request: Request):
    return templates.TemplateResponse(
        "upload.html",
        {"request": request}
    )

@app.post("/upload")
async def upload_process(
    request: Request,
    csv_files: List[UploadFile] = File(...),
    banks: List[str] = Form(...),
    db: Session = Depends(get_db),
):
    processed = []

    for file, bank in zip(csv_files, banks):
        content_bytes = await file.read()
        text = content_bytes.decode("utf-8", errors="ignore")
        lines = text.splitlines()

        # TODO: here later you will parse CSV into transactions
        # For now we just return some basic info
        processed.append({
            "filename": file.filename,
            "bank": bank,
            "line_count": len(lines),
        })

    # For now, just return JSON so you see it works
    return {"processed": processed}