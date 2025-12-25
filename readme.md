# Finance Tracker Web App (v1)

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
```


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



Absolutely — below is **clean, copy-paste-ready README content**, written in a **human, honest, portfolio-friendly tone** (not corporate, not fluffy).

You can paste this **above** your “Current version” section.

---

## Project Overview

This project is a **personal finance tracking web application** built for my own real monthly usage.

I originally managed my finances using CSV exports from different banks and manual Excel processing. Over time, this became slow, error-prone, and difficult to analyze. I decided to build a **proper system** that would allow me to:

- Upload raw bank statements
- Normalize and clean the data
- Review and edit transactions before saving
- Store everything in a structured database
- Analyze monthly spending in a clear, visual way

The result is a stable personal finance app that I actively use to track expenses, income, and monthly trends.

This project is intentionally **not a commercial product** — it’s a practical, well-designed system built to solve a real personal problem and to deepen my understanding of backend, data flows, and system design.

---

## Design Decisions

### Server-rendered UI (FastAPI + Jinja)

I chose **server-rendered templates instead of React** because:
- The app is data-heavy and form-driven
- It simplifies state management for multi-step flows (upload → preview → review → save)
- It keeps the architecture simpler and easier to reason about
- Performance and UX are more than sufficient for personal usage

JavaScript is used only where it adds real value (inline editing, filters, charts).

---

### SQLite as the database

SQLite was chosen because:
- The application is for personal use
- Data is local, private, and small-to-medium in size
- It requires zero infrastructure or setup
- It is reliable, fast, and easy to back up

The database layer is built with SQLAlchemy, making it easy to migrate to another database later if needed.

---

### Batch-based CSV import flow

Bank statement imports are handled as **temporary in-memory batches** because:
- Users should be able to review and edit data before committing
- It prevents accidental bad data from entering the database
- It mirrors real-world ETL pipelines (extract → transform → load)
- It makes error handling and debugging easier

This design prioritizes **data correctness over speed**, which is critical for financial data.

---

## What I Learned

This project significantly improved my understanding of:

- Designing **multi-step backend workflows**
- Handling real-world, messy input data
- Building reliable data validation and normalization pipelines
- Structuring a FastAPI project for long-term maintainability
- Using SQLAlchemy effectively with a real schema
- Balancing frontend interactivity with backend simplicity
- Knowing when **not** to add features and freeze a stable version

Most importantly, I learned how to **finish a project**, define a clear scope, and stop at a stable version instead of endlessly refactoring or overengineering.

---