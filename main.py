# main.py

from datetime import date, timedelta, datetime
import re

from fastapi import FastAPI, Request, Depends, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

from db import Base, engine, SessionLocal
from sqlalchemy.orm import Session
import models
from models import Transaction

from typing import List, Any, Optional, Dict

import uuid
import os

from services.csv_import import *

from services.import_helpers import build_transaction_from_dict





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
        "transactions": tx_list,
    }



@app.post("/upload/preview", response_class=HTMLResponse)
async def upload_preview(
    request: Request,
    csv_files: List[UploadFile] = File(...),
    banks: List[str] = Form(...),
):
    # 1) Create a new batch id
    batch_id = str(uuid.uuid4())

    # 2) Create folder uploads/batch_<id>
    folder = f"uploads/batch_{batch_id}"
    os.makedirs(folder, exist_ok=True)

    saved_paths = []

    # 3) Save each uploaded CSV into the batch folder
    for file, bank in zip(csv_files, banks):
        file_location = os.path.join(folder, file.filename)
        saved_paths.append(file_location)

        with open(file_location, "wb") as f:
            f.write(await file.read())

    # 4) Initialize batch entry in memory
    PENDING_BATCHES[batch_id] = {
        "files": saved_paths,
        "transactions": {},
        "order": [],
        "banks": banks,
    }

    batch = PENDING_BATCHES[batch_id]

    # 5) Parse CSVs and fill the batch with normalized transactions
    parse_csvs(batch, batch_id, saved_paths, banks)

    # 6) Build a list of transactions including temp_id for the template
    transactions_for_template = []
    for temp_id in batch["order"]:
        tx_data = batch["transactions"][temp_id].copy()
        tx_data["temp_id"] = temp_id
        transactions_for_template.append(tx_data)

        
    # 7) Render preview page with real data
    return templates.TemplateResponse(
        "upload_preview.html",
        {
            "request": request,
            "batch_id": batch_id,
            "transactions": transactions_for_template,
        },
    )



TRANSACTION_KEY_RE = re.compile(
    r"^transactions\[(?P<temp_id>.+?)\]\[(?P<field>.+?)\]$"
)

@app.post("/upload/review", response_class=HTMLResponse)
async def upload_review(request: Request):
    """
    Receive edited transactions from the preview page.
    - Parse nested field names like transactions[t1][date]
    - Apply delete_ids
    - Convert numeric fields
    - Show read-only review page with 'Back' + 'Save to database'
    """

    form = await request.form()

    batch_id = form.get("batch_id")
    delete_ids: List[str] = form.getlist("delete_ids")

    # 1) Rebuild raw_tx: { "t1": { "date": "...", "category": "...", ... }, ... }
    raw_tx: Dict[str, Dict[str, Any]] = {}

    for key, value in form.items():
        match = TRANSACTION_KEY_RE.match(key)
        if not match:
            continue

        temp_id = match.group("temp_id")
        field = match.group("field")

        if temp_id not in raw_tx:
            raw_tx[temp_id] = {}

        raw_tx[temp_id][field] = value

    # 2) Clean + convert + skip deleted
    cleaned: List[Dict[str, Any]] = []

    for temp_id, tx_data in raw_tx.items():
        if temp_id in delete_ids:
            continue

        # Build a very explicit dict so we know what goes to the template
        tx: Dict[str, Any] = {
            "temp_id": temp_id,
            "date": tx_data.get("date") or "",
            "account_name": tx_data.get("account_name") or "",
            "description": tx_data.get("description") or "",
            "currency_original": tx_data.get("currency_original") or "",
            "category": tx_data.get("category") or "",      # 👈 ensure category exists
            "notes": tx_data.get("notes") or "",
        }

        # amount_original
        try:
            tx["amount_original"] = float(tx_data.get("amount_original"))
        except Exception:
            tx["amount_original"] = None

        # amount_eur
        try:
            raw_eur = tx_data.get("amount_eur")
            tx["amount_eur"] = float(raw_eur) if raw_eur not in (None, "", "None") else None
        except Exception:
            tx["amount_eur"] = None

        cleaned.append(tx)

    # 3) Save into pending batches for /upload/save-batch
    if batch_id:
        if batch_id not in PENDING_BATCHES:
            PENDING_BATCHES[batch_id] = {}
        PENDING_BATCHES[batch_id]["final"] = cleaned

    # 4) Render read-only review page
    return templates.TemplateResponse(
        "upload_review.html",
        {
            "request": request,
            "batch_id": batch_id,
            "transactions": cleaned,
        },
    )


# On success: go to the main transactions page
@app.post("/upload/save-batch")
async def save_batch(batch_id: str = Form(...)):
    """
    FINAL VERSION:
    - Take cleaned tx dicts from PENDING_BATCHES[batch_id]["final"]
    - Convert each dict -> Transaction ORM object (using helper)
    - Insert them into the database
    - Redirect to /transactions
    """

    batch = PENDING_BATCHES.get(batch_id)

    if not batch or "final" not in batch:
        print(f"[save-batch] No final data found for batch_id={batch_id!r}")
        # In this case just go back to transactions page
        return RedirectResponse(url="/transactions", status_code=303)

    final = batch["final"]  # list of dicts from /upload/review

    print(f"\n[save-batch] Preparing to insert {len(final)} transactions for batch_id={batch_id!r}")

    db = SessionLocal()
    try:
        orm_objects = []

        for i, tx_dict in enumerate(final, start=1):
            try:
                t = build_transaction_from_dict(tx_dict)
                orm_objects.append(t)

                # Optional: debug log
                print(f"  [#{i}] {t.date} | {t.description} | {t.amount_eur} EUR | {t.category}")
            except Exception as e:
                print(f"[save-batch] ERROR converting tx_dict #{i}: {e!r}")
                print("  Raw dict:", tx_dict)

        if not orm_objects:
            print("[save-batch] No valid transactions to insert.")
            return RedirectResponse(url="/transactions", status_code=303)

        # Insert all at once
        db.add_all(orm_objects)
        db.commit()
        print(f"[save-batch] Successfully inserted {len(orm_objects)} transactions for batch {batch_id!r}")

        # Optional: clean up from memory
        PENDING_BATCHES.pop(batch_id, None)

    except Exception as e:
        db.rollback()
        print(f"[save-batch] ERROR during DB insert: {e!r}")
        # If you want, you can render an error HTML page instead:
        return HTMLResponse(
            f"""
            <html>
            <body style="font-family:sans-serif; padding:20px;">
                <h1>Error while saving batch</h1>
                <p>{e!r}</p>
                <a href="/transactions">Back to transactions</a>
            </body>
            </html>
            """,
            status_code=500,
        )
    finally:
        db.close()

    # On success: go to the main transactions page
    return RedirectResponse(url="/transactions", status_code=303) 