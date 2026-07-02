$root = $PSScriptRoot

if (-not (Test-Path "$root\backend\venv")) {
    Write-Host "Erstelle Python venv..."
    python -m venv "$root\backend\venv"
    & "$root\backend\venv\Scripts\pip.exe" install -r "$root\backend\requirements.txt"
}

if (-not (Test-Path "$root\frontend\node_modules")) {
    Write-Host "Installiere Frontend-Abhaengigkeiten..."
    Push-Location "$root\frontend"
    npm install
    Pop-Location
}

Write-Host "Starte Backend auf http://localhost:8000 ..."
Start-Process -FilePath "$root\backend\venv\Scripts\uvicorn.exe" -ArgumentList "app.main:app --port 8000" -WorkingDirectory "$root\backend"

Write-Host "Starte Frontend auf http://localhost:5173 ..."
Push-Location "$root\frontend"
# Hinweis: "npm run dev" bricht auf Windows ab, wenn der Pfad ein "&" enthaelt
# (z.B. OneDrive-Pfade mit Firmennamen). Direkter node-Aufruf umgeht das.
node node_modules/vite/bin/vite.js
Pop-Location
