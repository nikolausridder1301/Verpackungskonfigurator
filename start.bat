@echo off
setlocal
rem Startet Backend (FastAPI, Port 8000) und Frontend (Vite, Port 5173).
rem Installiert beim ersten Lauf automatisch alle Abhaengigkeiten.
set "ROOT=%~dp0"

if not exist "%ROOT%backend\venv" (
    echo Erstelle Python venv...
    python -m venv "%ROOT%backend\venv"
    "%ROOT%backend\venv\Scripts\pip.exe" install -r "%ROOT%backend\requirements.txt"
)

if not exist "%ROOT%frontend\node_modules" (
    echo Installiere Frontend-Abhaengigkeiten...
    pushd "%ROOT%frontend"
    call npm install
    popd
)

echo Starte Backend auf http://localhost:8000 ...
start "Verpackungskonfigurator Backend" /D "%ROOT%backend" "%ROOT%backend\venv\Scripts\uvicorn.exe" app.main:app --port 8000

echo Starte Frontend auf http://localhost:5173 ...
pushd "%ROOT%frontend"
rem Hinweis: "npm run dev" bricht auf Windows ab, wenn der Pfad ein "&" enthaelt
rem (z.B. OneDrive-Pfade mit Firmennamen). Direkter node-Aufruf umgeht das.
node node_modules\vite\bin\vite.js
popd
