# main.py
"""
Main FastAPI app for the personal finance tracker.

Current features:
- View all transactions from the database
- Add a test transaction (for debugging)
- Upload CSV bank statements
- Preview imported transactions with inline editing
- Review cleaned transactions
- Save a batch of transactions to the database
"""

import os
import re
import uuid
from datetime import date
from typing import List, Any, Dict

from fastapi import FastAPI, Request, Depends, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

from sqlalchemy.orm import Session

from db import Base, engine, SessionLocal
from models import Transaction
from services.csv_import import parse_csvs
from services.import_helpers import build_transaction_from_dict


# -------------------------------------------------------------------
# Global in-memory storage for upload batches
# -------------------------------------------------------------------

# Structure:
# PENDING_BATCHES[batch_id] = {
#     "files": [...],         # list of file paths on disk
#     "transactions": {...},  # temp_id -> tx dict (from CSV parsing)
#     "order": [...],         # list of temp_ids to preserve table order
#     "banks": [...],         # bank names (parallel to csv_files)
#     "final": [...],         # list of cleaned tx dicts (after /upload/review)
# }
PENDING_BATCHES: Dict[str, Dict[str, Any]] = {}


# -------------------------------------------------------------------
# Database & app setup
# -------------------------------------------------------------------

# Create database tables (only if they don't exist yet)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finance Tracker")

# Static files (CSS/JS) are served from the "static" folder at /static/...
# Make sure your folder structure has "static/" at the project root.
app.mount("/static", StaticFiles(directory="static"), name="static")

# Jinja2 templates are loaded from the "templates" folder at the project root.
templates = Jinja2Templates(directory="templates")


def get_db():
    """
    Dependency that provides a database session and ensures it's closed.

    Usage (in routes):
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------------------------------------------------
# Basic routes
# -------------------------------------------------------------------

@app.get("/")
def read_root():
    """
    Simple health check / landing endpoint.
    """
    return {"message": "My finance app is running"}


@app.get("/transactions", response_class=HTMLResponse)
def transactions_page(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Show all transactions stored in the database.
    """
    transactions = (
        db.query(Transaction)
        .order_by(Transaction.date.desc())
        .all()
    )

    return templates.TemplateResponse(
        "transactions.html",
        {
            "request": request,
            "transactions": transactions,
        },
    )


@app.post("/add-test-transaction")
def add_test_transaction(db: Session = Depends(get_db)):
    """
    Debug endpoint: insert one hard-coded test transaction into the DB.
    Useful to test that DB + models + /transactions page are working.
    """
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


# -------------------------------------------------------------------
# Upload flow: step 0 – show upload page
# -------------------------------------------------------------------

@app.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request):
    """
    Render the CSV upload page.

    This page allows the user to:
    - pick one or more CSV files
    - select which bank each file belongs to
    - submit the form to /upload/preview
    """
    return templates.TemplateResponse(
        "upload.html",
        {"request": request},
    )


# -------------------------------------------------------------------
# Upload flow: legacy JSON endpoint (keep as debug if you want)
# -------------------------------------------------------------------

@app.post("/upload")
async def upload_process(
    request: Request,
    csv_files: List[UploadFile] = File(...),
    banks: List[str] = Form(...),
    db: Session = Depends(get_db),  # not used currently, but kept for future
):
    """
    Legacy / debug endpoint:

    - Saves uploaded CSV files into uploads/batch_<id>
    - Parses them with parse_csvs
    - Returns a JSON payload with parsed transactions

    NOTE:
        Your main flow now uses /upload/preview to show HTML preview.
        You can keep this as a debugging endpoint, or remove it later.
    """
    batch_id = str(uuid.uuid4())

    # Folder: uploads/batch_<id>
    folder = f"uploads/batch_{batch_id}"
    os.makedirs(folder, exist_ok=True)

    saved_paths: List[str] = []

    # Save each file to disk
    for file, bank in zip(csv_files, banks):
        file_location = os.path.join(folder, file.filename)
        saved_paths.append(file_location)

        with open(file_location, "wb") as f:
            f.write(await file.read())

    # Initialize batch structure in memory
    PENDING_BATCHES[batch_id] = {
        "files": saved_paths,
        "transactions": {},
        "order": [],
        "banks": banks,
    }
    batch = PENDING_BATCHES[batch_id]

    # Parse CSVs into normalized transactions
    parse_csvs(batch, batch_id, saved_paths, banks)

    # Build list for JSON response
    tx_list = [batch["transactions"][tid] for tid in batch["order"]]

    return {
        "batch_id": batch_id,
        "transaction_count": len(tx_list),
        "transactions": tx_list,
    }


# -------------------------------------------------------------------
# Upload flow: step 1 – process CSV -> show editable preview
# -------------------------------------------------------------------

