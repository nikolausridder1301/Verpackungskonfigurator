import pytest
from pydantic import ValidationError

from app.models import Artikel


def gültige_artikel_daten(**overrides):
    daten = {
        "artikel_id": "A-1",
        "bezeichnung": "Testartikel",
        "laenge_mm": 100,
        "breite_mm": 50,
        "hoehe_mm": 30,
        "gewicht_kg": 1.5,
        "menge": 10,
    }
    daten.update(overrides)
    return daten


def test_artikel_zerbrechlich_default_false():
    artikel = Artikel(**gültige_artikel_daten())
    assert artikel.zerbrechlich is False


def test_artikel_zerbrechlich_setzbar():
    artikel = Artikel(**gültige_artikel_daten(zerbrechlich=True))
    assert artikel.zerbrechlich is True


def test_artikel_pflichtfeld_fehlt():
    daten = gültige_artikel_daten()
    del daten["gewicht_kg"]
    with pytest.raises(ValidationError):
        Artikel(**daten)


def test_artikel_menge_muss_ganzzahl_sein():
    with pytest.raises(ValidationError):
        Artikel(**gültige_artikel_daten(menge="drei"))
