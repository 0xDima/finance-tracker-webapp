# models.py
# Role: SQLAlchemy ORM models for the finance tracker domain.
#       Currently defines the Transaction model, which represents
#       a single normalized financial transaction stored in the database.

from datetime import datetime

from sqlalchemy import Column, Integer, String, Date, Float, Text, DateTime, ForeignKey
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


class ImportSession(Base):
    """
    ORM model representing a CSV import session.
    """

    __tablename__ = "import_sessions"

    id = Column(String, primary_key=True, index=True)
    status = Column(String, nullable=False, default="draft")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    committed_at = Column(DateTime, nullable=True)


class StagingTransaction(Base):
    """
    ORM model representing a staged transaction during import.
    """

    __tablename__ = "staging_transactions"

    id = Column(Integer, primary_key=True, index=True)
    import_id = Column(String, ForeignKey("import_sessions.id"), index=True, nullable=False)
    date = Column(Date, nullable=True)
    description = Column(String, nullable=True)
    currency_original = Column(String(3), nullable=True)
    amount_original = Column(Float, nullable=True)
    amount_eur = Column(Float, nullable=True)
    account_name = Column(String, nullable=True)
    category = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