@app.post("/upload/preview", response_class=HTMLResponse)
async def upload_preview(
    request: Request,
    csv_files: List[UploadFile] = File(...),
    banks: List[str] = Form(...),
):
    """
    Step 1 of the main flow:

    - Receive uploaded CSV files and selected banks
    - Save CSV files into uploads/batch_<id> on disk
    - Parse them into normalized transaction dicts using parse_csvs
    - Store parsed data in PENDING_BATCHES[batch_id]
    - Render upload_preview.html with an editable table

    The preview page:
    - shows one row per transaction
    - allows inline editing via JS
    - uses hidden inputs so edited values are posted to /upload/review
    """
    batch_id = str(uuid.uuid4())

    # Create batch folder on disk
    folder = f"uploads/batch_{batch_id}"
    os.makedirs(folder, exist_ok=True)

    saved_paths: List[str] = []

    # Save each uploaded CSV into the batch folder
    for file, bank in zip(csv_files, banks):
        file_location = os.path.join(folder, file.filename)
        saved_paths.append(file_location)

        with open(file_location, "wb") as f:
            f.write(await file.read())

    # Initialize batch entry in memory
    PENDING_BATCHES[batch_id] = {
        "files": saved_paths,
        "transactions": {},
        "order": [],
        "banks": banks,
    }
    batch = PENDING_BATCHES[batch_id]

    # Parse CSVs and fill the batch["transactions"] + batch["order"]
    parse_csvs(batch, batch_id, saved_paths, banks)

    # Build a list of transactions including temp_id for the template
    transactions_for_template: List[Dict[str, Any]] = []
    for temp_id in batch["order"]:
        tx_data = batch["transactions"][temp_id].copy()
        tx_data["temp_id"] = temp_id
        transactions_for_template.append(tx_data)

    # Render preview page
    return templates.TemplateResponse(
        "upload_preview.html",
        {
            "request": request,
            "batch_id": batch_id,
            "transactions": transactions_for_template,
        },
    )


# -------------------------------------------------------------------
# Upload flow: step 2 – read edited form -> show read-only review
# -------------------------------------------------------------------

# Regex to match keys like: transactions[t_123][amount_eur]
TRANSACTION_KEY_RE = re.compile(
    r"^transactions\[(?P<temp_id>.+?)\]\[(?P<field>.+?)\]$"
)


@app.post("/upload/review", response_class=HTMLResponse)
async def upload_review(request: Request):
    """
    Step 2 of the main flow:

    Called when user clicks "Import" on the preview page.

    Responsibilities:
    - Read all form fields from upload_preview.html
    - Parse nested field names like transactions[t1][date]
    - Group fields by temp_id into raw_tx dict
    - Skip rows that were marked for deletion (delete_ids)
    - Convert numeric fields (amount_original, amount_eur)
    - Store cleaned list in PENDING_BATCHES[batch_id]["final"]
    - Render upload_review.html (read-only review table)
    """

    form = await request.form()

    batch_id = form.get("batch_id")
    delete_ids: List[str] = form.getlist("delete_ids")

    # raw_tx: { "t1": { "date": "...", "category": "...", ... }, ... }
    raw_tx: Dict[str, Dict[str, Any]] = {}

    for key, value in form.items():
        match = TRANSACTION_KEY_RE.match(key)
        if not match:
            # Ignore keys like batch_id, delete_ids, etc.
            continue

        temp_id = match.group("temp_id")
        field = match.group("field")

        if temp_id not in raw_tx:
            raw_tx[temp_id] = {}

        raw_tx[temp_id][field] = value

    # Build cleaned list, skipping deleted rows
    cleaned: List[Dict[str, Any]] = []

    for temp_id, tx_data in raw_tx.items():
        if temp_id in delete_ids:
            # Row was marked for deletion (checkbox checked) -> skip
            continue

        tx: Dict[str, Any] = {
            "temp_id": temp_id,
            "date": tx_data.get("date") or "",
            "account_name": tx_data.get("account_name") or "",
            "description": tx_data.get("description") or "",
            "currency_original": tx_data.get("currency_original") or "",
            "category": tx_data.get("category") or "",
            "notes": tx_data.get("notes") or "",
        }

        # amount_original
        try:
            tx["amount_original"] = float(tx_data.get("amount_original"))
        except Exception:
            tx["amount_original"] = None

        # amount_eur
        raw_eur = tx_data.get("amount_eur")
        if raw_eur in (None, "", "None"):
            tx["amount_eur"] = None
        else:
            try:
                tx["amount_eur"] = float(raw_eur)
            except Exception:
                tx["amount_eur"] = None

        cleaned.append(tx)

    # Store cleaned list in PENDING_BATCHES so /upload/save-batch can use it
    if batch_id:
        if batch_id not in PENDING_BATCHES:
            PENDING_BATCHES[batch_id] = {}
        PENDING_BATCHES[batch_id]["final"] = cleaned

    # Show read-only review table
    return templates.TemplateResponse(
        "upload_review.html",
        {
            "request": request,
            "batch_id": batch_id,
            "transactions": cleaned,
        },
    )


# -------------------------------------------------------------------
# Upload flow: step 3 – save cleaned batch into the DB
# -------------------------------------------------------------------

@app.post("/upload/save-batch")
async def save_batch(batch_id: str = Form(...)):
    """
    Step 3 of the main flow:

    Called when user clicks "Save to database" on the review page.

    Responsibilities:
    - Take cleaned tx dicts from PENDING_BATCHES[batch_id]["final"]
    - Convert each dict into a Transaction ORM object (build_transaction_from_dict)
    - Insert them into the database in one transaction
    - Optionally clean up the batch from memory
    - Redirect to /transactions (or show a success page)
    """

    batch = PENDING_BATCHES.get(batch_id)

    if not batch or "final" not in batch:
        print(f"[save-batch] No final data found for batch_id={batch_id!r}")
        return RedirectResponse(url="/transactions", status_code=303)

    final = batch["final"]  # list of dicts from /upload/review

    print(f"\n[save-batch] Preparing to insert {len(final)} transactions for batch_id={batch_id!r}")

    db = SessionLocal()
    try:
        orm_objects: List[Transaction] = []

        for i, tx_dict in enumerate(final, start=1):
            try:
                t = build_transaction_from_dict(tx_dict)
                orm_objects.append(t)
                # Debug log
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

        # Clean up from memory
        PENDING_BATCHES.pop(batch_id, None)

    except Exception as e:
        db.rollback()
        print(f"[save-batch] ERROR during DB insert: {e!r}")
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