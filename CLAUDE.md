# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Siehe [SPEC.md](SPEC.md) für die vollständige Spezifikation. GitHub Issues (#1–39) bilden den Umsetzungsplan ab, gelabelt mit `core` / `supporting` / `nice-to-have`.

## Befehle

**Alles starten (Backend + Frontend, installiert Abhängigkeiten beim ersten Lauf):**
```powershell
./start.ps1        # Windows; ./start.sh für Git Bash/macOS/Linux
```

**Backend einzeln** (FastAPI auf http://localhost:8000):
```bash
cd backend
venv/Scripts/activate          # einmalig: python -m venv venv && pip install -r requirements.txt
uvicorn app.main:app --port 8000 --reload
```

**Frontend einzeln** (Vite-Dev-Server auf http://localhost:5173):
```bash
cd frontend
node node_modules/vite/bin/vite.js
```

**⚠️ Niemals `npm run dev`/`npm run build` verwenden:** Der Projektpfad enthält ein `&` (OneDrive-Firmenordner „Schmidt, Kranz & Co."), was die npm-cmd-Shims unter Windows mit `MODULE_NOT_FOUND` brechen lässt. Immer direkt via `node node_modules/<paket>/bin/<binary>.js` aufrufen. Gleiches gilt für `tsc` beim Build: `node node_modules/typescript/bin/tsc -b && node node_modules/vite/bin/vite.js build`.

**Tests** (Backend, pytest; Dev-Abhängigkeiten via `pip install -r requirements-dev.txt`):
```bash
cd backend && venv/Scripts/activate
python -m pytest -v             # alle Tests
python -m pytest tests/test_config.py -k karton   # einzelner Test
```
CI: `.github/workflows/tests.yml` läuft bei jedem Push (Backend-pytest + Frontend-Build). In CI funktioniert `npm run build` normal — das `&`-Pfadproblem existiert nur lokal.

**Hinweis OneDrive:** pip/npm-Installationen in diesem Ordner sind durch OneDrive-Sync spürbar langsam. `backend/venv/` und `frontend/node_modules/` sind gitignored; ggf. vom Sync ausschließen.

## Architektur

- **backend/** — Python 3.13 / FastAPI. `app/main.py` (API-Endpoints `/health`, `/packaging-catalog`, `/upload`, `/calculate`; CORS für localhost:5173; 30s-Berechnungs-Timeout), `app/config.py` (lädt und validiert `data/packaging_catalog.yaml` inkl. Toleranz beim Start, Fehler = SystemExit), `app/models.py` (Pydantic-Modelle `Artikel`, `Verpackung`, `Toleranz`), `app/parsing.py` (CSV/XLSX-Parsing mit zeilenbezogenen Fehlermeldungen), `app/packer.py` (Packalgorithmus: Greedy/First-Fit-Decreasing mit Lagenbildung, Rotation, Schwerpunkt- und Zerbrechlichkeits-Prüfung — bewusst unabhängig von FastAPI, damit er ohne API testbar bleibt).
- **frontend/** — React 19 (Vite) + TypeScript. Kommuniziert mit dem Backend über REST (`API_BASE` in `src/api.ts`). Ablauf in `App.tsx`: Upload → Vorschau → Berechnung → Ergebnis; SVG-Visualisierung (Drauf-/Seitenansicht) in `src/components/PackeinheitKarte.tsx`, kein Canvas/3D.
- **beispiele/demo_sendung.csv** — Beispieldatei für Onboarding und Integrationstests.
- **backend/data/packaging_catalog.yaml** — Verpackungsstammdaten (Kartons/Paletten), einzige Konfigurationsquelle; Änderungen greifen nach Backend-Neustart. YAML-Keys nutzen deutsche Umlaute (`innenmaße_mm`), das Pydantic-Modell mappt auf `innenmasse_mm`.
- Sendungsdaten (CSV/XLSX-Upload) sind bewusst nicht persistent — nur pro Berechnung im Speicher.

## Harte Geschäftsregeln (nicht verhandelbar, nicht aus Code ableitbar)

- Max. Stapelhöhe und max. Zuladungsgewicht pro Verpackung sind harte Nebenbedingungen — niemals überschreitbar, kein Override.
- Zerbrechlichkeit ist eine weiche Regel: bei Verletzung wird gewarnt, nicht blockiert.
- Toleranzwert Standard ±2mm / 1% der Artikelmaße, konfigurierbar in der Config-Datei.
- Freie Rotation in allen 3 Achsen ist für v1 gewollt (kein Rotations-Flag pro Artikel) — bekannte Einschränkung, nicht nachträglich „fixen".
- Bei fehlender stabiler Lösung: Best-Effort-Ergebnis mit sichtbarer Warnung liefern, niemals stillschweigend eine unsichere Lage ausgeben.
- Artikel größer als jede verfügbare Verpackung: harter Abbruch, kein Teilergebnis.
- Performance-Ziel: <10s typisch, harter Timeout bei 30s mit kontrolliertem Abbruch.
- Alle nutzersichtbaren Fehlermeldungen in verständlicher deutscher Alltagssprache, zeilenbezogen bei Upload-Fehlern.

## Explizit out of scope für v1 (nicht implementieren ohne Rücksprache)

ERP/WMS-Anbindung, Mehrbenutzer/Auth, PDF/Datenexport, Carrier-APIs, 3D-Visualisierung, Cloud-Deployment, Admin-UI für Verpackungsstammdaten.

## Skalierungsannahme

Ausgelegt für 1–3 Artikeltypen pro Sendung, bis ~100 Stück gesamt. Nicht für breite Sortimentsvielfalt optimieren.
