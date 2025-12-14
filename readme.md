# Finance Tracker Webapp (v0.2)

Personal finance web application built with **FastAPI** + **SQLite**, focused on
transaction importing, normalization, and manual analysis.

This version (v0.2) moves beyond the initial CSV import pipeline and introduces
a usable transactions page with filtering, improved UI structure, and clearer
backend separation. Dashboard analytics are partially prepared and will be
expanded in future versions.

---

## Tech Stack

- Python 3.12
- FastAPI
- Uvicorn
- SQLAlchemy + SQLite
- Jinja2 templates
- Vanilla JavaScript, HTML, CSS

---

## Current Features (v0.2)

### Dashboard (WIP)
- `/dashboard` page is implemented (template + styles + JS)
- UI structure is in place, but some backend/metrics are not fully implemented yet
- Planned metrics include income/expenses/net + portfolio cards (crypto/stocks)

### Transactions
- `/transactions` page with:
  - Date range filtering
  - Category filtering
  - Account filtering
  - Clean, readable table layout
- Clickable transactions with full stored details
- Test/debug endpoints for inserting diverse transactions

### CSV Import Pipeline
- Upload multiple CSV files with bank selection
- Parse and normalize data (currency → EUR)
- Preview parsed transactions in an editable table
- Review final, read-only transaction list
- Save validated batches into the database

---

## Project Structure

```text
FINANCE-TRACKER-WEBAPP/
├── app/
│   ├── services/
│   │   ├── csv_import.py
│   │   └── import_helpers.py
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   ├── templates/
│   ├── routes_dashboard.py
│   ├── routes_transactions.py
│   ├── routes_upload.py
│   ├── routes_root.py
│   ├── db.py
│   ├── models.py
│   └── main.py
├── database/
│   └── finance.db   # gitignored
├── uploads/
├── requirements.txt
└── README.md