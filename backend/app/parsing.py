"""Einlesen und Validierung der Sendungsdaten (CSV/XLSX), SPEC 4.2 / 6.1.

Alle Fehlermeldungen sind zeilenbezogen und in Alltagssprache formuliert.
Zeilennummern beziehen sich auf die Datei (Kopfzeile = Zeile 1).
"""

import io
from dataclasses import dataclass, field

import pandas as pd

from app.models import Artikel

PFLICHTSPALTEN = [
    "artikel_id",
    "bezeichnung",
    "laenge_mm",
    "breite_mm",
    "hoehe_mm",
    "gewicht_kg",
    "menge",
]

_WAHR = {"true", "ja", "wahr", "1", "x", "yes"}
_FALSCH = {"false", "nein", "falsch", "0", "", "no"}


class UploadFehler(Exception):
    """Upload wird abgelehnt; enthält zeilenbezogene Fehlermeldungen."""

    def __init__(self, fehler: list[dict]):
        self.fehler = fehler
        super().__init__("; ".join(f["meldung"] for f in fehler))


@dataclass
class ParseErgebnis:
    artikel: list[Artikel]
    warnungen: list[str] = field(default_factory=list)


def _lese_tabelle(dateiname: str, inhalt: bytes) -> pd.DataFrame:
    name = dateiname.lower()
    if name.endswith(".csv"):
        # sep=None erkennt Komma und Semikolon (deutsche CSV) automatisch
        return pd.read_csv(io.BytesIO(inhalt), sep=None, engine="python", dtype=str)
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(io.BytesIO(inhalt), dtype=str)
    raise UploadFehler(
        [
            {
                "zeile": None,
                "meldung": (
                    f"Das Dateiformat von „{dateiname}“ wird nicht unterstützt. "
                    "Bitte eine CSV- oder Excel-Datei (.csv, .xlsx) hochladen."
                ),
            }
        ]
    )


def _zahl(wert: str | None, spalte: str, zeile: int, fehler: list, ganzzahl: bool = False):
    if wert is None or str(wert).strip() == "" or str(wert).lower() == "nan":
        fehler.append(
            {"zeile": zeile, "meldung": f"Zeile {zeile}: {_spaltenname(spalte)} fehlt – bitte ergänzen."}
        )
        return None
    text = str(wert).strip().replace(",", ".")
    try:
        zahl = float(text)
    except ValueError:
        fehler.append(
            {
                "zeile": zeile,
                "meldung": f"Zeile {zeile}: „{wert}“ ist keine gültige Zahl für {_spaltenname(spalte)}.",
            }
        )
        return None
    if ganzzahl:
        if zahl != int(zahl):
            fehler.append(
                {
                    "zeile": zeile,
                    "meldung": f"Zeile {zeile}: Die Menge muss eine ganze Zahl sein (angegeben: {wert}).",
                }
            )
            return None
        zahl = int(zahl)
    if zahl <= 0:
        fehler.append(
            {
                "zeile": zeile,
                "meldung": (
                    f"Zeile {zeile}: {_spaltenname(spalte)} muss größer als 0 sein "
                    f"(angegeben: {wert}) – bitte korrigieren."
                ),
            }
        )
        return None
    return zahl


def _spaltenname(spalte: str) -> str:
    namen = {
        "laenge_mm": "die Länge (laenge_mm)",
        "breite_mm": "die Breite (breite_mm)",
        "hoehe_mm": "die Höhe (hoehe_mm)",
        "gewicht_kg": "das Gewicht (gewicht_kg)",
        "menge": "die Menge",
    }
    return namen.get(spalte, spalte)


def _text(wert, spalte: str, zeile: int, fehler: list) -> str | None:
    if wert is None or str(wert).strip() == "" or str(wert).lower() == "nan":
        name = "die Artikel-ID" if spalte == "artikel_id" else "die Bezeichnung"
        fehler.append({"zeile": zeile, "meldung": f"Zeile {zeile}: {name} fehlt – bitte ergänzen."})
        return None
    return str(wert).strip()


