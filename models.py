# models.py
# Role: SQLAlchemy ORM models for the finance tracker domain.
#       Currently defines the Transaction model, which represents
#       a single normalized financial transaction stored in the database.

from sqlalchemy import Column, Integer, String, Date, Float, Text
from db import Base


class Transaction(Base):
    """
    ORM model representing a single financial transaction.

    Each row corresponds to one normalized transaction imported from CSV,
    manually added, or migrated from historical data. Amounts are stored
    both in the original currency and converted to EUR for aggregation.
    """

    __tablename__ = "transactions"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Date of the transaction (bank posting / value date)
    date = Column(Date, nullable=False)

    # Bank-provided description / merchant name
    description = Column(String, nullable=False)

    # Original currency code, e.g. "EUR", "UAH", "USD"
    currency_original = Column(String(3), nullable=True)

    # Amount in the original currency (negative = expense, positive = income)
    amount_original = Column(Float, nullable=False)

    # Same amount converted to EUR (used for filtering, sorting, and summaries)
    amount_eur = Column(Float, nullable=False)

    # Account this transaction belongs to (free-text for now)
    account_name = Column(String, nullable=True)

    # User-defined category (can be empty / uncategorized)
    category = Column(String, nullable=True)

    # Optional free-text notes
    notes = Column(Text, nullable=True)