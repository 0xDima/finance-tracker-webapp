# routes_root.py
"""
Root / basic endpoints (health, landing).
"""

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()


@router.get("/")
def read_root():
    """
    Simple health check / landing endpoint.
    Later we might redirect this to /dashboard.
    """
    return RedirectResponse(url="/dashboard", status_code=302)