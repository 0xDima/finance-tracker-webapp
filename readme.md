# Finance Tracker Web App (v0.1)

Personal finance web application built for my own use.  
It imports bank statements (CSV), lets me review/edit/categorize transactions before saving, stores everything in a local SQLite database, and provides a dashboard with monthly insights.

---

## What it does

### CSV Import flow
- Upload one or more CSV bank statements
- Backend normalization & validation
- Preview table with:
  - inline editing
  - category selection
  - delete-before-import
- Review page (read-only confirmation)
- Save batch into SQLite via SQLAlchemy

### Dashboard
- Monthly summary (Income / Expenses / Net)
- Spending by category chart (interactive)
- Clickable category chips (redirect to filtered transactions)
- “Previous month imported” indicator
- Top 10 largest transactions (previous month)
- Navigation buttons: **Upload** / **Transactions**

### Transactions page
- Loads transactions from SQLite
- Advanced filtering:
  - date range
  - category
  - account
  - min/max amount
  - text search

---

## Who it’s for
This project is intentionally built **for personal use only**.  
There is no authentication, no multi-user logic, and no hosted deployment target (yet).

---

## Why this project exists
I previously tracked finances using CSV → Python → Excel workflows.  
This app replaces that flow with a **single, persistent, and user-friendly system** that:
- keeps all transactions in SQL
- provides fast monthly insights
- reduces manual work and mistakes
- makes financial analysis easier to read and reason about

---

## Tech stack
- **Backend:** FastAPI
- **Templating:** Jinja2
- **ORM:** SQLAlchemy
- **Database:** SQLite
- **Frontend:** Vanilla JS, CSS
- **Charts:** Chart.js

---

## Project structure (high level)
app/
main.py
routes_*.py
deps.py
templates/
static/
services/
scripts/
uploads/        # gitignored
*.db            # gitignored


---

## Setup

### 1) Create virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload



## Current version

**v1 — Stable personal MVP**

✔ Upload → review → save  
✔ Dashboard analytics  
✔ Full transaction filtering  
✔ Legacy Excel data migrated  

This version is stable enough for monthly real usage.

---

## Future ideas / Roadmap

### Short-term (v2)
- Dashboard UI polish
- Improve “Previous month transactions” UX
- Import history tracking (which months were imported)
- Smarter category management

### Medium-term (v1.x)
- Rule-based auto-categorization
- AI-assisted category suggestions
- Monthly trend comparisons
- Better error reporting & import diagnostics

### Long-term (v2+)
- Crypto portfolio tracking
- Stock portfolio tracking
- Investment performance overview
- Optional authentication & sessions
- Export & backup:
  - CSV export
  - Google Drive sync
  - Notion export

---

## Notes
- Database is local SQLite
- Deleting the database file will reset all data
- This repository represents a learning + personal productivity project