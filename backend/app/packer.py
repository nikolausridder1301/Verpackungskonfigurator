"""Packalgorithmus: Greedy / First-Fit-Decreasing mit Lagenbildung (SPEC 5.2/5.3).

Unabhängig von FastAPI, damit die Logik ohne API testbar bleibt.

Harte Regeln (nie überschreitbar): max. Zuladungsgewicht, max. Stapel-/Innenhöhe.
Weiche Regeln (Verletzung -> Warnung im Ergebnis): Zerbrechlichkeit, Schwerpunkt.
"""

from dataclasses import dataclass, field
from itertools import permutations

from pydantic import BaseModel

from app.models import Artikel, Toleranz, Verpackung


class PackFehler(Exception):
    """Sendung kann nicht berechnet werden (z.B. Artikel passt nirgends hinein)."""

    def __init__(self, meldung: str):
        self.meldung = meldung
        super().__init__(meldung)


# ---------------------------------------------------------------------------
# Ergebnis-Modelle (identisch zur API-Response, SPEC/Issue #17)
# ---------------------------------------------------------------------------


class Platzierung(BaseModel):
    artikel_id: str
    bezeichnung: str
    x_mm: float
    y_mm: float
    z_mm: float
    laenge_mm: float  # Maße nach Rotation
    breite_mm: float
    hoehe_mm: float
    lage_index: int
    gewicht_kg: float
    zerbrechlich: bool


class Lage(BaseModel):
    index: int
    z_mm: float
    hoehe_mm: float


class Schwerpunkt(BaseModel):
    x_mm: float
    y_mm: float
    z_mm: float


class Packeinheit(BaseModel):
    verpackung_id: str
    typ: str
    nummer: int
    basis_laenge_mm: float
    basis_breite_mm: float
    max_hoehe_mm: float
    kosten_eur: float
    gewicht_kg: float  # Zuladung + Eigengewicht
    zuladung_kg: float
    auslastung_prozent: float
    schwerpunkt: Schwerpunkt
    lagen: list[Lage]
    platzierungen: list[Platzierung]
    warnungen: list[str]


class Packergebnis(BaseModel):
    einheiten: list[Packeinheit]
    anzahl_je_typ: dict[str, int]
    gesamtkosten_eur: float
    gesamtgewicht_kg: float
    warnungen: list[str]
    hinweise: list[str]
    stabil: bool


# ---------------------------------------------------------------------------
# Sortierung (Issues #6, #11, #12)
# ---------------------------------------------------------------------------


def sortiere_nach_volumen(artikel: list[Artikel]) -> list[Artikel]:
    """First-Fit-Decreasing-Basissortierung: Volumen absteigend (SPEC 5.2.1)."""
    return sorted(artikel, key=lambda a: -a.volumen_mm3)


@dataclass
class _Stueck:
    """Ein einzelnes Exemplar eines Artikels."""

    artikel: Artikel

    @property
    def gewicht(self) -> float:
        return self.artikel.gewicht_kg


def _stueckliste(artikel: list[Artikel]) -> list[_Stueck]:
    """Expandiert Mengen zu Einzelstücken in Packreihenfolge:
    nicht-zerbrechliche zuerst (zerbrechliche nach oben), darin schwere zuerst
    (schwere nach unten), darin Volumen absteigend (FFD)."""
    stuecke = [
        _Stueck(artikel=a)
        for a in sorted(artikel, key=lambda a: (a.zerbrechlich, -a.gewicht_kg, -a.volumen_mm3))
        for _ in range(a.menge)
    ]
    return stuecke


# ---------------------------------------------------------------------------
# Rotation (Issue #7) und Toleranz (Issue #13)
# ---------------------------------------------------------------------------


def rotationsvarianten(artikel: Artikel) -> list[tuple[float, float, float]]:
    """Alle bis zu 6 eindeutigen Orientierungen (laenge, breite, hoehe)."""
    return sorted(set(permutations((artikel.laenge_mm, artikel.breite_mm, artikel.hoehe_mm))))


def _mit_toleranz(masse: tuple[float, float, float], toleranz: Toleranz) -> tuple[float, float, float]:
    """Effektive (sichere) Maße: Nominalmaß + Toleranzaufmaß je Achse."""
    return tuple(m + toleranz.aufmass_mm(m) for m in masse)


def passt_in_verpackung(artikel: Artikel, verpackung: Verpackung, toleranz: Toleranz) -> bool:
    """Passt ein Einzelstück (irgendwie rotiert, inkl. Toleranz) in die leere Verpackung?"""
    if artikel.gewicht_kg > verpackung.max_zuladung_kg:
        return False
    L, B, H = verpackung.basis_laenge_mm, verpackung.basis_breite_mm, verpackung.max_hoehe_mm
    for variante in rotationsvarianten(artikel):
        l, b, h = _mit_toleranz(variante, toleranz)
        if l <= L and b <= B and h <= H:
            return True
    return False


