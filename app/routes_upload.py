# filename: app/routes_upload.py
# Role: CSV upload/import workflow routes.
#       Implements the multi-step flow:
#       1) /upload (select CSVs + bank mapping)
#       2) /upload/preview (parse + create staging rows)
#       3) /import/{id}/preview (editable preview table)
#       4) /import/{id}/review (read-only confirmation)
#       5) /import/{id}/commit (persist to DB and cleanup staging)
#
#       Also includes a legacy JSON upload endpoint (/upload POST) kept for debugging.

"""
Routes for the CSV upload → preview → review → save flow.
"""

import os
import uuid
from datetime import datetime, date
from typing import List, Any, Dict, Optional

from fastapi import (
    APIRouter,
    Request,
    Depends,
    UploadFile,
    File,
    Form,
    Body,
    HTTPException,
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import Transaction, ImportSession, StagingTransaction
from app.services.csv_import import parse_csvs, parse_csv_for_bank
from app.services.import_helpers import build_transaction_from_dict
from app.services.auto_categorize import categorize
from app.deps import (
    templates,
    get_db,
    PENDING_BATCHES,
)

router = APIRouter()

# Allowed categories for AI validation (must match the dropdown on preview page)
ALLOWED_CATEGORIES: List[str] = [
    "Groceries",
    "Transportation",
    "Coffee",
    "Dining & Restaurants",
    "Shopping",
    "Home",
    "Cash Withdrawals",
    "Entertainment & Subscriptions",
    "Travelling",
    "Education & Studying",
    "Other",
    "Investments",
    "Income",
]


def _parse_date(value: Any) -> Optional[date]:
    if value in (None, "", "None"):
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date()
        except Exception:
            return None
    return None


def _coerce_float(value: Any) -> Optional[float]:
    if value in (None, "", "None"):
        return None
    try:
        return float(value)
    except Exception:
        return None


class SuggestCategoriesRequest(BaseModel):
    delete_ids: List[int] = []


# -------------------------------------------------------------------
# Step 0 – show upload page
# -------------------------------------------------------------------

@router.get("/upload", response_class=HTMLResponse)
def upload_page(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Render the CSV upload page.

    This page allows the user to:
    - pick one or more CSV files
    - select which bank each file belongs to
    - submit the form to /upload/preview (main HTML flow)
    """
    drafts = (
        db.query(ImportSession)
        .filter(ImportSession.status == "draft")
        .order_by(ImportSession.created_at.desc())
        .all()
    )

    draft_imports: List[Dict[str, Any]] = []
    for session in drafts:
        count = (
            db.query(StagingTransaction)
            .filter(StagingTransaction.import_id == session.id)
            .count()
        )
        draft_imports.append(
            {
                "id": session.id,
                "created_at": session.created_at,
                "count": count,
            }
        )

    return templates.TemplateResponse(
        "upload.html",
        {"request": request, "draft_imports": draft_imports},
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
    Legacy / debug endpoint.

    - Saves uploaded CSV files into uploads/batch_<id>
    - Parses them with parse_csvs
    - Returns a JSON payload with parsed transactions

    NOTE:
        The primary user-facing flow is /upload/preview → /import/{id}/preview → /import/{id}/review → /import/{id}/commit.
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

    # Initialize batch structure in memory for debugging/inspection
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
# Auto-categorization endpoint (optional AI)
# -------------------------------------------------------------------

@router.post("/import/{import_id}/suggest-categories")
async def suggest_categories(
    import_id: str,
    payload: SuggestCategoriesRequest,
    db: Session = Depends(get_db),
):
    """
    Suggest categories for the given import_id.

    Contract:
    - Never throws to client (silent failure)
    - Returns suggestions as:
        { staging_id: { category, confidence, reason } }
    """
    try:
        if not import_id:
            return {"import_id": import_id, "suggestions": {}}

        delete_ids = set(payload.delete_ids or [])

        txs = (
            db.query(StagingTransaction)
            .filter(StagingTransaction.import_id == import_id)
            .order_by(StagingTransaction.id.asc())
            .all()
        )

        suggestions: Dict[str, Dict[str, Any]] = {}

        for tx in txs:
            if tx.id in delete_ids:
                continue

            description = tx.description or ""
            account_name = tx.account_name or ""
            amount_eur = tx.amount_eur

            amt: Optional[float]
            if amount_eur in (None, "", "None"):
                amt = None
            else:
                try:
                    amt = float(amount_eur)
                except Exception:
                    amt = None

            cat, conf, reason = categorize(
                description=description,
                account_name=account_name,
                amount_eur=amt,
                allowed_categories=ALLOWED_CATEGORIES,
            )

            suggestions[str(tx.id)] = {
                "category": cat,
                "confidence": float(conf) if isinstance(conf, (int, float)) else 0.0,
                "reason": str(reason or ""),
            }

        return {"import_id": import_id, "suggestions": suggestions}

    except Exception:
        # Silent failure by design
        return {"import_id": import_id, "suggestions": {}}


# -------------------------------------------------------------------
# Step 1 – process CSV → show editable preview
# -------------------------------------------------------------------

@router.post("/upload/preview", response_class=HTMLResponse)
async def upload_preview(
    request: Request,
    csv_files: List[UploadFile] = File(...),
    banks: List[str] = Form(...),
    db: Session = Depends(get_db),
):
    """
    Step 1 of the main flow:

    - Receive uploaded CSV files and selected banks
    - Save CSV files into uploads/batch_<id> on disk
    - Parse them into normalized transaction dicts
    - Insert rows into staging_transactions tied to an import_session
    - Redirect to /import/{import_id}/preview
    """
    import_id = str(uuid.uuid4())

    folder = f"uploads/batch_{import_id}"
    os.makedirs(folder, exist_ok=True)

    saved_paths: List[str] = []

    for file, bank in zip(csv_files, banks):
        file_location = os.path.join(folder, file.filename)
        saved_paths.append(file_location)

        with open(file_location, "wb") as f:
            f.write(await file.read())

    session = ImportSession(id=import_id, status="draft")
    db.add(session)
    db.flush()

    staged_rows: List[StagingTransaction] = []

    for file_path, bank in zip(saved_paths, banks):
        rows = parse_csv_for_bank(file_path, bank)
        for row in rows:
            staged_rows.append(
                StagingTransaction(
                    import_id=import_id,
                    date=_parse_date(row.get("date")),
                    description=row.get("description") or "",
                    currency_original=row.get("currency_original") or None,
                    amount_original=_coerce_float(row.get("amount_original")),
                    amount_eur=_coerce_float(row.get("amount_eur")),
                    account_name=row.get("account_name") or "",
                    category=row.get("category") or None,
                    notes=row.get("notes") or "",
                )
            )

    if staged_rows:
        db.add_all(staged_rows)
    db.commit()

    return RedirectResponse(url=f"/import/{import_id}/preview", status_code=303)


# -------------------------------------------------------------------
# Step 1b – load staging rows → show editable preview
# -------------------------------------------------------------------

@router.get("/import/{import_id}/preview", response_class=HTMLResponse)
async def import_preview(
    request: Request,
    import_id: str,
    db: Session = Depends(get_db),
):
    """
    Load staging rows for a given import session and render the preview table.
    """
    session = (
        db.query(ImportSession)
        .filter(ImportSession.id == import_id)
        .first()
    )
    if not session or session.status != "draft":
        raise HTTPException(status_code=404, detail="Import session not found")

    transactions = (
        db.query(StagingTransaction)
        .filter(StagingTransaction.import_id == import_id)
        .order_by(StagingTransaction.id.asc())
        .all()
    )

    return templates.TemplateResponse(
        "upload_preview.html",
        {
            "request": request,
            "import_id": import_id,
            "transactions": transactions,
        },
    )


# -------------------------------------------------------------------
# Step 2 – show read-only review
# -------------------------------------------------------------------

@router.get("/import/{import_id}/review", response_class=HTMLResponse)
async def import_review(
    request: Request,
    import_id: str,
    db: Session = Depends(get_db),
):
    """
    Render the read-only review table from staging rows.
    """
    session = (
        db.query(ImportSession)
        .filter(ImportSession.id == import_id)
        .first()
    )
    if not session or session.status != "draft":
        raise HTTPException(status_code=404, detail="Import session not found")

    transactions = (
        db.query(StagingTransaction)
        .filter(StagingTransaction.import_id == import_id)
        .order_by(StagingTransaction.id.asc())
        .all()
    )

    return templates.TemplateResponse(
        "upload_review.html",
        {
            "request": request,
            "import_id": import_id,
            "transactions": transactions,
        },
    )


# -------------------------------------------------------------------
# Step 2b – apply deletes from preview (optional) then show review
# -------------------------------------------------------------------

@router.post("/import/{import_id}/review", response_class=HTMLResponse)
async def import_review_post(
    request: Request,
    import_id: str,
    db: Session = Depends(get_db),
):
    session = (
        db.query(ImportSession)
        .filter(ImportSession.id == import_id)
        .first()
    )
    if not session or session.status != "draft":
        raise HTTPException(status_code=404, detail="Import session not found")

    form = await request.form()
    delete_ids_raw: List[str] = form.getlist("delete_ids")
    delete_ids: List[int] = []
    for raw in delete_ids_raw:
        try:
            delete_ids.append(int(raw))
        except Exception:
            continue

    if delete_ids:
        db.query(StagingTransaction).filter(
            StagingTransaction.import_id == import_id,
            StagingTransaction.id.in_(delete_ids),
        ).delete(synchronize_session=False)
        db.commit()

    transactions = (
        db.query(StagingTransaction)
        .filter(StagingTransaction.import_id == import_id)
        .order_by(StagingTransaction.id.asc())
        .all()
    )

    return templates.TemplateResponse(
        "upload_review.html",
        {
            "request": request,
            "import_id": import_id,
            "transactions": transactions,
        },
    )


# -------------------------------------------------------------------
# Step 3 – save staging batch into the DB
# -------------------------------------------------------------------

@router.post("/import/{import_id}/commit")
async def save_import(
    import_id: str,
    db: Session = Depends(get_db),
):
    """
    Commit staged rows into the main transactions table and cleanup staging.
    """
    session = (
        db.query(ImportSession)
        .filter(ImportSession.id == import_id)
        .first()
    )
    if not session or session.status != "draft":
        return RedirectResponse(url="/transactions", status_code=303)

    staging_rows = (
        db.query(StagingTransaction)
        .filter(StagingTransaction.import_id == import_id)
        .order_by(StagingTransaction.id.asc())
        .all()
    )

    if not staging_rows:
        return RedirectResponse(url="/transactions", status_code=303)

    validation_errors: List[str] = []
    for row in staging_rows:
        if row.date is None:
            validation_errors.append(f"Row {row.id}: missing date")
        if row.amount_original is None:
            validation_errors.append(f"Row {row.id}: missing amount")
        if not (row.description or "").strip():
            validation_errors.append(f"Row {row.id}: missing description")

    if validation_errors:
        error_html = "<br>".join(validation_errors)
        return HTMLResponse(
            f"""
            <html>
            <body style="font-family:sans-serif; padding:20px;">
                <h1>Cannot commit import</h1>
                <p>Please fix the following rows in the preview table:</p>
                <p>{error_html}</p>
                <a href="/import/{import_id}/preview">Back to preview</a>
            </body>
            </html>
            """,
            status_code=400,
        )

    try:
        orm_objects: List[Transaction] = []

        for row in staging_rows:
            tx_dict = {
                "date": row.date,
                "description": row.description,
                "currency_original": row.currency_original,
                "amount_original": row.amount_original,
                "amount_eur": row.amount_eur,
                "account_name": row.account_name,
                "category": row.category,
                "notes": row.notes,
            }
            tx_obj = build_transaction_from_dict(tx_dict)
            orm_objects.append(tx_obj)

        if not orm_objects:
            return RedirectResponse(url="/transactions", status_code=303)

        db.add_all(orm_objects)
        db.query(StagingTransaction).filter(StagingTransaction.import_id == import_id).delete(
            synchronize_session=False
        )
        session.status = "committed"
        session.committed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        db.rollback()
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


# -------------------------------------------------------------------
# Staging row CRUD
# -------------------------------------------------------------------


@router.post("/import/{import_id}/staging")
async def create_staging_row(
    import_id: str,
    db: Session = Depends(get_db),
):
    session = (
        db.query(ImportSession)
        .filter(ImportSession.id == import_id)
        .first()
    )
    if not session or session.status != "draft":
        raise HTTPException(status_code=404, detail="Import session not found")

    row = StagingTransaction(
        import_id=import_id,
        date=None,
        description="",
        currency_original=None,
        amount_original=None,
        amount_eur=None,
        account_name="",
        category=None,
        notes="",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "import_id": row.import_id,
    }


@router.patch("/import/{import_id}/staging/{row_id}")
async def update_staging_row(
    import_id: str,
    row_id: int,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
):
    row = (
        db.query(StagingTransaction)
        .filter(
            StagingTransaction.id == row_id,
            StagingTransaction.import_id == import_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Staging row not found")

    allowed = {
        "date",
        "description",
        "currency_original",
        "amount_original",
        "amount_eur",
        "account_name",
        "category",
        "notes",
    }

    for field, value in payload.items():
        if field not in allowed:
            raise HTTPException(status_code=400, detail=f"Unsupported field: {field}")

        if field == "date":
            parsed = _parse_date(value)
            if value not in (None, "", "None") and parsed is None:
                raise HTTPException(status_code=422, detail="Invalid date format")
            setattr(row, field, parsed)
        elif field in ("amount_original", "amount_eur"):
            parsed = _coerce_float(value)
            if value not in (None, "", "None") and parsed is None:
                raise HTTPException(status_code=422, detail="Invalid amount")
            setattr(row, field, parsed)
        elif field == "currency_original":
            if value in (None, "", "None"):
                setattr(row, field, None)
            else:
                setattr(row, field, str(value).upper()[:3])
        else:
            setattr(row, field, "" if value is None else str(value))

    db.commit()
    return {"status": "ok"}


@router.delete("/import/{import_id}")
async def delete_import(
    import_id: str,
    db: Session = Depends(get_db),
):
    session = (
        db.query(ImportSession)
        .filter(ImportSession.id == import_id)
        .first()
    )
    if not session or session.status != "draft":
        raise HTTPException(status_code=404, detail="Import session not found")

    db.query(StagingTransaction).filter(StagingTransaction.import_id == import_id).delete(
        synchronize_session=False
    )
    db.query(ImportSession).filter(ImportSession.id == import_id).delete(
        synchronize_session=False
    )
    db.commit()
    return JSONResponse({"status": "deleted", "import_id": import_id})
