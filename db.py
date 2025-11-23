from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite URL: file will be located at ./database/finance.db (from project root)
DATABASE_URL = "sqlite:///./database/finance.db"

# For SQLite, check_same_thread=False is needed for FastAPI/SQLAlchemy
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()