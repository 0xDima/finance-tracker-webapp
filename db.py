# db.py
"""
Database setup for the finance tracker.

- Uses SQLite database at: <project_root>/database/finance.db
- Ensures the 'database' folder exists.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Base directory of the project (where main.py lives)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Folder for SQLite DB
DB_DIR = os.path.join(BASE_DIR, "database")
os.makedirs(DB_DIR, exist_ok=True)  # ensure folder exists

DB_PATH = os.path.join(DB_DIR, "finance.db")

# Sqlalchemy connection URL
DATABASE_URL = f"sqlite:///{DB_PATH}"

# For SQLite, we need check_same_thread=False for FastAPI
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()