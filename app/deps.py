# deps.py
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

# Jinja2 templates loader (all routes use this)
templates = Jinja2Templates(directory="app/templates")

# -------------------------------------------------------------------
# In-memory batches for CSV import flow
# -------------------------------------------------------------------

# Structure:
# PENDING_BATCHES[batch_id] = {
#     "files": [...],
#     "transactions": {...},
#     "order": [...],
#     "banks": [...],
#     "final": [...],
# }
PENDING_BATCHES: Dict[str, Dict[str, Any]] = {}

# Regex to match keys like: transactions[t_123][amount_eur]
TRANSACTION_KEY_RE = re.compile(
    r"^transactions\[(?P<temp_id>.+?)\]\[(?P<field>.+?)\]$"
)

# -------------------------------------------------------------------
# Database dependency
# -------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session and ensures it's closed.

    Usage in routes:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()