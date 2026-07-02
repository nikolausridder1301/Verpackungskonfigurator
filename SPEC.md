# SPEC.md – Intelligenter Versandplaner (Packaging Optimizer)

**Projekt:** Webbasierter Versandplaner zur automatisierten, kostenoptimierten und sicheren Verpackungsplanung
**Auftraggeber:** Nikolaus Ridder, SK Group
**Stand:** 02.07.2026
**Version:** 1.0 (Erstspezifikation)

---

## 1. Ziel

### 1.1 Problem
Die manuelle Verpackungsplanung ist:
- **Ineffizient**: hoher Zeitaufwand pro Sendung, abhängig von der Erfahrung einzelner Mitarbeiter.
- **Kostenintensiv**: nicht gewichtsoptimierte Verpackungswahl führt zu unnötig hohen Frachtkosten.
- **Riskant**: inkonsistente, instabile Verladung gefährdet die Transportsicherheit (Beschädigung, Unfallrisiko).

### 1.2 Lösung
Eine lokal betriebene Webanwendung, die für eine Sendung mit gemischten Artikeln automatisch:
1. die **kostengünstigste Verpackungskombination** (Kartons/Paletten) berechnet,
2. eine **physikalisch stabile, blockartige Anordnung** der Artikel erzwingt,
3. einen **visuellen Versandplan** (2D-Grafik: Drauf- und Seitenansicht) zur schnellen Prüfung erzeugt.

### 1.3 Nicht-Ziele (out of scope für v1)
- Keine ERP-/WMS-Anbindung.
- Kein Mehrbenutzerbetrieb, keine Authentifizierung.
- Kein PDF-/Datenexport (nur Bildschirmansicht).
- Keine Anbindung an Versandlabel-Drucker/Carrier-APIs.
- Keine 3D-Visualisierung.
- Keine Cloud-Bereitstellung (lokaler Betrieb).

---

## 2. Zielgruppe & Nutzungskontext

- **Primäre Nutzer:** gemischt – Versandplaner im Büro (Sendungsvorbereitung) sowie Lagerpersonal an der Packstation (Tablet, Ausführung/Kontrolle des Plans).
- **Betriebsmodus:** Einzelplatzanwendung, lokal installiert, ein Nutzer gleichzeitig, keine Anmeldung.
- **Endgeräte:** Desktop-Browser im Büro, Tablet-Browser am Lagerarbeitsplatz (responsives Layout erforderlich, kein natives App-Deployment).

---

## 3. Technischer Stack (Empfehlung)

| Komponente | Wahl | Begründung |
|---|---|---|
| Backend | Python 3.11+ / FastAPI | Starke numerische/Optimierungs-Bibliotheken (NumPy), einfache REST-API, gut wartbar |
| Packalgorithmus | Eigene Heuristik (Greedy + First-Fit-Decreasing-Variante) | Schnell genug für 1–3 Artikeltypen, verständlich, ohne Solver-Abhängigkeit |
| Frontend | React (Vite) + TypeScript | Reaktive UI, gute Bibliotheken für 2D-Rendering (SVG/Canvas) |
| Visualisierung | SVG-Rendering (react + d3 oder reines SVG) | Präzise, skalierbare 2D-Darstellung von Drauf-/Seitenansicht |
| Datenhaltung | Lokale SQLite-Datei (nur Verpackungsstammdaten als Config; Sendungsdaten pro Session, nicht persistent) | Kein Serverbetrieb nötig, einfache Sicherung |
| Bereitstellung | Docker-Compose (Backend + Frontend) oder einfaches Start-Skript für lokalen Rechner | Ein-Klick-Start ohne IT-Infrastruktur |

**Hinweis:** Da keine Mehrbenutzer-Anforderung besteht, kann das Backend auch direkt auf `localhost` laufen; kein Reverse Proxy oder Cloud-Hosting nötig.

---

## 4. Datenmodell

### 4.1 Verpackungsstammdaten (fest im Code/Config hinterlegt, v1)
Konfigurationsdatei (z.B. `packaging_catalog.yaml`) mit Einträgen je Verpackungstyp:

