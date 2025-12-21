"""
This script migrates normalized transaction data from monthly Excel/CSV tables
(collected throughout the year) into a SQLite database.

All source files are pre-cleaned and normalized (consistent headers, date format,
and numeric values) before import. The script validates required fields, removes
empty rows, and inserts transactions into the database using SQLAlchemy ORM.

Purpose:
- Consolidate yearly financial data from Excel into a single SQLite database
- Ensure data consistency before further analysis and application usage
- Serve as a one-time / repeatable migration step during development
"""


from __future__ import annotations

from pathlib import Path
from datetime import datetime
import pandas as pd

from db import SessionLocal, engine, Base
from models import Transaction


NORMALIZED_DIR = Path("data-migration/normalized")


def _parse_date_ddmmyyyy(s: str):
    return datetime.strptime(str(s).strip(), "%d-%m-%Y").date()


def _none_if_nan(x):
    if pd.isna(x):
        return None
    s = str(x).strip()
    return None if s == "" or s.lower() == "nan" else s


def import_normalized_csvs_to_db(
    folder: Path = NORMALIZED_DIR,
    currency_default: str | None = "EUR",
    batch_size: int = 1000,
):
    folder = Path(folder)
    csv_files = sorted(folder.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in: {folder.resolve()}")

    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    total_inserted = 0

    try:
        for f in csv_files:
            df = pd.read_csv(f)

            # normalize headers
            df.columns = df.columns.str.strip().str.lower()

            # required
            required = {"date", "description", "sum"}
            missing = required - set(df.columns)
            if missing:
                raise ValueError(f"{f.name}: missing required columns: {sorted(missing)}")

            # optional
            if "category" not in df.columns:
                df["category"] = None
            if "notes" not in df.columns:
                df["notes"] = None
            if "account" not in df.columns:
                df["account"] = None

            # drop fully empty rows
            df = df.dropna(how="all").copy()

            # parse date (strict DD-MM-YYYY)
            df["date"] = df["date"].apply(_parse_date_ddmmyyyy)

            # parse sum (handle commas just in case)
            sum_clean = (
                df["sum"]
                .astype(str)
                .str.replace(" ", "", regex=False)
                .str.replace(",", ".", regex=False)
                .str.strip()
            )
            df["sum"] = pd.to_numeric(sum_clean, errors="raise")

            # build ORM objects
            objs = []
            for row in df.itertuples(index=False):
                date_val = getattr(row, "date")
                desc_val = _none_if_nan(getattr(row, "description"))
                sum_val = float(getattr(row, "sum"))

                if desc_val is None:
                    continue

                objs.append(
                    Transaction(
                        date=date_val,
                        description=desc_val,
                        currency_original=currency_default,
                        amount_original=sum_val,
                        amount_eur=sum_val,
                        account_name=_none_if_nan(getattr(row, "account")),
                        category=_none_if_nan(getattr(row, "category")),
                        notes=_none_if_nan(getattr(row, "notes")),
                    )
                )

            # insert in batches
            for i in range(0, len(objs), batch_size):
                session.add_all(objs[i : i + batch_size])
                session.commit()

            total_inserted += len(objs)
            print(f"✅ Imported {len(objs)} rows from {f.name}")

        print(f"\nDONE. Total inserted: {total_inserted}")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    import_normalized_csvs_to_db()