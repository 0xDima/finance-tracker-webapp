# app/routes_root.py
# Role: Root-level routes for the application.
#       Defines the base ("/") endpoint, currently used as a simple landing/redirect
#       into the main dashboard view.

"""
Root / basic endpoints (health, landing).
"""

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()


@router.get("/")
def read_root():
    return RedirectResponse(url="/dashboard", status_code=302)