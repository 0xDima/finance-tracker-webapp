# routes_upload.py
"""
Routes for the CSV upload → preview → review → save flow.
"""

import os
import uuid
from typing import List, Any, Dict

from fastapi import (
    APIRouter,
    Request,
    Depends,
    UploadFile,
    File,
    Form,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from models import Transaction
from app.services.csv_import import parse_csvs
from app.services.import_helpers import build_transaction_from_dict
from app.deps import (
    templates,
    get_db,
    PENDING_BATCHES,
    TRANSACTION_KEY_RE,
)

router = APIRouter()


# -------------------------------------------------------------------
# Step 0 – show upload page
# -------------------------------------------------------------------

@router.get("/upload", response_class=HTMLResponse)
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
# Legacy JSON upload endpoint (optional, debug only)
# -------------------------------------------------------------------

@router.post("/upload")
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

    folder = f"uploads/batch_{batch_id}"
    os.makedirs(folder, exist_ok=True)

    saved_paths: List[str] = []

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

    parse_csvs(batch, batch_id, saved_paths, banks)

    tx_list = [batch["transactions"][tid] for tid in batch["order"]]

    return {
        "batch_id": batch_id,
        "transaction_count": len(tx_list),
        "transactions": tx_list,
    }


# -------------------------------------------------------------------
# Step 1 – process CSV → show editable preview
# -------------------------------------------------------------------

@router.post("/upload/preview", response_class=HTMLResponse)
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
    """
    batch_id = str(uuid.uuid4())

    folder = f"uploads/batch_{batch_id}"
    os.makedirs(folder, exist_ok=True)

    saved_paths: List[str] = []

    for file, bank in zip(csv_files, banks):
        file_location = os.path.join(folder, file.filename)
        saved_paths.append(file_location)

        with open(file_location, "wb") as f:
            f.write(await file.read())

    PENDING_BATCHES[batch_id] = {
        "files": saved_paths,
        "transactions": {},
        "order": [],
        "banks": banks,
    }
    batch = PENDING_BATCHES[batch_id]

    parse_csvs(batch, batch_id, saved_paths, banks)

    transactions_for_template: List[Dict[str, Any]] = []
    for temp_id in batch["order"]:
        tx_data = batch["transactions"][temp_id].copy()
        tx_data["temp_id"] = temp_id
        transactions_for_template.append(tx_data)

    return templates.TemplateResponse(
        "upload_preview.html",
        {
            "request": request,
            "batch_id": batch_id,
            "transactions": transactions_for_template,
        },
    )


# -------------------------------------------------------------------
# Step 2 – read edited form → show read-only review
# -------------------------------------------------------------------

@router.post("/upload/review", response_class=HTMLResponse)
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

    cleaned: List[Dict[str, Any]] = []

    for temp_id, tx_data in raw_tx.items():
        if temp_id in delete_ids:
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

        try:
            tx["amount_original"] = float(tx_data.get("amount_original"))
        except Exception:
            tx["amount_original"] = None

        raw_eur = tx_data.get("amount_eur")
        if raw_eur in (None, "", "None"):
            tx["amount_eur"] = None
        else:
            try:
                tx["amount_eur"] = float(raw_eur)
            except Exception:
                tx["amount_eur"] = None

        cleaned.append(tx)

    if batch_id:
        if batch_id not in PENDING_BATCHES:
            PENDING_BATCHES[batch_id] = {}
        PENDING_BATCHES[batch_id]["final"] = cleaned

    return templates.TemplateResponse(
        "upload_review.html",
        {
            "request": request,
            "batch_id": batch_id,
            "transactions": cleaned,
        },
    )


# -------------------------------------------------------------------
# Step 3 – save cleaned batch into the DB
# -------------------------------------------------------------------

@router.post("/upload/save-batch")
async def save_batch(
    batch_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Step 3 of the main flow:

    Called when user clicks "Save to database" on the review page.

    Responsibilities:
    - Take cleaned tx dicts from PENDING_BATCHES[batch_id]["final"]
    - Convert each dict into a Transaction ORM object (build_transaction_from_dict)
    - Insert them into the database in one transaction
    - Clean up the batch from memory
    - Redirect to /transactions
    """

    batch = PENDING_BATCHES.get(batch_id)

    if not batch or "final" not in batch:
        print(f"[save-batch] No final data found for batch_id={batch_id!r}")
        return RedirectResponse(url="/transactions", status_code=303)

    final = batch["final"]  # list of dicts from /upload/review

    print(f"\n[save-batch] Preparing to insert {len(final)} transactions for batch_id={batch_id!r}")

    try:
        orm_objects: List[Transaction] = []

        for i, tx_dict in enumerate(final, start=1):
            try:
                tx_obj = build_transaction_from_dict(tx_dict)
                orm_objects.append(tx_obj)
                print(f"  [#{i}] {tx_obj.date} | {tx_obj.description} | {tx_obj.amount_eur} EUR | {tx_obj.category}")
            except Exception as e:
                print(f"[save-batch] ERROR converting tx_dict #{i}: {e!r}")
                print("  Raw dict:", tx_dict)

        if not orm_objects:
            print("[save-batch] No valid transactions to insert.")
            return RedirectResponse(url="/transactions", status_code=303)

        db.add_all(orm_objects)
        db.commit()
        print(f"[save-batch] Successfully inserted {len(orm_objects)} transactions for batch {batch_id!r}")

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

    return RedirectResponse(url="/transactions", status_code=303)