# ---------------------------------------------------------------------------
# Platzierung: Lagen und Reihen (Issue #8)
# ---------------------------------------------------------------------------


@dataclass
class _Reihe:
    y_start: float
    x_cursor: float = 0.0
    tiefe: float = 0.0


@dataclass
class _LageZustand:
    index: int
    z_start: float
    hoehe: float = 0.0
    y_cursor: float = 0.0
    reihen: list[_Reihe] = field(default_factory=list)


@dataclass
class _EinheitZustand:
    verpackung: Verpackung
    lagen: list[_LageZustand] = field(default_factory=lambda: [_LageZustand(index=0, z_start=0.0)])
    platzierungen: list[Platzierung] = field(default_factory=list)
    zuladung_kg: float = 0.0

    @property
    def aktuelle_lage(self) -> _LageZustand:
        return self.lagen[-1]


def _orientierungen_geordnet(
    artikel: Artikel, toleranz: Toleranz
) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    """(nominal, effektiv)-Paare, flach liegende Orientierung zuerst
    (niedrige Höhe -> gleichmäßige, stabile Lagen)."""
    paare = []
    for nominal in rotationsvarianten(artikel):
        effektiv = _mit_toleranz(nominal, toleranz)
        paare.append((nominal, effektiv))
    paare.sort(key=lambda p: (p[1][2], p[1][1], p[1][0]))
    return paare


def _platziere_stueck(einheit: _EinheitZustand, stueck: _Stueck, toleranz: Toleranz) -> bool:
    """Versucht ein Einzelstück in der Einheit zu platzieren.
    Reihenfolge: aktuelle Reihe -> neue Reihe in aktueller Lage -> neue Lage.
    Gewichts- und Höhengrenzen sind harte Bedingungen (Issue #9)."""
    verpackung = einheit.verpackung
    artikel = stueck.artikel

    if einheit.zuladung_kg + artikel.gewicht_kg > verpackung.max_zuladung_kg:
        return False

    L, B, H = verpackung.basis_laenge_mm, verpackung.basis_breite_mm, verpackung.max_hoehe_mm
    lage = einheit.aktuelle_lage
    orientierungen = _orientierungen_geordnet(artikel, toleranz)

    def lege_ab(x: float, y: float, nominal: tuple[float, float, float]) -> None:
        einheit.platzierungen.append(
            Platzierung(
                artikel_id=artikel.artikel_id,
                bezeichnung=artikel.bezeichnung,
                x_mm=x,
                y_mm=y,
                z_mm=lage.z_start,
                laenge_mm=nominal[0],
                breite_mm=nominal[1],
                hoehe_mm=nominal[2],
                lage_index=lage.index,
                gewicht_kg=artikel.gewicht_kg,
                zerbrechlich=artikel.zerbrechlich,
            )
        )
        einheit.zuladung_kg += artikel.gewicht_kg

    def passt_zur_lagenhoehe(h_eff: float) -> bool:
        # Blockartige Lagen: In einer begonnenen Lage darf kein Artikel die
        # Lagenhöhe überragen (sonst entstehen instabile Mischlagen).
        return not lage.reihen or h_eff <= lage.hoehe

    # 1) In der aktuellen Reihe anlegen
    if lage.reihen:
        reihe = lage.reihen[-1]
        for nominal, (l_eff, b_eff, h_eff) in orientierungen:
            if lage.z_start + h_eff > H or not passt_zur_lagenhoehe(h_eff):
                continue
            if reihe.x_cursor + l_eff <= L and reihe.y_start + b_eff <= B:
                lege_ab(reihe.x_cursor, reihe.y_start, nominal)
                reihe.x_cursor += l_eff
                reihe.tiefe = max(reihe.tiefe, b_eff)
                lage.y_cursor = max(lage.y_cursor, reihe.y_start + reihe.tiefe)
                lage.hoehe = max(lage.hoehe, h_eff)
                return True

    # 2) Neue Reihe in der aktuellen Lage
    for nominal, (l_eff, b_eff, h_eff) in orientierungen:
        if lage.z_start + h_eff > H or not passt_zur_lagenhoehe(h_eff):
            continue
        if l_eff <= L and lage.y_cursor + b_eff <= B:
            reihe = _Reihe(y_start=lage.y_cursor, x_cursor=l_eff, tiefe=b_eff)
            lage.reihen.append(reihe)
            lege_ab(0.0, reihe.y_start, nominal)
            lage.y_cursor = reihe.y_start + b_eff
            lage.hoehe = max(lage.hoehe, h_eff)
            return True

    # 3) Neue Lage darüber beginnen (blockartig: erst wenn Lage voll ist)
    if lage.reihen:
        z_neu = lage.z_start + lage.hoehe
        for nominal, (l_eff, b_eff, h_eff) in orientierungen:
            if z_neu + h_eff > H:
                continue
            if l_eff <= L and b_eff <= B:
                neue_lage = _LageZustand(index=lage.index + 1, z_start=z_neu)
                einheit.lagen.append(neue_lage)
                reihe = _Reihe(y_start=0.0, x_cursor=l_eff, tiefe=b_eff)
                neue_lage.reihen.append(reihe)
                neue_lage.y_cursor = b_eff
                neue_lage.hoehe = h_eff
                lage = neue_lage
                lege_ab(0.0, 0.0, nominal)
                return True

    return False


