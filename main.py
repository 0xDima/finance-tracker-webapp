# main.py
# Role: Application entry point for the finance tracker.
#       Initializes the FastAPI app, creates database tables,
#       mounts static assets, and registers all route modules.

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

# Create database tables (only if they don't exist yet).
# This is safe to run on startup for SQLite and development usage.
Base.metadata.create_all(bind=engine)

# FastAPI application instance
app = FastAPI(title="Finance Tracker")

# Serve static files (CSS/JS) from /static
# Maps URL path "/static/*" to files under app/static/
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# -------------------------------------------------------------------
# Include routers
# -------------------------------------------------------------------

# Root / landing routes
app.include_router(root_router)

# Transactions list, filters, and related helpers
app.include_router(transactions_router)

# CSV upload → preview → review → save flow
app.include_router(upload_router)

# Dashboard (monthly overview, charts, summaries)
app.include_router(dashboard_router)