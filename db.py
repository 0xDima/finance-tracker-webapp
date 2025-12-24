# db.py
# Role: Database bootstrap for the FastAPI finance tracker.
#       Defines the SQLite engine, SQLAlchemy session factory, and declarative Base.
#       Also ensures the on-disk database directory exists before the app starts.

"""
Database setup for the finance tracker.

- Uses SQLite database at: <project_root>/database/finance.db
- Ensures the 'database' folder exists.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Base directory of the project (where this module lives)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Folder for SQLite DB (created on startup if missing)
DB_DIR = os.path.join(BASE_DIR, "database")
os.makedirs(DB_DIR, exist_ok=True)  # ensure folder exists

# Full path to the SQLite database file
DB_PATH = os.path.join(DB_DIR, "finance.db")

# SQLAlchemy connection URL
DATABASE_URL = f"sqlite:///{DB_PATH}"

# For SQLite, we need check_same_thread=False for FastAPI (threaded request handling)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Standard session factory used via dependency injection (see app/deps.py:get_db)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Declarative base class for ORM models
Base = declarative_base()