# ---------------------------------------------------------------------------
# Prüfungen: Schwerpunkt (Issue #11) und Zerbrechlichkeit (Issue #12)
# ---------------------------------------------------------------------------


def _ueberlappen_xy(a: Platzierung, b: Platzierung) -> bool:
    return (
        a.x_mm < b.x_mm + b.laenge_mm
        and b.x_mm < a.x_mm + a.laenge_mm
        and a.y_mm < b.y_mm + b.breite_mm
        and b.y_mm < a.y_mm + a.breite_mm
    )


def berechne_schwerpunkt(platzierungen: list[Platzierung]) -> Schwerpunkt:
    gesamt = sum(p.gewicht_kg for p in platzierungen)
    if gesamt <= 0:
        return Schwerpunkt(x_mm=0, y_mm=0, z_mm=0)
    x = sum((p.x_mm + p.laenge_mm / 2) * p.gewicht_kg for p in platzierungen) / gesamt
    y = sum((p.y_mm + p.breite_mm / 2) * p.gewicht_kg for p in platzierungen) / gesamt
    z = sum((p.z_mm + p.hoehe_mm / 2) * p.gewicht_kg for p in platzierungen) / gesamt
    return Schwerpunkt(x_mm=round(x, 1), y_mm=round(y, 1), z_mm=round(z, 1))


def _pruefe_einheit(einheit: _EinheitZustand, nummer: int) -> list[str]:
    warnungen: list[str] = []
    name = f"{einheit.verpackung.id} Nr. {nummer}"

    # Schwerpunkt innerhalb der Grundfläche (harte SPEC-Anforderung, Warnung bei Verstoß)
    sp = berechne_schwerpunkt(einheit.platzierungen)
    if not (
        0 <= sp.x_mm <= einheit.verpackung.basis_laenge_mm
        and 0 <= sp.y_mm <= einheit.verpackung.basis_breite_mm
    ):
        warnungen.append(
            f"{name}: Der Schwerpunkt der Ladung liegt außerhalb der Grundfläche – "
            "Stabilität nicht garantiert, bitte manuell prüfen."
        )

    # Zerbrechliche Artikel: nichts Schwereres/Nicht-Zerbrechliches darüber
    for unten in einheit.platzierungen:
        if not unten.zerbrechlich:
            continue
        for oben in einheit.platzierungen:
            if oben.lage_index <= unten.lage_index or not _ueberlappen_xy(unten, oben):
                continue
            if not oben.zerbrechlich or oben.gewicht_kg > unten.gewicht_kg:
                warnungen.append(
                    f"{name}: Auf dem zerbrechlichen Artikel „{unten.artikel_id}“ "
                    f"liegt „{oben.artikel_id}“ – bitte manuell prüfen."
                )

    # Konflikt: zerbrechlicher Artikel liegt oben, ist aber schwerer als seine Unterlage
    for oben in einheit.platzierungen:
        if not oben.zerbrechlich or oben.lage_index == 0:
            continue
        traeger = [
            p
            for p in einheit.platzierungen
            if p.lage_index == oben.lage_index - 1 and _ueberlappen_xy(oben, p)
        ]
        if traeger and any(p.gewicht_kg < oben.gewicht_kg for p in traeger):
            warnungen.append(
                f"{name}: Der zerbrechliche Artikel „{oben.artikel_id}“ ist schwerer als "
                "die Artikel darunter (Konflikt schwer/zerbrechlich) – "
                "Stabilität nicht garantiert, bitte manuell prüfen."
            )
            break

    return list(dict.fromkeys(warnungen))