```yaml
- id: karton_s
  typ: karton
  innenmaße_mm: {laenge: 200, breite: 150, hoehe: 100}
  eigengewicht_kg: 0.3
  max_zuladung_kg: 15
  kosten_eur: 1.20

- id: euro_palette
  typ: palette
  grundflaeche_mm: {laenge: 1200, breite: 800}
  max_stapelhoehe_mm: 1800
  max_zuladung_kg: 500
  kosten_eur: 8.00
```

Unterstützte Verpackungstypen v1: **Standardkartons** (rechteckig, feste Größen) und **Paletten** (EUR/Industrie, mit max. Stapelhöhe).

Änderungen an dieser Liste erfolgen durch manuelle Bearbeitung der Config-Datei durch einen Administrator/Entwickler (kein Admin-UI in v1).

### 4.2 Sendungsdaten (Input pro Berechnung)
Upload einer CSV/Excel-Datei pro Sendung mit Spalten:

| Spalte | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| artikel_id | string | ja | Eindeutige Kennung |
| bezeichnung | string | ja | Klartextname |
| laenge_mm | number | ja | Artikelmaß |
| breite_mm | number | ja | Artikelmaß |
| hoehe_mm | number | ja | Artikelmaß |
| gewicht_kg | number | ja | Stückgewicht |
| menge | integer | ja | Stückzahl dieses Artikeltyps |
| zerbrechlich | boolean | nein (default: false) | Zerbrechlichkeits-Flag |

**Erwarteter Sendungsumfang (v1):** 1–3 unterschiedliche Artikeltypen, jeweils 1 bis mehrere Dutzend Stück (z.B. 3 Typen à 50 Stück). Die Anwendung ist für diesen Umfang performance-optimiert; größere Sortimentsvielfalt ist nicht Ziel von v1 (siehe Abschnitt 8, Skalierungs-Grenze).

---

## 5. Kernfunktionen

