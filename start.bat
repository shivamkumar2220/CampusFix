@echo off
REM ==============================================================
REM  CampusFix - double-click this file to start the project.
REM  It starts the backend and opens the login page in your browser.
REM  First time only: run setup first (see README, "Quick start").
REM ==============================================================

cd /d "%~dp0backend"

if not exist venv\Scripts\python.exe (
    echo Virtual environment not found. Creating it and installing packages...
    python -m venv venv
    venv\Scripts\python.exe -m pip install -r requirements.txt
)

echo Opening the login page...
start "" "http://localhost:8000/app/pages/login.html"

echo Starting CampusFix on http://localhost:8000  (press Ctrl+C to stop)
venv\Scripts\python.exe -m uvicorn app.main:app --reload
