from pydantic import BaseModel


class Toleranz(BaseModel):
    """Globale Fertigungstoleranz (SPEC 5.3): Artikel können real bis zu
    diesem Aufmaß größer sein als angegeben. Die Platzierung rechnet daher
    mit Artikelmaß + Toleranz (sichere Seite)."""

    absolut_mm: float = 2.0
    relativ_prozent: float = 1.0

    def aufmass_mm(self, mass_mm: float) -> float:
        """Effektives Aufmaß für ein Einzelmaß: das Größere aus absolutem
        und relativem Toleranzwert."""
        return max(self.absolut_mm, mass_mm * self.relativ_prozent / 100.0)


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

    @property
    def basis_laenge_mm(self) -> float:
        """Nutzbare Grundfläche: Länge."""
        masse = self.innenmasse_mm or self.grundflaeche_mm
        assert masse is not None
        return masse.laenge

    @property
    def basis_breite_mm(self) -> float:
        """Nutzbare Grundfläche: Breite."""
        masse = self.innenmasse_mm or self.grundflaeche_mm
        assert masse is not None
        return masse.breite

    @property
    def max_hoehe_mm(self) -> float:
        """Nutzbare Höhe: Karton-Innenhöhe bzw. maximale Stapelhöhe der Palette."""
        if self.innenmasse_mm is not None and self.innenmasse_mm.hoehe is not None:
            return self.innenmasse_mm.hoehe
        assert self.max_stapelhoehe_mm is not None
        return self.max_stapelhoehe_mm

    @property
    def volumen_mm3(self) -> float:
        return self.basis_laenge_mm * self.basis_breite_mm * self.max_hoehe_mm


class Artikel(BaseModel):
    artikel_id: str
    bezeichnung: str
    laenge_mm: float
    breite_mm: float
    hoehe_mm: float
    gewicht_kg: float
    menge: int
    zerbrechlich: bool = False

    @property
    def volumen_mm3(self) -> float:
        return self.laenge_mm * self.breite_mm * self.hoehe_mm
