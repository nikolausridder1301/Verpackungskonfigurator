from pathlib import Path

import yaml
from pydantic import BaseModel

from app.models import Massangaben, Toleranz, Verpackung

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "packaging_catalog.yaml"


class ConfigError(Exception):
    pass


class AppConfig(BaseModel):
    verpackungen: list[Verpackung]
    toleranz: Toleranz


def _parse_entry(entry: dict) -> Verpackung:
    required = {"id", "typ", "kosten_eur", "max_zuladung_kg"}
    missing = required - entry.keys()
    if missing:
        raise ConfigError(f"Verpackungseintrag unvollständig, fehlende Felder: {missing} in {entry}")

    innenmasse = entry.get("innenmaße_mm")
    grundflaeche = entry.get("grundflaeche_mm")

    typ = entry["typ"]
    if typ == "karton":
        if not innenmasse or innenmasse.get("hoehe") is None:
            raise ConfigError(
                f"Karton '{entry['id']}': innenmaße_mm mit laenge/breite/hoehe erforderlich"
            )
    elif typ == "palette":
        if not grundflaeche:
            raise ConfigError(f"Palette '{entry['id']}': grundflaeche_mm erforderlich")
        if entry.get("max_stapelhoehe_mm") is None:
            raise ConfigError(f"Palette '{entry['id']}': max_stapelhoehe_mm erforderlich")
    else:
        raise ConfigError(f"Unbekannter Verpackungstyp '{typ}' in Eintrag '{entry['id']}'")

    return Verpackung(
        id=entry["id"],
        typ=typ,
        kosten_eur=entry["kosten_eur"],
        max_zuladung_kg=entry["max_zuladung_kg"],
        innenmasse_mm=Massangaben(**innenmasse) if innenmasse else None,
        eigengewicht_kg=entry.get("eigengewicht_kg"),
        grundflaeche_mm=Massangaben(**grundflaeche) if grundflaeche else None,
        max_stapelhoehe_mm=entry.get("max_stapelhoehe_mm"),
    )


def _parse_toleranz(raw: dict | None) -> Toleranz:
    if not raw:
        return Toleranz()
    try:
        toleranz = Toleranz(**raw)
    except Exception as exc:
        raise ConfigError(f"Toleranz-Angaben ungültig: {exc}")
    if toleranz.absolut_mm < 0 or toleranz.relativ_prozent < 0:
        raise ConfigError("Toleranzwerte dürfen nicht negativ sein")
    return toleranz


def load_config(path: Path = CATALOG_PATH) -> AppConfig:
    """Lädt Verpackungskatalog und Toleranz. Unterstützt das neue Format
    (Mapping mit 'verpackungen' und 'toleranz') sowie das alte reine
    Listenformat (dann gilt die Standard-Toleranz)."""
    if not path.exists():
        raise ConfigError(f"Config-Datei nicht gefunden: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not raw:
        raise ConfigError("Config-Datei ist leer")

    if isinstance(raw, dict):
        eintraege = raw.get("verpackungen")
        if not eintraege:
            raise ConfigError("Config-Datei enthält keine 'verpackungen'-Einträge")
        toleranz = _parse_toleranz(raw.get("toleranz"))
    else:
        eintraege = raw
        toleranz = Toleranz()

    return AppConfig(verpackungen=[_parse_entry(e) for e in eintraege], toleranz=toleranz)


def load_packaging_catalog(path: Path = CATALOG_PATH) -> list[Verpackung]:
    return load_config(path).verpackungen
