# Verpackungskonfigurator
Verpackungsdaten auf Basis der Produktabmessung und Vorgabe der Verpackungseinheit und Verpackungsmittel

Details zur Spezifikation: siehe [SPEC.md](SPEC.md).

## Stack
- Backend: Python 3.11+ / FastAPI
- Frontend: React (Vite) + TypeScript
- Verpackungsstammdaten: `backend/data/packaging_catalog.yaml`

## Lokal starten

**Windows (PowerShell):**
```powershell
./start.ps1
```

**macOS/Linux/Git Bash:**
```bash
./start.sh
```

Das Skript installiert beim ersten Lauf automatisch die Abhängigkeiten (Python venv + npm) und startet:
- Backend auf http://localhost:8000 (Health-Check: `/health`, Katalog: `/packaging-catalog`)
- Frontend auf http://localhost:5173

### Manuell starten
```bash
# Backend
cd backend
python -m venv venv
venv/Scripts/activate   # Windows; unter macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000

# Frontend (separates Terminal)
cd frontend
npm install
node node_modules/vite/bin/vite.js   # statt "npm run dev" -- siehe Hinweis unten
```

> **Hinweis (Windows):** Liegt das Projekt in einem Pfad mit `&` (z.B. manche OneDrive-Firmenordner),
> bricht `npm run dev`/`npm run build` mit `MODULE_NOT_FOUND` ab (cmd.exe-Shim-Bug von npm).
> Workaround: Vite direkt über `node node_modules/vite/bin/vite.js` starten.
