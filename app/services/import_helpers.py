# import_helpers.py

from datetime import datetime, date
from models import Transaction


def build_transaction_from_dict(tx: dict) -> Transaction:
    """
    Convert one cleaned tx dict (from PENDING_BATCHES[...]["final"])
    into a Transaction ORM object.
    """

    date_raw = tx.get("date")
    if isinstance(date_raw, str):
        date_parsed = datetime.strptime(date_raw, "%Y-%m-%d").date()
    else:
        date_parsed = date_raw  # already a date object

    # Amounts
    amount_original = tx.get("amount_original") or 0.0
    amount_eur = tx.get("amount_eur")

    # amount_eur cannot be NULL in the DB → ensure fallback
    if amount_eur is None:
        amount_eur = float(amount_original)

    t = Transaction(
        date=date_parsed,
        description=tx.get("description", ""),
        currency_original=tx.get("currency_original") or None,
        amount_original=float(amount_original),
        amount_eur=float(amount_eur),
        account_name=tx.get("account_name") or None,
        category=tx.get("category") or None,
        notes=tx.get("notes") or None,
    )

    return t




def get_month_range(month_str: str | None):
    """
    month_str: 'YYYY-MM' or None.
    Returns (start_date, end_date_exclusive, normalized_month_str).
    If month_str is None or invalid, uses current month.
    """
    if month_str:
        try:
            year_str, month_only_str = month_str.split("-")
            year = int(year_str)
            month = int(month_only_str)
            if not (1 <= month <= 12):
                raise ValueError
        except Exception:
            today = date.today()
            year, month = today.year, today.month
    else:
        today = date.today()
        year, month = today.year, today.month

    start_date = date(year, month, 1)

    if month == 12:
        end_date_exclusive = date(year + 1, 1, 1)
    else:
        end_date_exclusive = date(year, month + 1, 1)

    normalized = f"{year:04d}-{month:02d}"
    return start_date, end_date_exclusive, normalized
