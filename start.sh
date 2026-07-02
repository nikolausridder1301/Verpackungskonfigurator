#!/bin/bash
set -e
root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "$root/backend/venv" ]; then
  echo "Erstelle Python venv..."
  python=$(command -v python3 || command -v python)
  "$python" -m venv "$root/backend/venv"
  "$root/backend/venv/bin/pip" install -r "$root/backend/requirements.txt" 2>/dev/null || \
    "$root/backend/venv/Scripts/pip" install -r "$root/backend/requirements.txt"
fi

if [ ! -d "$root/frontend/node_modules" ]; then
  echo "Installiere Frontend-Abhaengigkeiten..."
  (cd "$root/frontend" && npm install)
fi

echo "Starte Backend auf http://localhost:8000 ..."
if [ -x "$root/backend/venv/bin/uvicorn" ]; then
  uvicorn_bin="$root/backend/venv/bin/uvicorn"       # macOS/Linux
else
  uvicorn_bin="$root/backend/venv/Scripts/uvicorn"   # Windows (Git Bash)
fi
(cd "$root/backend" && "$uvicorn_bin" app.main:app --port 8000) &

echo "Starte Frontend auf http://localhost:5173 ..."
# Hinweis: "npm run dev" bricht auf Windows ab, wenn der Pfad ein "&" enthaelt
# (z.B. OneDrive-Pfade mit Firmennamen). Direkter node-Aufruf umgeht das.
(cd "$root/frontend" && node node_modules/vite/bin/vite.js)
