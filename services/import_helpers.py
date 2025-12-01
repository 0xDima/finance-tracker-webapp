from datetime import datetime
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