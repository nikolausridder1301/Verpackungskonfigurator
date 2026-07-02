import time
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as main_modul
from app.main import app
from app.models import Artikel
from app.packer import berechne_packloesung

client = TestClient(app)

DEMO_CSV = Path(__file__).resolve().parent.parent.parent / "beispiele" / "demo_sendung.csv"


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_packaging_catalog_liefert_alle_einträge():
    response = client.get("/packaging-catalog")
    assert response.status_code == 200
    daten = response.json()
    assert isinstance(daten, list)
    assert len(daten) >= 2
    for eintrag in daten:
        assert "id" in eintrag
        assert "typ" in eintrag
        assert eintrag["kosten_eur"] > 0
        assert eintrag["max_zuladung_kg"] > 0


# --- Issues #4/#5: Upload ---


def upload(dateiname: str, inhalt: bytes):
    return client.post("/upload", files={"datei": (dateiname, inhalt, "text/csv")})


def test_upload_demo_csv_erfolgreich():
    response = upload("demo_sendung.csv", DEMO_CSV.read_bytes())
    assert response.status_code == 200
    daten = response.json()
    assert len(daten["artikel"]) == 3
    assert daten["artikel"][2]["zerbrechlich"] is True
    assert daten["warnungen"] == []


def test_upload_mit_fehlern_liefert_zeilenbezogene_meldungen():
    inhalt = (
        "artikel_id,bezeichnung,laenge_mm,breite_mm,hoehe_mm,gewicht_kg,menge\n"
        "A-1,Koffer,150,100,80,,12\n"
    ).encode("utf-8")
    response = upload("kaputt.csv", inhalt)
    assert response.status_code == 422
    fehler = response.json()["detail"]["fehler"]
    assert fehler[0]["zeile"] == 2
    assert "Gewicht" in fehler[0]["meldung"]


def test_upload_falsches_format():
    response = upload("sendung.txt", b"egal")
    assert response.status_code == 422
    assert "nicht unterstützt" in response.json()["detail"]["fehler"][0]["meldung"]


# --- Issues #17/#34: Berechnung End-to-End ---


def test_upload_bis_berechnung_end_to_end():
    upload_response = upload("demo_sendung.csv", DEMO_CSV.read_bytes())
    artikel = upload_response.json()["artikel"]

    response = client.post("/calculate", json={"artikel": artikel})
    assert response.status_code == 200
    ergebnis = response.json()

    assert ergebnis["gesamtkosten_eur"] > 0
    assert ergebnis["gesamtgewicht_kg"] > 0
    assert len(ergebnis["einheiten"]) >= 1
    # Alle Stück der Demo-Sendung sind platziert
    gesamt_menge = sum(a["menge"] for a in artikel)
    platziert = sum(len(e["platzierungen"]) for e in ergebnis["einheiten"])
    assert platziert == gesamt_menge
    for einheit in ergebnis["einheiten"]:
        assert einheit["lagen"]
        for p in einheit["platzierungen"]:
            assert p["x_mm"] + p["laenge_mm"] <= einheit["basis_laenge_mm"] + 1e-6
            assert p["y_mm"] + p["breite_mm"] <= einheit["basis_breite_mm"] + 1e-6
            assert p["z_mm"] + p["hoehe_mm"] <= einheit["max_hoehe_mm"] + 1e-6


def test_positionsdaten_der_api_entsprechen_der_kernlogik():
    """Akzeptanzkriterium 9.1: Response-Positionen == intern berechnete Positionen."""
    upload_response = upload("demo_sendung.csv", DEMO_CSV.read_bytes())
    artikel_json = upload_response.json()["artikel"]

    artikel = [Artikel(**a) for a in artikel_json]
    intern = berechne_packloesung(
        artikel, main_modul.config.verpackungen, main_modul.config.toleranz
    )

    response = client.post("/calculate", json={"artikel": artikel_json})
    extern = response.json()

    assert len(extern["einheiten"]) == len(intern.einheiten)
    for e_ext, e_int in zip(extern["einheiten"], intern.einheiten):
        for p_ext, p_int in zip(e_ext["platzierungen"], e_int.platzierungen):
            assert p_ext["x_mm"] == p_int.x_mm
            assert p_ext["y_mm"] == p_int.y_mm
            assert p_ext["z_mm"] == p_int.z_mm
            assert p_ext["lage_index"] == p_int.lage_index


def test_berechnung_artikel_zu_gross_fehlerfall():
    artikel = [
        {
            "artikel_id": "riese",
            "bezeichnung": "Maschinenteil",
            "laenge_mm": 1300,
            "breite_mm": 900,
            "hoehe_mm": 1900,
            "gewicht_kg": 40,
            "menge": 1,
        }
    ]
    response = client.post("/calculate", json={"artikel": artikel})
    assert response.status_code == 422
    assert "riese" in response.json()["detail"]["meldung"]


def test_berechnung_ohne_artikel():
    response = client.post("/calculate", json={"artikel": []})
    assert response.status_code == 422


# --- Issue #18: Timeout ---


def test_timeout_bricht_berechnung_kontrolliert_ab(monkeypatch):
    def langsame_berechnung(*args, **kwargs):
        time.sleep(2)

    monkeypatch.setattr(main_modul, "berechne_packloesung", langsame_berechnung)
    monkeypatch.setattr(main_modul, "BERECHNUNGS_TIMEOUT_S", 0.2)

    artikel = [
        {
            "artikel_id": "A-1",
            "bezeichnung": "Koffer",
            "laenge_mm": 90,
            "breite_mm": 70,
            "hoehe_mm": 45,
            "gewicht_kg": 1,
            "menge": 1,
        }
    ]
    response = client.post("/calculate", json={"artikel": artikel})
    assert response.status_code == 504
    assert "zu komplex" in response.json()["detail"]["meldung"]