# ---------------------------------------------------------------------------
# Packen einer Sendung (Issues #6, #9, #16) und Kostenwahl (Issue #10)
# ---------------------------------------------------------------------------


def _packe_mit_typ(
    stuecke: list[_Stueck], verpackung: Verpackung, toleranz: Toleranz
) -> list[_EinheitZustand] | None:
    """First-Fit-Decreasing: jedes Stück in die erste offene Einheit, die es
    aufnehmen kann; sonst neue Einheit dieses Typs. None, wenn ein Stück
    grundsätzlich nicht in diesen Typ passt."""
    einheiten: list[_EinheitZustand] = []
    for stueck in stuecke:
        if not passt_in_verpackung(stueck.artikel, verpackung, toleranz):
            return None
        for einheit in einheiten:
            if _platziere_stueck(einheit, stueck, toleranz):
                break
        else:
            einheit = _EinheitZustand(verpackung=verpackung)
            einheiten.append(einheit)
            if not _platziere_stueck(einheit, stueck, toleranz):
                return None  # dürfte nach passt_in_verpackung nicht passieren
    return einheiten


def _packe_gemischt(
    stuecke: list[_Stueck], katalog: list[Verpackung], toleranz: Toleranz
) -> list[_EinheitZustand]:
    """Gemischte Strategie: erste passende offene Einheit, sonst neue Einheit
    des günstigsten Typs, in den das Stück passt."""
    nach_preis = sorted(katalog, key=lambda v: (v.kosten_eur, v.volumen_mm3))
    einheiten: list[_EinheitZustand] = []
    for stueck in stuecke:
        for einheit in einheiten:
            if _platziere_stueck(einheit, stueck, toleranz):
                break
        else:
            for verpackung in nach_preis:
                if passt_in_verpackung(stueck.artikel, verpackung, toleranz):
                    einheit = _EinheitZustand(verpackung=verpackung)
                    if _platziere_stueck(einheit, stueck, toleranz):
                        einheiten.append(einheit)
                        break
            else:
                raise PackFehler(
                    f"Artikel „{stueck.artikel.artikel_id}“ konnte keiner Verpackung "
                    "zugeordnet werden."
                )
    return einheiten


def _verbessere_letzte_einheit(
    einheiten: list[_EinheitZustand], katalog: list[Verpackung], toleranz: Toleranz
) -> list[_EinheitZustand]:
    """Issue #16: Restmenge der letzten Einheit in eine günstigere (kleinere)
    Verpackung umpacken, wenn sie dort komplett hineinpasst."""
    if not einheiten:
        return einheiten
    letzte = einheiten[-1]
    rest_stuecke = [_Stueck(artikel=_platzierung_zu_artikel(p)) for p in letzte.platzierungen]
    beste: _EinheitZustand | None = None
    for verpackung in katalog:
        if verpackung.kosten_eur >= letzte.verpackung.kosten_eur:
            continue
        kandidat = _EinheitZustand(verpackung=verpackung)
        if all(_platziere_stueck(kandidat, s, toleranz) for s in rest_stuecke):
            if beste is None or verpackung.kosten_eur < beste.verpackung.kosten_eur:
                beste = kandidat
    if beste is not None:
        return einheiten[:-1] + [beste]
    return einheiten


def _platzierung_zu_artikel(p: Platzierung) -> Artikel:
    return Artikel(
        artikel_id=p.artikel_id,
        bezeichnung=p.bezeichnung,
        laenge_mm=p.laenge_mm,
        breite_mm=p.breite_mm,
        hoehe_mm=p.hoehe_mm,
        gewicht_kg=p.gewicht_kg,
        menge=1,
        zerbrechlich=p.zerbrechlich,
    )


def _koste(einheiten: list[_EinheitZustand]) -> float:
    return sum(e.verpackung.kosten_eur for e in einheiten)


def _pruefe_alle_passen(artikel: list[Artikel], katalog: list[Verpackung], toleranz: Toleranz) -> None:
    """Issue #14: Artikel, der in keine Verpackung passt -> harter Abbruch."""
    groesste = max(katalog, key=lambda v: v.volumen_mm3)
    for a in artikel:
        if not any(passt_in_verpackung(a, v, toleranz) for v in katalog):
            masse = f"{a.laenge_mm:g} × {a.breite_mm:g} × {a.hoehe_mm:g} mm, {a.gewicht_kg:g} kg"
            g_masse = (
                f"{groesste.basis_laenge_mm:g} × {groesste.basis_breite_mm:g} × "
                f"{groesste.max_hoehe_mm:g} mm, max. {groesste.max_zuladung_kg:g} kg"
            )
            raise PackFehler(
                f"Der Artikel „{a.artikel_id}“ ({a.bezeichnung}, {masse}) passt in keine "
                f"verfügbare Verpackung. Größte verfügbare Verpackung: "
                f"„{groesste.id}“ ({g_masse}). Die Sendung wurde nicht berechnet."
            )


