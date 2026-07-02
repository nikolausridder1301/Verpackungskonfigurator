from pathlib import Path

import yaml

from app.models import Massangaben, Verpackung

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "packaging_catalog.yaml"


class ConfigError(Exception):
    pass


def _parse_entry(entry: dict) -> Verpackung:
    required = {"id", "typ", "kosten_eur", "max_zuladung_kg"}
    missing = required - entry.keys()
    if missing:
        raise ConfigError(f"Verpackungseintrag unvollständig, fehlende Felder: {missing} in {entry}")

    innenmasse = entry.get("innenmaße_mm")
    grundflaeche = entry.get("grundflaeche_mm")

    return Verpackung(
        id=entry["id"],
        typ=entry["typ"],
        kosten_eur=entry["kosten_eur"],
        max_zuladung_kg=entry["max_zuladung_kg"],
        innenmasse_mm=Massangaben(**innenmasse) if innenmasse else None,
        eigengewicht_kg=entry.get("eigengewicht_kg"),
        grundflaeche_mm=Massangaben(**grundflaeche) if grundflaeche else None,
        max_stapelhoehe_mm=entry.get("max_stapelhoehe_mm"),
    )


def load_packaging_catalog(path: Path = CATALOG_PATH) -> list[Verpackung]:
    if not path.exists():
        raise ConfigError(f"Config-Datei nicht gefunden: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not raw:
        raise ConfigError("Config-Datei ist leer")

    return [_parse_entry(entry) for entry in raw]
