"""
Main FastAPI app for the personal finance tracker.

Here we only:
- create the FastAPI app
- set up static files
- create DB tables
- include route modules
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from db import Base, engine
from app.routes_root import router as root_router
from app.routes_transactions import router as transactions_router
from app.routes_upload import router as upload_router
from app.routes_dashboard import router as dashboard_router


# -------------------------------------------------------------------
# App & DB setup
# -------------------------------------------------------------------

# Create database tables (only if they don't exist yet)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finance Tracker")

# Serve static files (CSS/JS) from /static
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# -------------------------------------------------------------------
# Include routers
# -------------------------------------------------------------------

app.include_router(root_router)
app.include_router(transactions_router)
app.include_router(upload_router)
app.include_router(dashboard_router)