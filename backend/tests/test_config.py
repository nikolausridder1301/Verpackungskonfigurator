from pathlib import Path

import pytest

from app.config import CATALOG_PATH, ConfigError, load_config, load_packaging_catalog


def write_yaml(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "catalog.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_lädt_mitgelieferten_katalog():
    katalog = load_packaging_catalog(CATALOG_PATH)
    assert len(katalog) >= 2
    ids = {v.id for v in katalog}
    assert "karton_s" in ids
    assert "euro_palette" in ids


def test_karton_felder_werden_gemappt():
    katalog = load_packaging_catalog(CATALOG_PATH)
    karton = next(v for v in katalog if v.id == "karton_s")
    assert karton.typ == "karton"
    assert karton.innenmasse_mm is not None
    assert karton.innenmasse_mm.laenge == 200
    assert karton.innenmasse_mm.breite == 150
    assert karton.innenmasse_mm.hoehe == 100
    assert karton.kosten_eur == pytest.approx(1.20)
    assert karton.max_zuladung_kg == 15


def test_palette_felder_werden_gemappt():
    katalog = load_packaging_catalog(CATALOG_PATH)
    palette = next(v for v in katalog if v.id == "euro_palette")
    assert palette.typ == "palette"
    assert palette.grundflaeche_mm is not None
    assert palette.grundflaeche_mm.laenge == 1200
    assert palette.grundflaeche_mm.breite == 800
    assert palette.max_stapelhoehe_mm == 1800
    assert palette.innenmasse_mm is None


def test_fehlende_datei_wirft_config_error(tmp_path):
    with pytest.raises(ConfigError, match="nicht gefunden"):
        load_packaging_catalog(tmp_path / "gibts_nicht.yaml")


def test_leere_datei_wirft_config_error(tmp_path):
    path = write_yaml(tmp_path, "")
    with pytest.raises(ConfigError, match="leer"):
        load_packaging_catalog(path)


def test_unvollständiger_eintrag_wirft_config_error(tmp_path):
    path = write_yaml(
        tmp_path,
        """
- id: kaputt
  typ: karton
""",
    )
    with pytest.raises(ConfigError, match="unvollständig"):
        load_packaging_catalog(path)


def test_karton_ohne_innenmasse_wirft_config_error(tmp_path):
    path = write_yaml(
        tmp_path,
        """
- id: mini
  typ: karton
  kosten_eur: 0.5
  max_zuladung_kg: 5
""",
    )
    with pytest.raises(ConfigError, match="innenmaße_mm"):
        load_packaging_catalog(path)

def test_gültiger_minimaler_karton_mit_innenmassen(tmp_path):
    path = write_yaml(
        tmp_path,
        """
- id: mini
  typ: karton
  kosten_eur: 0.5
  max_zuladung_kg: 5
  innenmaße_mm: {laenge: 100, breite: 80, hoehe: 60}
""",
    )
    katalog = load_packaging_catalog(path)
    assert len(katalog) == 1
    assert katalog[0].id == "mini"
    assert katalog[0].max_hoehe_mm == 60


def test_toleranz_wird_aus_config_gelesen(tmp_path):
    path = write_yaml(
        tmp_path,
        """
toleranz:
  absolut_mm: 3
  relativ_prozent: 2
verpackungen:
  - id: mini
    typ: karton
    kosten_eur: 0.5
    max_zuladung_kg: 5
    innenmaße_mm: {laenge: 100, breite: 80, hoehe: 60}
""",
    )
    config = load_config(path)
    assert config.toleranz.absolut_mm == 3
    assert config.toleranz.relativ_prozent == 2
    # Aufmaß: Maximum aus absolut und relativ
    assert config.toleranz.aufmass_mm(100) == 3      # 2% von 100 = 2 < 3
    assert config.toleranz.aufmass_mm(400) == 8      # 2% von 400 = 8 > 3


def test_toleranz_default_ohne_angabe():
    config = load_config(CATALOG_PATH)
    assert config.toleranz.absolut_mm == 2
    assert config.toleranz.relativ_prozent == 1


def test_negative_toleranz_wirft_config_error(tmp_path):
    path = write_yaml(
        tmp_path,
        """
toleranz:
  absolut_mm: -1
verpackungen:
  - id: mini
    typ: karton
    kosten_eur: 0.5
    max_zuladung_kg: 5
    innenmaße_mm: {laenge: 100, breite: 80, hoehe: 60}
""",
    )
    with pytest.raises(ConfigError, match="negativ"):
        load_config(path)
