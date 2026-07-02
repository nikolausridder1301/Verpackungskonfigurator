from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


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
