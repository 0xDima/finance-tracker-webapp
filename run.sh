#!/bin/bash

# Go to project root
cd /Users/test/Documents/Documents/Personal/projects/finance-tracker-webapp

# Activate virtual environment
source venv/bin/activate

# Open browser after a short delay
(
  sleep 2
  open http://127.0.0.1:8000/dashboard
) &

# Start the FastAPI app
uvicorn main:app --reload
