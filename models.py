from sqlalchemy import Column, Integer, String, Date, Float, Text
from db import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)

    # Date of the transaction
    date = Column(Date, nullable=False)

    # Bank-provided description / merchant
    description = Column(String, nullable=False)

    # Original currency, e.g. "EUR", "UAH", "USD"
    currency_original = Column(String(3), nullable=True)

    # Amount in the original currency (negative = expense, positive = income)
    amount_original = Column(Float, nullable=False)

    # Same amount converted to EUR
    amount_eur = Column(Float, nullable=False)

    # Which account this transaction belongs to (text for now)
    account_name = Column(String, nullable=True)

    # User-defined category, can be empty at first
    category = Column(String, nullable=True)

    # Free-text notes
    notes = Column(Text, nullable=True)