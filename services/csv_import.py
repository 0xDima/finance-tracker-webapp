# csv_import.py

from typing import List, Dict
import pandas as pd
import numpy as np


def parse_eu_number(value: str) -> float:
    """
    Converts European formatted numbers like '−50,00' or '1.234,56'
    into a Python float.
    """
    if value is None:
        return 0.0

    s = str(value)

    # Replace Unicode minus with normal minus
    s = s.replace("−", "-")  # U+2212 → '-'

    # Remove thousand separators
    s = s.replace(".", "")

    # Replace comma decimal separator with dot
    s = s.replace(",", ".")

    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_revolut(file_path: str) -> List[Dict]:
    """
    Parse a Revolut CSV file into a list of normalized transaction dicts.
    """
    df = pd.read_csv(file_path, encoding="utf-8")

    # Drop columns you don't need
    df = df.drop(
        columns=["Type", "Product", "Completed Date", "Fee", "State", "Balance"],
        errors="ignore",
    )

    # Completed Date is the effective transaction date
    df["Started Date"] = pd.to_datetime(df["Started Date"]).dt.date

    # Rename to normalized schema
    df = df.rename(
        columns={
            "Started Date": "date",
            "Description": "description",
            "Amount": "amount_original",
            "Currency": "currency_original",
        }
    )

    # Types
    df["amount_original"] = df["amount_original"].astype(float)

    # Normalized extra fields
    df["amount_eur"] = df["amount_original"]  # Revolut export already in EUR
    df["account_name"] = "Revolut"
    df["category"] = None
    df["notes"] = ""  # Revolut CSV has no notes column

    return df.to_dict(orient="records")


def parse_erste(file_path: str) -> List[Dict]:
    """
    Parse an Erste CSV file into a list of normalized transaction dicts.
    """
    df = pd.read_csv(file_path, encoding="utf-16")

    # Parse date "31.08.2025"
    df["Datum unosa"] = pd.to_datetime(
        df["Datum unosa"], format="%d.%m.%Y"
    ).dt.date

    # Parse amount like "−50,00"
    df["Iznos"] = df["Iznos"].apply(parse_eu_number)

    # Rename to normalized schema
    df = df.rename(
        columns={
            "Datum unosa": "date",
            "Iznos": "amount_original",
            "Opis": "description",
            "Bilješka": "notes",
        }
    )

    # Normalize extra fields
    df["notes"] = df["notes"].fillna("")
    df["amount_eur"] = df["amount_original"]
    df["currency_original"] = "EUR"
    df["account_name"] = "Erste"
    df["category"] = None

    return df.to_dict(orient="records")


def parse_monobank(file_path: str) -> List[Dict]:
    """
    Parse a Monobank CSV file into a list of normalized transaction dicts.
    """
    df = pd.read_csv(file_path, encoding="utf-8")

    # Drop columns which are not relevant
    df = df.drop(
        columns=[
            "MCC",
            "Card currency amount, (UAH)",
            "Exchange rate",
            "Commission, (UAH)",
            "Cashback amount, (UAH)",
            "Balance",
        ],
        errors="ignore",
    )

    # Parse datetime: "29.01.2025 00:59:57"
    df["Date and time"] = pd.to_datetime(
        df["Date and time"], format="%d.%m.%Y %H:%M:%S"
    )

    # Rename to normalized schema
    df = df.rename(
        columns={
            "Date and time": "date",
            "Description": "description",
            "Operation amount": "amount_original",
            "Operation currency": "currency_original",
        }
    )

    # Types
    df["date"] = df["date"].dt.date
    df["amount_original"] = df["amount_original"].astype(float)

    # amount_eur:
    # - if operation currency is EUR → same as amount_original
    # - otherwise (UAH etc.) → None for now
    df["amount_eur"] = np.where(
        df["currency_original"] == "EUR", df["amount_original"], None
    )

    # Extra normalized fields
    df["account_name"] = "Monobank"
    df["category"] = None
    df["notes"] = ""  # Monobank export has no notes column

    return df.to_dict(orient="records")


def parse_csv_for_bank(file_path: str, bank: str) -> List[Dict]:
    """
    Dispatch to the correct bank-specific parser based on `bank` string.
    """
    bank_lower = bank.lower()

    if bank_lower == "erste":
        return parse_erste(file_path)
    elif bank_lower == "monobank":
        return parse_monobank(file_path)
    elif bank_lower == "revolut":
        return parse_revolut(file_path)
    else:
        # Unknown bank – return empty list for now
        return []


def parse_csvs(batch: dict, batch_id: str, file_paths: list[str], banks: list[str]):
    """
    Read all CSV files in a batch, parse them into normalized
    transaction dicts, assign temp IDs, and store them in `batch`
    under 'transactions' and 'order'.
    """
    all_transactions: Dict[str, Dict] = {}
    order: List[str] = []

    temp_counter = 1

    for file_path, bank in zip(file_paths, banks):
        rows = parse_csv_for_bank(file_path, bank)

        for row in rows:
            temp_id = f"t{temp_counter}"
            temp_counter += 1

            row["temp_id"] = temp_id
            row["batch_id"] = batch_id
            row["bank"] = bank

            all_transactions[temp_id] = row
            order.append(temp_id)

    batch["transactions"] = all_transactions
    batch["order"] = order