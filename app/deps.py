# app/deps.py
# Role: Shared application-level dependencies and globals.
#       Provides the Jinja2 templates loader, an in-memory store for CSV upload batches,
#       common regex helpers, and the standard SQLAlchemy database session dependency.

"""
Shared dependencies and globals for the finance tracker app.
"""

import re
from typing import Dict, Any, Generator

from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from db import SessionLocal

# -------------------------------------------------------------------
# Templates
# -------------------------------------------------------------------

# Jinja2 templates loader (used by all HTML-rendering routes)
templates = Jinja2Templates(directory="app/templates")

# -------------------------------------------------------------------
# In-memory batches for CSV import flow
# -------------------------------------------------------------------

# Temporary in-memory storage for multi-step CSV uploads.
# Each batch_id maps to a dict holding parsed files, transactions,
# original ordering, selected banks, and finalized rows.
#
# Structure:
# PENDING_BATCHES[batch_id] = {
#     "files": [...],
#     "transactions": {...},
#     "order": [...],
#     "banks": [...],
#     "final": [...],
# }
PENDING_BATCHES: Dict[str, Dict[str, Any]] = {}

# Regex to match flattened form keys like: transactions[t_123][amount_eur]
# Used when reconstructing transaction payloads from form submissions.
TRANSACTION_KEY_RE = re.compile(
    r"^transactions\[(?P<temp_id>.+?)\]\[(?P<field>.+?)\]$"
)

# -------------------------------------------------------------------
# Database dependency
# -------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session and ensures it is closed.

    Typical usage in routes:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()