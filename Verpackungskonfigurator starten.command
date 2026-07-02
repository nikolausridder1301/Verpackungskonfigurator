#!/bin/bash
# Doppelklick-Start fuer macOS: startet Backend + Frontend und oeffnet den Browser.
# Das Terminal-Fenster waehrend der Nutzung offen lassen; Schliessen beendet die App.
cd "$(dirname "$0")"

# Browser oeffnen, sobald das Frontend erreichbar ist (max. 5 Minuten warten,
# der erste Start kann wegen der Installation der Abhaengigkeiten dauern)
(
  for _ in $(seq 1 300); do
    if curl -s -o /dev/null http://localhost:5173; then
      open http://localhost:5173
      exit 0
    fi
    sleep 1
  done
) &

./start.sh