def _zerbrechlich(wert, zeile: int, fehler: list) -> bool | None:
    if wert is None:
        return False
    text = str(wert).strip().lower()
    if text == "nan":
        return False
    if text in _WAHR:
        return True
    if text in _FALSCH:
        return False
    fehler.append(
        {
            "zeile": zeile,
            "meldung": (
                f"Zeile {zeile}: „{wert}“ ist kein gültiger Wert für zerbrechlich – "
                "bitte ja/nein oder true/false verwenden."
            ),
        }
    )
    return None


def parse_sendung(dateiname: str, inhalt: bytes) -> ParseErgebnis:
    """Parst eine Sendungsdatei zu Artikel-Objekten.

    Wirft UploadFehler mit zeilenbezogenen Meldungen, wenn die Datei
    abgelehnt wird (SPEC 6.1). Doppelte artikel_id führt zu Warnung und
    Mengen-Zusammenfassung unter der ersten ID.
    """
    try:
        df = _lese_tabelle(dateiname, inhalt)
    except UploadFehler:
        raise
    except Exception:
        raise UploadFehler(
            [
                {
                    "zeile": None,
                    "meldung": (
                        "Die Datei konnte nicht gelesen werden. Bitte prüfen, ob es sich um eine "
                        "gültige CSV- oder Excel-Datei handelt."
                    ),
                }
            ]
        )

    df.columns = [str(c).strip().lower() for c in df.columns]

    fehlende_spalten = [s for s in PFLICHTSPALTEN if s not in df.columns]
    if fehlende_spalten:
        raise UploadFehler(
            [
                {
                    "zeile": 1,
                    "meldung": (
                        "In der Datei fehlen folgende Spalten: "
                        + ", ".join(fehlende_spalten)
                        + ". Bitte die Kopfzeile prüfen."
                    ),
                }
            ]
        )

    if df.empty:
        raise UploadFehler([{"zeile": None, "meldung": "Keine Artikel gefunden – die Datei enthält keine Datenzeilen."}])

    fehler: list[dict] = []
    warnungen: list[str] = []
    artikel_map: dict[str, Artikel] = {}

    for index, row in df.iterrows():
        zeile = int(index) + 2  # +1 für 0-Index, +1 für Kopfzeile

        artikel_id = _text(row.get("artikel_id"), "artikel_id", zeile, fehler)
        bezeichnung = _text(row.get("bezeichnung"), "bezeichnung", zeile, fehler)
        laenge = _zahl(row.get("laenge_mm"), "laenge_mm", zeile, fehler)
        breite = _zahl(row.get("breite_mm"), "breite_mm", zeile, fehler)
        hoehe = _zahl(row.get("hoehe_mm"), "hoehe_mm", zeile, fehler)
        gewicht = _zahl(row.get("gewicht_kg"), "gewicht_kg", zeile, fehler)
        menge = _zahl(row.get("menge"), "menge", zeile, fehler, ganzzahl=True)
        zerbrechlich = _zerbrechlich(row.get("zerbrechlich"), zeile, fehler)

        if None in (artikel_id, bezeichnung, laenge, breite, hoehe, gewicht, menge, zerbrechlich):
            continue

        if artikel_id in artikel_map:
            artikel_map[artikel_id].menge += menge
            warnungen.append(
                f"Artikel-ID „{artikel_id}“ kommt mehrfach vor (Zeile {zeile}) – "
                "die Mengen wurden unter dem ersten Eintrag zusammengefasst."
            )
            continue

        artikel_map[artikel_id] = Artikel(
            artikel_id=artikel_id,
            bezeichnung=bezeichnung,
            laenge_mm=laenge,
            breite_mm=breite,
            hoehe_mm=hoehe,
            gewicht_kg=gewicht,
            menge=menge,
            zerbrechlich=zerbrechlich,
        )

    if fehler:
        raise UploadFehler(fehler)

    if not artikel_map:
        raise UploadFehler([{"zeile": None, "meldung": "Keine Artikel gefunden – die Datei enthält keine Datenzeilen."}])

    return ParseErgebnis(artikel=list(artikel_map.values()), warnungen=warnungen)