def berechne_packloesung(
    artikel: list[Artikel], katalog: list[Verpackung], toleranz: Toleranz
) -> Packergebnis:
    """Berechnet die kostengünstigste stabile Verpackungskombination.

    Wirft PackFehler, wenn ein Artikel in keine Verpackung passt (kein
    Teilergebnis). Liefert sonst immer ein Ergebnis – bei verletzten weichen
    Regeln als Best-Effort mit Warnungen (Issue #15).
    """
    if not artikel:
        raise PackFehler("Keine Artikel übergeben – es gibt nichts zu verpacken.")
    if not katalog:
        raise PackFehler("Es sind keine Verpackungen im Katalog hinterlegt.")

    _pruefe_alle_passen(artikel, katalog, toleranz)
    stuecke = _stueckliste(artikel)

    kandidaten: list[list[_EinheitZustand]] = []
    for verpackung in katalog:
        einheiten = _packe_mit_typ(stuecke, verpackung, toleranz)
        if einheiten is not None:
            kandidaten.append(_verbessere_letzte_einheit(einheiten, katalog, toleranz))
    kandidaten.append(_verbessere_letzte_einheit(_packe_gemischt(stuecke, katalog, toleranz), katalog, toleranz))

    # Günstigste Kombination; bei Kostengleichstand weniger Einheiten (Issue #10)
    beste = min(kandidaten, key=lambda e: (_koste(e), len(e)))

    return _als_ergebnis(beste)


def _als_ergebnis(einheiten: list[_EinheitZustand]) -> Packergebnis:
    ergebnis_einheiten: list[Packeinheit] = []
    alle_warnungen: list[str] = []
    hinweise: list[str] = []
    anzahl_je_typ: dict[str, int] = {}
    laufende_nummer: dict[str, int] = {}

    for einheit in einheiten:
        vp = einheit.verpackung
        anzahl_je_typ[vp.id] = anzahl_je_typ.get(vp.id, 0) + 1
        laufende_nummer[vp.id] = laufende_nummer.get(vp.id, 0) + 1
        nummer = laufende_nummer[vp.id]

        warnungen = _pruefe_einheit(einheit, nummer)
        alle_warnungen.extend(warnungen)

        volumen_artikel = sum(p.laenge_mm * p.breite_mm * p.hoehe_mm for p in einheit.platzierungen)
        auslastung = round(100 * volumen_artikel / vp.volumen_mm3, 1)

        ergebnis_einheiten.append(
            Packeinheit(
                verpackung_id=vp.id,
                typ=vp.typ,
                nummer=nummer,
                basis_laenge_mm=vp.basis_laenge_mm,
                basis_breite_mm=vp.basis_breite_mm,
                max_hoehe_mm=vp.max_hoehe_mm,
                kosten_eur=vp.kosten_eur,
                gewicht_kg=round(einheit.zuladung_kg + (vp.eigengewicht_kg or 0.0), 3),
                zuladung_kg=round(einheit.zuladung_kg, 3),
                auslastung_prozent=auslastung,
                schwerpunkt=berechne_schwerpunkt(einheit.platzierungen),
                lagen=[
                    Lage(index=lage.index, z_mm=lage.z_start, hoehe_mm=lage.hoehe)
                    for lage in einheit.lagen
                    if lage.reihen
                ],
                platzierungen=einheit.platzierungen,
                warnungen=warnungen,
            )
        )

    # Issue #16: Auslastung der letzten Einheit ausweisen, wenn sie kaum gefüllt ist
    if ergebnis_einheiten:
        letzte = ergebnis_einheiten[-1]
        if len(ergebnis_einheiten) > 1 and letzte.auslastung_prozent < 50:
            prozent = f"{letzte.auslastung_prozent:g}".replace(".", ",")
            hinweise.append(
                f"{letzte.verpackung_id} Nr. {letzte.nummer}: nur {prozent} % befüllt."
            )

    return Packergebnis(
        einheiten=ergebnis_einheiten,
        anzahl_je_typ=anzahl_je_typ,
        gesamtkosten_eur=round(sum(e.kosten_eur for e in ergebnis_einheiten), 2),
        gesamtgewicht_kg=round(sum(e.gewicht_kg for e in ergebnis_einheiten), 3),
        warnungen=alle_warnungen,
        hinweise=hinweise,
        stabil=not alle_warnungen,
    )
