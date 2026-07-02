# Verpackungskonfigurator

Webbasierter Versandplaner: berechnet für eine Sendung mit gemischten Artikeln automatisch die
kostengünstigste Verpackungskombination (Kartons/Paletten), erzwingt eine stabile, blockartige
Anordnung und zeigt einen visuellen Versandplan (Drauf- und Seitenansicht).

Details zur Spezifikation: siehe [SPEC.md](SPEC.md).

## Bedienung: In 3 Schritten vom Upload zum Versandplan

1. **Sendungsdatei hochladen** — Auf der Startseite die CSV- oder Excel-Datei mit den Artikeln
   der Sendung in das Upload-Feld ziehen (oder klicken und auswählen). Zum Ausprobieren liegt
   eine fertige Beispieldatei unter [beispiele/demo_sendung.csv](beispiele/demo_sendung.csv) bereit.
   Fehler in der Datei (fehlende Werte, ungültige Zahlen) werden sofort mit Zeilenangabe angezeigt.
2. **Artikel prüfen** — Die eingelesenen Artikel erscheinen in einer Vorschautabelle
   (inkl. Zerbrechlich-Kennzeichnung). Wenn alles stimmt: **„Versandplan berechnen"** klicken.
3. **Ergebnis kontrollieren** — Die Übersicht zeigt Gesamtkosten, Gesamtgewicht und die Anzahl
   der Verpackungseinheiten. Jede Einheit hat eine eigene Karte mit Draufsicht je Lage und
   Seitenansicht (⌖ = Schwerpunkt). Farbige Flächen = Artikeltypen, schraffiert = zerbrechlich;
   Antippen/Überfahren eines Artikels zeigt Details. Ein rotes Banner weist auf
   Stabilitätswarnungen hin — dann bitte manuell prüfen.

### Format der Sendungsdatei

Pflichtspalten: `artikel_id`, `bezeichnung`, `laenge_mm`, `breite_mm`, `hoehe_mm`, `gewicht_kg`,
`menge`. Optional: `zerbrechlich` (ja/nein). Beispiel: [beispiele/demo_sendung.csv](beispiele/demo_sendung.csv).

## Stack

- Backend: Python 3.11+ / FastAPI (Packalgorithmus: Greedy / First-Fit-Decreasing)
- Frontend: React (Vite) + TypeScript, Visualisierung als SVG
- Verpackungsstammdaten & Toleranz: `backend/data/packaging_catalog.yaml`
  (Änderungen greifen nach Neustart des Backends)

## Starten

### Variante A: Start-Skript (ohne Docker)

**macOS:** Doppelklick auf `Verpackungskonfigurator starten.command` — startet beides und
öffnet automatisch den Browser. Das Terminal-Fenster während der Nutzung offen lassen.

**Windows:** Doppelklick auf `start.bat` (oder in der Eingabeaufforderung ausführen).
Alternativ in PowerShell:
```powershell
./start.ps1
```

**Linux/Git Bash:**
```bash
./start.sh
```

Das Skript installiert beim ersten Lauf automatisch die Abhängigkeiten (Python venv + npm) und startet:
- Backend auf http://localhost:8000 (Health-Check: `/health`, Katalog: `/packaging-catalog`)
- Frontend auf http://localhost:5173

### Variante B: Docker Compose

```bash
docker compose up --build
```

Frontend: http://localhost:5173 — Backend: http://localhost:8000.
Die Verpackungsstammdaten sind als Volume eingebunden (`backend/data/`) und können ohne
Neu-Build geändert werden (Container-Neustart genügt). Nach dem initialen Build ist keine
Internetverbindung mehr nötig.

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

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest -v
```
