# routes_root.py
"""
Root / basic endpoints (health, landing).
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def read_root():
    """
    Simple health check / landing endpoint.
    Later we might redirect this to /dashboard.
    """
    return {"message": "My finance app is running"}