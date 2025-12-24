# app/services/import_helpers.py
#
# Import Helper Functions
# Provides utility functions for converting parsed transaction dictionaries into ORM models
# and calculating date ranges for monthly financial reports.

from datetime import datetime, date
from models import Transaction


# ---- Transaction Conversion ----

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


# ---- Date Range Utilities ----

def get_month_range(month_str: str | None):
    """
    month_str: 'YYYY-MM' or None.
    Returns (start_date, end_date_exclusive, normalized_month_str).
    If month_str is None or invalid, uses PREVIOUS month.
    """

    def previous_month_from_today():
        today = date.today()
        if today.month == 1:
            return today.year - 1, 12
        return today.year, today.month - 1

    # 1) pick year/month
    if month_str:
        try:
            year_str, month_only_str = month_str.split("-")
            year = int(year_str)
            month = int(month_only_str)
            if not (1 <= month <= 12):
                raise ValueError
        except Exception:
            year, month = previous_month_from_today()
    else:
        # 👇 DEFAULT: previous month
        year, month = previous_month_from_today()

    # 2) compute start and first day of next month
    start_date = date(year, month, 1)
    if month == 12:
        end_date_exclusive = date(year + 1, 1, 1)
    else:
        end_date_exclusive = date(year, month + 1, 1)

    normalized = f"{year:04d}-{month:02d}"
    return start_date, end_date_exclusive, normalized