from pydantic import BaseModel


class Massangaben(BaseModel):
    laenge: float
    breite: float
    hoehe: float | None = None


class Verpackung(BaseModel):
    id: str
    typ: str  # "karton" oder "palette"
    kosten_eur: float
    max_zuladung_kg: float
    innenmasse_mm: Massangaben | None = None
    eigengewicht_kg: float | None = None
    grundflaeche_mm: Massangaben | None = None
    max_stapelhoehe_mm: float | None = None


class Artikel(BaseModel):
    artikel_id: str
    bezeichnung: str
    laenge_mm: float
    breite_mm: float
    hoehe_mm: float
    gewicht_kg: float
    menge: int
    zerbrechlich: bool = False
