# Finance Tracker Webapp (v0.1)

Personal finance web application built with **FastAPI** + **SQLite**.

This version is an early checkpoint (v0.1) focused on the CSV import pipeline.  
Core “analytics” / dashboard functionality is planned but not implemented yet.

---

## Tech Stack

- Python 3.12
- FastAPI
- Uvicorn
- SQLAlchemy + SQLite
- Jinja2 templates
- Vanilla JavaScript + HTML + CSS

---

## Current Features (v0.1)

- Basic FastAPI project structure (`app/` package)
- SQLite database with a single `Transaction` table
- `/transactions` page that lists all saved transactions
- CSV upload flow:
  1. **Upload CSVs** with selected bank
  2. **Preview & edit** parsed transactions in an inline-editable table
  3. **Review** final, read-only list of transactions
  4. **Save batch** into the database

Data is stored in `database/finance.db` (ignored by Git).

---

## Project Structure

```text
FINANCE-TRACKER-WEBAPP/
├── app/
│   ├── main.py               # FastAPI app + routes
│   ├── models.py             # SQLAlchemy models (Transaction)
│   ├── db.py                 # DB engine + SessionLocal + Base
│   ├── services/
│   │   ├── csv_import.py     # CSV parsing & normalization
│   │   └── import_helpers.py # dict -> Transaction helpers
│   ├── static/
│   │   ├── css/              # styles for pages
│   │   └── js/               # upload & preview JS
│   └── templates/
│       ├── upload.html
│       ├── upload_preview.html
│       ├── upload_review.html
│       └── transactions.html
├── database/
│   └── finance.db            # local SQLite DB (gitignored)
├── notes/                    # personal notes (optional)
├── requirements.txt
├── .gitignore
└── README.md