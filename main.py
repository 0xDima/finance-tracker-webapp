# main.py

from datetime import date, timedelta, datetime

from fastapi import FastAPI, Request, Depends, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from db import Base, engine, SessionLocal
from sqlalchemy.orm import Session
import models
from models import Transaction

from typing import List

import uuid
import os

from services.csv_import import *







PENDING_BATCHES = {}

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
    batch_id = str(uuid.uuid4())

    # Folder: uploads/batch_<id>
    folder = f"uploads/batch_{batch_id}"
    os.makedirs(folder, exist_ok=True)

    saved_paths = []  # store filepaths for later cleanup

    # ---- 2. Save each file to the batch folder ----
    for file, bank in zip(csv_files, banks):
        file_location = os.path.join(folder, file.filename)
        saved_paths.append(file_location)

        with open(file_location, "wb") as f:
            f.write(await file.read())

    # ---- 3. Create batch structure in memory ----
    PENDING_BATCHES[batch_id] = {
        "files": saved_paths,        # paths to saved CSVs
        "transactions": {},          # will be filled by parse_csvs
        "order": [],                 # order of temp IDs
        "banks": banks,              # for reference
    }

    batch = PENDING_BATCHES[batch_id]

    # ---- 4. Call parse_csvs to fill this batch ----
    parse_csvs(batch, batch_id, saved_paths, banks)
    print (
        f"""
        batch: {batch}
        batchId: {batch_id}
        saved_paths: {saved_paths}
        banks: {banks}

    """)


    # For debugging: see what was parsed
    tx_list = [batch["transactions"][tid] for tid in batch["order"]]

    return {
        "batch_id": batch_id,
        "transaction_count": len(tx_list),
        "transactions": tx_list[:10],
    }