### 5.1 Eingabe
- Datei-Upload (CSV/XLSX) über die Web-UI.
- Validierung direkt nach Upload (siehe 6. Edge Cases) mit sofortigem, verständlichem Feedback bei Fehlern (z.B. „Zeile 4: Gewicht fehlt oder ist 0 – bitte korrigieren.").
- Vorschau der eingelesenen Artikelliste in einer Tabelle vor Berechnung, mit Möglichkeit, offensichtliche Fehler direkt zu sehen.

### 5.2 Optimierungslogik

**Algorithmus:** Heuristischer Ansatz (Greedy / First-Fit-Decreasing):

1. Artikel werden nach Volumen absteigend sortiert.
2. Für jede verfügbare Verpackung wird geprüft, wie viele Artikel (unter Beachtung Rotation, Gewichts- und Stapelgrenzen) hineinpassen.
3. Die Kombination mit den **geringsten Gesamtkosten** (Summe der Verpackungskosten) wird gewählt, die alle Artikel unterbringt.
4. Rotation: Artikel dürfen **frei in allen drei Achsen rotiert werden**, um die Packdichte zu maximieren.

**Kostenoptimierung:** Zielfunktion = Minimierung der Summe aus Verpackungskosten (`kosten_eur` je genutzter Verpackungseinheit). Bei Kostengleichstand wird die Kombination mit weniger Einzelverpackungen bevorzugt (einfachere Handhabung).

### 5.3 Sicherheitslogik (Stabilität)

- **Blockartige Anordnung:** Artikel werden in Lagen (Layern) angeordnet; jede Lage wird so weit wie möglich vollständig gefüllt, bevor die nächste beginnt.
- **Schwerpunkt-Check:** Der Gesamtschwerpunkt der Ladung (inkl. aller Lagen) muss innerhalb der Grundfläche der Verpackung liegen. Schwere Artikel werden bevorzugt in unteren Lagen platziert.
- **Stapelgrenzen:** Maximale Stapelhöhe (aus Verpackungsstammdaten) und maximales Zuladungsgewicht pro Verpackungstyp werden hart durchgesetzt (harte Nebenbedingung, kein Override möglich).
- **Toleranz:** Ein fester globaler Toleranzwert (Standard: **±2 mm bzw. 1% der Artikelmaße**, konfigurierbar in der Config-Datei) wird bei der Platzierung berücksichtigt, um reale Fertigungstoleranzen abzubilden, ohne die Blockstabilität zu gefährden.
- **Zerbrechlichkeit:** Als zerbrechlich markierte Artikel werden nicht als unterste Lage unter schwereren/nicht-zerbrechlichen Artikeln platziert (weiche Regel, wird bei Verletzung im Ergebnis gewarnt).

### 5.4 Visualisierung

- **Zwei kombinierte 2D-Ansichten** pro Verpackungseinheit:
  1. **Draufsicht (Grundriss)** je Lage – zeigt exakte X/Y-Positionen aller Artikel dieser Lage.
  2. **Seitenansicht (Querschnitt)** – zeigt die vertikale Stapelreihenfolge und Schwerpunktlage zur Plausibilitätsprüfung.
- Jede Verpackungseinheit (Karton/Palette) erhält eine eigene Kachel/Karte in der UI mit beiden Ansichten nebeneinander.
- Artikel werden farblich nach Artikeltyp codiert; zerbrechliche Artikel zusätzlich mit Symbol/Muster markiert.
- Mouseover/Tap auf einen Artikel zeigt Details (ID, Maße, Gewicht) als Tooltip.
- Darstellung ist reine Bildschirmansicht; kein Export in v1.

### 5.5 Ergebnisübersicht
- Zusammenfassung pro Sendung: Anzahl benötigter Verpackungseinheiten je Typ, Gesamtkosten, Gesamtgewicht.
- Klare Kennzeichnung, falls Warnungen vorliegen (siehe 6.2).

---

## 6. Edge Cases

### 6.1 Eingabevalidierung
| Fall | Verhalten |
|---|---|
| Fehlende Pflichtfelder | Upload wird abgelehnt, Zeile(n) mit Fehler werden benannt |
| Negative/Null-Werte bei Maßen/Gewicht | Upload wird abgelehnt mit Hinweis |
| Doppelte artikel_id | Warnung, Zusammenfassung der Mengen unter der ersten ID |
| Leere Datei | Fehlermeldung „Keine Artikel gefunden" |

### 6.2 Packlogik
| Fall | Verhalten |
|---|---|
| **Artikel größer als jede verfügbare Verpackung** | Sendung wird nicht berechnet; klare Fehlermeldung mit Angabe, welcher Artikel (ID, Maße) das Problem verursacht und welche die größte verfügbare Verpackung ist. Kein Teilergebnis. |
| **Keine gültige/stabile Kombination gefunden** | **Best-Effort-Vorschlag** wird trotzdem angezeigt, mit deutlich sichtbarem Warnhinweis (z.B. rote Banner-Meldung „Stabilität nicht garantiert – manuelle Prüfung erforderlich") und Angabe, welche Regel verletzt wurde (z.B. Schwerpunkt außerhalb, Stapelgewicht überschritten). |
| **Restmengen** (Artikel passen nicht vollständig in die zuletzt optimal befüllte Verpackung) | Es wird eine zusätzliche (ggf. kleinere) Verpackungseinheit für den Rest verwendet; im Ergebnis wird ausgewiesen, dass diese letzte Einheit nicht voll ausgelastet ist (z.B. „Palette 3: nur 40% befüllt"). |
| **Gemischte Sendung mit stark unterschiedlichem Gewicht/Zerbrechlichkeit** | Schwerere/robustere Artikel werden algorithmisch in untere Lagen priorisiert; zerbrechliche Artikel werden nach oben/außen priorisiert. Bei Konflikt (z.B. zerbrechlicher Artikel ist auch der schwerste) wird eine Warnung ausgegeben statt eine unsichere Lage stillschweigend zu erzeugen. |

### 6.3 Sonstiges
- Verbindungsabbruch/Fehler im Backend während Berechnung: UI zeigt Fehlermeldung mit Retry-Möglichkeit, kein stiller Fehlschlag.
- Sehr lange Berechnungszeit (Timeout): Bei > 10s Berechnungsdauer (siehe Performance-Ziel unten) wird ein Ladeindikator angezeigt; bei Überschreitung eines harten Timeouts (30s) wird die Berechnung abgebrochen mit Hinweis, dass die Sendung zu komplex für die aktuelle Version ist.

---

## 7. Risiken & Tradeoffs

| Risiko/Tradeoff | Beschreibung | Entscheidung/Mitigation |
|---|---|---|
| **Heuristik statt exaktem Solver** | Greedy-Ansatz liefert nicht immer die mathematisch optimale Lösung, sondern eine gute Näherung. | Akzeptiert für v1, da Sendungen klein sind (1-3 Artikeltypen) und Wartbarkeit/Geschwindigkeit priorisiert werden. Spätere Umstellung auf exakten Solver (z.B. OR-Tools) als Erweiterung möglich, ohne API-Vertrag zu ändern. |
| **Fester globaler Toleranzwert statt pro Artikel** | Einfacher zu konfigurieren und zu verstehen, aber weniger präzise für sehr heterogene Artikelsortimente. | Für v1 akzeptiert; Erweiterung auf pro-Artikel-Toleranz ist im Datenmodell vorbereitbar (optionale Spalte), aber nicht in v1 implementiert. |
| **Einfacher Schwerpunkt-Check statt vollständiger physikalischer Simulation** | Deckt die meisten praktischen Stabilitätsfälle ab, garantiert aber keine 100%ige physikalische Korrektheit (z.B. keine Berücksichtigung von Reibung, dynamischen Kräften beim Transport). | Bewusster Tradeoff zwischen Implementierungsaufwand und Nutzen; App liefert Entscheidungsunterstützung, ersetzt nicht die fachliche Endkontrolle durch den Mitarbeiter. Deshalb: Visuelle Bestätigung als expliziter Kernbestandteil (Pflicht-Review durch Menschen). |
| **Feste Verpackungsliste im Code statt Admin-UI** | Änderungen an Kartongrößen erfordern Entwicklereingriff. | Akzeptiert, da Sortiment „selten Änderung" laut Anforderung. Config-Datei ist aber so gestaltet, dass ein späteres Admin-UI ohne Datenmodelländerung ergänzbar ist. |
| **Keine Persistenz von Sendungsdaten** | Sendungen werden nicht dauerhaft gespeichert (nur CSV-Upload pro Sitzung). | Reduziert Komplexität und Datenschutzrisiko; falls Historisierung später gewünscht wird, ist dies eine separate Erweiterung. |
| **Keine Authentifizierung** | Einzelplatzbetrieb ohne Login erleichtert Nutzung, aber die App darf nicht in einem Netzwerk mit mehreren Zugriffsberechtigten exponiert werden. | Es wird empfohlen, die App ausschließlich lokal (localhost) zu betreiben und nicht ohne Zusatzmaßnahmen im Firmennetz freizugeben. |
| **Freie Rotation aller Artikel** | Maximiert Packdichte/Kosteneffizienz, kann aber bei Artikeln mit funktionalen Einschränkungen (z.B. „darf nicht auf dem Kopf stehen") zu unsicheren Vorschlägen führen, da dies in v1 nicht abgebildet ist. | **Bekannte Einschränkung für v1:** Kein Rotations-Flag pro Artikel. Muss im Rahmen der Akzeptanzkriterien getestet und dem Nutzer klar kommuniziert werden (siehe 8. Akzeptanzkriterien und 9. Bekannte Limitierungen). |

---

## 8. Bekannte Limitierungen (v1)

Explizit **nicht** abgedeckt, sollten aber im Bewusstsein des Auftraggebers sein:

1. Kein Orientierungs-Flag pro Artikel (z.B. „nur aufrecht transportieren") – freie Rotation gilt für alle Artikel gleichermaßen.
2. Keine Berücksichtigung von Reibung, Vibration oder dynamischen Transportkräften – reiner statischer Schwerpunkt-Check.
3. Skalierungsgrenze: ausgelegt für 1–3 Artikeltypen pro Sendung; bei deutlich höherer Artikelvielfalt ist weder Performance noch Optimalität der Heuristik garantiert.
4. Keine Mandantenfähigkeit/Mehrbenutzerbetrieb.
5. Kein Datenexport (PDF/CSV) des Ergebnisses – rein bildschirmbasierte Bestätigung.

---

## 9. Akzeptanzkriterien

Die Anwendung gilt als abnahmefähig, wenn folgende Kriterien erfüllt sind:

### 9.1 Funktional
- [ ] Nutzer kann eine CSV/XLSX-Datei mit Sendungsdaten hochladen; ungültige Dateien werden mit konkreter, zeilenbezogener Fehlermeldung abgelehnt.
- [ ] Für eine gültige Sendung mit 1–3 Artikeltypen berechnet das System eine Verpackungskombination aus Kartons und/oder Paletten gemäß der hinterlegten Stammdaten.
- [ ] Die gewählte Kombination ist nachweislich kostengünstiger oder gleich kostengünstig wie mindestens zwei alternative, manuell konstruierte Vergleichskombinationen (Testfälle).
- [ ] Für jede erzeugte Verpackungseinheit wird eine Draufsicht und eine Seitenansicht angezeigt, die die tatsächliche Artikel-Platzierung korrekt widerspiegelt (Positionsdaten aus Backend = Positionsdaten in Grafik, keine Abweichung).
- [ ] Der Gesamtschwerpunkt jeder Verpackungseinheit liegt nachweislich innerhalb der Grundfläche (per Testfall verifiziert), sofern keine Warnung ausgegeben wird.
- [ ] Maximale Stapelhöhe und maximales Zuladungsgewicht werden nie überschritten (harte Grenze, mit Testfällen für Grenzwertüberschreitung abgesichert).
- [ ] Der definierte Toleranzwert wird nachweislich in der Platzierungslogik berücksichtigt (Testfall mit Artikeln an der Toleranzgrenze).

### 9.2 Edge Cases
- [ ] Ein Artikel, der größer als jede verfügbare Verpackung ist, führt zu einer klaren Fehlermeldung ohne Teilergebnis.
- [ ] Eine Sendung, für die keine stabile Lösung gefunden wird, erzeugt einen Best-Effort-Vorschlag mit sichtbarer Warnung und Begründung der Regel-Verletzung.
- [ ] Restmengen werden in einer zusätzlichen Verpackungseinheit untergebracht, deren Auslastung im Ergebnis ausgewiesen wird.
- [ ] Zerbrechliche Artikel werden nicht standardmäßig unter schwereren Artikeln platziert; bei unvermeidbarem Konflikt erscheint eine Warnung.

### 9.3 Performance
- [ ] Für eine typische Sendung (1-3 Artikeltypen, insgesamt bis 100 Stück) liefert die Berechnung ein Ergebnis in unter 10 Sekunden auf Standard-Bürohardware.
- [ ] Bei Überschreitung von 30 Sekunden Berechnungszeit bricht das System kontrolliert ab und informiert den Nutzer.

### 9.4 UI/UX
- [ ] Die Anwendung ist ohne Anleitung durch einen Versandmitarbeiter bedienbar (Upload → Ergebnis in max. 3 Klicks/Schritten).
- [ ] Die Darstellung ist auf einem Tablet (Lagerarbeitsplatz) ohne Verzerrung oder abgeschnittene Inhalte nutzbar (responsives Layout, getestet auf min. einer gängigen Tablet-Auflösung).
- [ ] Farbcodierung der Artikeltypen sowie Zerbrechlichkeits-Kennzeichnung sind auf den ersten Blick unterscheidbar (Kontrast-Check).
- [ ] Alle Fehlermeldungen sind in verständlicher, konkreter Alltagssprache formuliert (kein technischer Jargon, keine reinen Fehlercodes).

### 9.5 Betrieb
- [ ] Die Anwendung lässt sich mit einem einzigen Befehl/Skript lokal starten (kein manuelles Setup mehrerer Dienste durch den Endnutzer).
- [ ] Keine Internetverbindung notwendig für den Betrieb nach Installation.
- [ ] Änderung der Verpackungsstammdaten (Config-Datei) wird nach Neustart der Anwendung korrekt übernommen (verifiziert per Testfall).

---

## 10. Offene Punkte für spätere Versionen (Backlog, nicht Teil von v1)

- Admin-UI zur Pflege der Verpackungsstammdaten.
- Pro-Artikel-Rotationsbeschränkung und individuelle Toleranzwerte.
- PDF-/CSV-Export des Versandplans.
- Mehrbenutzerbetrieb mit Login und zentraler Datenbank.
- Anbindung an ERP/WMS bzw. Label-Druck-Systeme.
- Exakter Solver (z.B. OR-Tools) als Option für höhere Optimalität bei größeren Sendungen.
- Historisierung/Reporting über vergangene Versandpläne.
