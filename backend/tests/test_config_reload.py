"""Issue #35: Änderungen an packaging_catalog.yaml werden nach Neustart übernommen.

Die Config wird beim Anwendungsstart einmalig geladen (app/main.py). Dieser Test
simuliert den Neustart durch erneutes load_config() nach Dateiänderung und
verifiziert, dass die Berechnung die neuen Werte verwendet.
"""

from pathlib import Path

from app.config import load_config
from app.models import Artikel
from app.packer import berechne_packloesung

CONFIG_V1 = """
verpackungen:
  - id: box_klein
    typ: karton
    innenmaße_mm: {laenge: 200, breite: 150, hoehe: 100}
    max_zuladung_kg: 15
    kosten_eur: 1.00
"""

CONFIG_V2 = """
verpackungen:
  - id: box_klein
    typ: karton
    innenmaße_mm: {laenge: 200, breite: 150, hoehe: 100}
    max_zuladung_kg: 15
    kosten_eur: 5.00
  - id: box_gross
    typ: karton
    innenmaße_mm: {laenge: 400, breite: 300, hoehe: 250}
    max_zuladung_kg: 25
    kosten_eur: 2.00
"""


def test_config_aenderung_wird_nach_neustart_uebernommen(tmp_path: Path):
    config_datei = tmp_path / "packaging_catalog.yaml"
    artikel = [
        Artikel(
            artikel_id="A-1",
            bezeichnung="Koffer",
            laenge_mm=90,
            breite_mm=70,
            hoehe_mm=45,
            gewicht_kg=1,
            menge=4,
        )
    ]

    # "Erster Start": nur box_klein für 1.00 EUR verfügbar
    config_datei.write_text(CONFIG_V1, encoding="utf-8")
    config = load_config(config_datei)
    ergebnis = berechne_packloesung(artikel, config.verpackungen, config.toleranz)
    assert ergebnis.anzahl_je_typ == {"box_klein": 1}
    assert ergebnis.gesamtkosten_eur == 1.00

    # Config wird geändert, Anwendung "neu gestartet" (Config neu geladen)
    config_datei.write_text(CONFIG_V2, encoding="utf-8")
    config = load_config(config_datei)
    ergebnis = berechne_packloesung(artikel, config.verpackungen, config.toleranz)
    # box_klein ist jetzt teurer als box_gross -> neue Werte greifen in der Berechnung
    assert ergebnis.anzahl_je_typ == {"box_gross": 1}
    assert ergebnis.gesamtkosten_eur == 2.00
