import time

import pytest

from app.config import load_config, CATALOG_PATH
from app.models import Artikel, Massangaben, Toleranz, Verpackung
from app.packer import (
    PackFehler,
    _packe_mit_typ,
    _stueckliste,
    berechne_packloesung,
    passt_in_verpackung,
    rotationsvarianten,
    sortiere_nach_volumen,
)

CONFIG = load_config(CATALOG_PATH)
KATALOG = CONFIG.verpackungen
TOLERANZ = CONFIG.toleranz


def artikel(**overrides) -> Artikel:
    daten = {
        "artikel_id": "A-1",
        "bezeichnung": "Testartikel",
        "laenge_mm": 90,
        "breite_mm": 70,
        "hoehe_mm": 45,
        "gewicht_kg": 1.0,
        "menge": 1,
    }
    daten.update(overrides)
    return Artikel(**daten)


def karton(id="box", laenge=200, breite=150, hoehe=100, zuladung=15, kosten=1.20) -> Verpackung:
    return Verpackung(
        id=id,
        typ="karton",
        kosten_eur=kosten,
        max_zuladung_kg=zuladung,
        innenmasse_mm=Massangaben(laenge=laenge, breite=breite, hoehe=hoehe),
    )


# --- Issue #6: Sortierung und First-Fit-Decreasing ---


def test_sortierung_nach_volumen_absteigend():
    a_klein = artikel(artikel_id="klein", laenge_mm=10, breite_mm=10, hoehe_mm=10)
    a_gross = artikel(artikel_id="gross", laenge_mm=100, breite_mm=100, hoehe_mm=100)
    a_mittel = artikel(artikel_id="mittel", laenge_mm=50, breite_mm=50, hoehe_mm=50)
    sortiert = sortiere_nach_volumen([a_klein, a_gross, a_mittel])
    assert [a.artikel_id for a in sortiert] == ["gross", "mittel", "klein"]


def test_einfaches_szenario_ein_artikeltyp_ein_verpackungstyp():
    # 8 Stück 90x70x45 passen exakt in einen karton_s (2x2 pro Lage, 2 Lagen)
    ergebnis = berechne_packloesung([artikel(menge=8)], KATALOG, TOLERANZ)
    assert len(ergebnis.einheiten) == 1
    einheit = ergebnis.einheiten[0]
    assert einheit.verpackung_id == "karton_s"
    assert len(einheit.platzierungen) == 8
    assert len(einheit.lagen) == 2
    assert ergebnis.gesamtkosten_eur == pytest.approx(1.20)
    # Alle Positionen liegen innerhalb der Verpackung
    for p in einheit.platzierungen:
        assert 0 <= p.x_mm and p.x_mm + p.laenge_mm <= einheit.basis_laenge_mm
        assert 0 <= p.y_mm and p.y_mm + p.breite_mm <= einheit.basis_breite_mm
        assert 0 <= p.z_mm and p.z_mm + p.hoehe_mm <= einheit.max_hoehe_mm


# --- Issue #7: Rotation ---


def test_rotationsvarianten_sind_alle_sechs():
    a = artikel(laenge_mm=10, breite_mm=20, hoehe_mm=30)
    assert len(rotationsvarianten(a)) == 6
    wuerfel = artikel(laenge_mm=10, breite_mm=10, hoehe_mm=10)
    assert len(rotationsvarianten(wuerfel)) == 1


def test_artikel_passt_nur_rotiert():
    # 90x190x140: in Anlieferungsorientierung zu breit/hoch für karton_s,
    # rotiert (190 entlang der Länge, 90 nach oben) passt er.
    a = artikel(laenge_mm=90, breite_mm=190, hoehe_mm=140)
    karton_s = next(v for v in KATALOG if v.id == "karton_s")
    assert passt_in_verpackung(a, karton_s, TOLERANZ)

    ergebnis = berechne_packloesung([a], KATALOG, TOLERANZ)
    platzierung = ergebnis.einheiten[0].platzierungen[0]
    assert platzierung.hoehe_mm == 90
    assert {platzierung.laenge_mm, platzierung.breite_mm} == {190, 140}


# --- Issue #8: Lagenbildung ---


def test_mehrlagiges_szenario_hat_positionsdaten():
    ergebnis = berechne_packloesung([artikel(menge=8)], KATALOG, TOLERANZ)
    einheit = ergebnis.einheiten[0]
    lagen_indizes = {p.lage_index for p in einheit.platzierungen}
    assert lagen_indizes == {0, 1}
    # untere Lage beginnt bei z=0, obere darüber
    z_werte = {p.lage_index: p.z_mm for p in einheit.platzierungen}
    assert z_werte[0] == 0
    assert z_werte[1] > 0


# --- Issue #9: Harte Grenzen ---


def test_zuladungsgrenze_wird_nie_ueberschritten():
    # 3 Stück à 6 kg: karton_s trägt max. 15 kg -> höchstens 2 pro Karton
    stuecke = _stueckliste([artikel(laenge_mm=60, breite_mm=60, hoehe_mm=60, gewicht_kg=6, menge=3)])
    karton_s = next(v for v in KATALOG if v.id == "karton_s")
    einheiten = _packe_mit_typ(stuecke, karton_s, TOLERANZ)
    assert len(einheiten) == 2
    for e in einheiten:
        assert e.zuladung_kg <= karton_s.max_zuladung_kg


def test_stapelhoehe_wird_nie_ueberschritten():
    # 150x100x60: nur 1 Stück pro Lage und nur 1 Lage im karton_s (2x62mm > 100mm)
    stuecke = _stueckliste([artikel(laenge_mm=150, breite_mm=100, hoehe_mm=60, menge=3)])
    karton_s = next(v for v in KATALOG if v.id == "karton_s")
    einheiten = _packe_mit_typ(stuecke, karton_s, TOLERANZ)
    assert len(einheiten) == 3
    for e in einheiten:
        for p in e.platzierungen:
            assert p.z_mm + p.hoehe_mm <= karton_s.max_hoehe_mm


def test_gesamtloesung_haelt_grenzen_ein():
    sendung = [
        artikel(artikel_id="schwer", gewicht_kg=6, menge=10),
        artikel(artikel_id="leicht", menge=20),
    ]
    ergebnis = berechne_packloesung(sendung, KATALOG, TOLERANZ)
    katalog_map = {v.id: v for v in KATALOG}
    for e in ergebnis.einheiten:
        vp = katalog_map[e.verpackung_id]
        assert e.zuladung_kg <= vp.max_zuladung_kg
        for p in e.platzierungen:
            assert p.z_mm + p.hoehe_mm <= vp.max_hoehe_mm + 1e-9


# --- Issue #10: Kostenoptimierung ---


def test_guenstigste_kombination_wird_gewaehlt():
    # 8 kleine Artikel: 1x karton_s (1.20) schlägt 1x karton_m (2.10) und Palette (8.00)
    ergebnis = berechne_packloesung([artikel(menge=8)], KATALOG, TOLERANZ)
    vergleich_karton_m = 2.10
    vergleich_palette = 8.00
    assert ergebnis.gesamtkosten_eur <= vergleich_karton_m
    assert ergebnis.gesamtkosten_eur <= vergleich_palette
    assert ergebnis.anzahl_je_typ == {"karton_s": 1}


def test_kostengleichstand_bevorzugt_weniger_einheiten():
    klein = karton(id="einzeln", laenge=110, breite=110, hoehe=110, kosten=1.00)
    doppelt = karton(id="doppelt", laenge=210, breite=110, hoehe=110, kosten=2.00)
    a = artikel(laenge_mm=100, breite_mm=100, hoehe_mm=100, menge=2)
    ergebnis = berechne_packloesung([a], [klein, doppelt], TOLERANZ)
    assert ergebnis.gesamtkosten_eur == pytest.approx(2.00)
    assert len(ergebnis.einheiten) == 1
    assert ergebnis.einheiten[0].verpackung_id == "doppelt"


# --- Issue #11: Schwerpunkt und schwere Artikel unten ---


def test_schwere_artikel_liegen_unten_und_schwerpunkt_in_grundflaeche():
    sendung = [
        artikel(artikel_id="schwer", gewicht_kg=3.0, menge=4),
        artikel(artikel_id="leicht", gewicht_kg=0.5, menge=4),
    ]
    # Nur ein Verpackungstyp mit 4 Plätzen pro Lage -> zwei Lagen erzwungen
    ergebnis = berechne_packloesung(sendung, [karton()], TOLERANZ)
    einheit = ergebnis.einheiten[0]
    for p in einheit.platzierungen:
        if p.artikel_id == "schwer":
            assert p.lage_index == 0
        else:
            assert p.lage_index == 1
    sp = einheit.schwerpunkt
    assert 0 <= sp.x_mm <= einheit.basis_laenge_mm
    assert 0 <= sp.y_mm <= einheit.basis_breite_mm
    assert ergebnis.stabil is True


# --- Issue #12: Zerbrechlichkeit ---


def test_zerbrechliche_artikel_kommen_nach_oben_ohne_warnung():
    sendung = [
        artikel(artikel_id="robust", gewicht_kg=1.0, menge=4),
        artikel(artikel_id="glas", gewicht_kg=0.5, menge=4, zerbrechlich=True),
    ]
    ergebnis = berechne_packloesung(sendung, KATALOG, TOLERANZ)
    einheit = ergebnis.einheiten[0]
    for p in einheit.platzierungen:
        if p.zerbrechlich:
            assert p.lage_index == 1
    assert ergebnis.warnungen == []
    assert ergebnis.stabil is True


def test_konflikt_zerbrechlich_und_schwer_erzeugt_warnung():
    sendung = [
        artikel(artikel_id="leicht", gewicht_kg=0.5, menge=4),
        artikel(artikel_id="glas-schwer", gewicht_kg=3.0, menge=4, zerbrechlich=True),
    ]
    ergebnis = berechne_packloesung(sendung, KATALOG, TOLERANZ)
    assert ergebnis.stabil is False
    assert any("zerbrechliche" in w.lower() or "zerbrechlich" in w.lower() for w in ergebnis.warnungen)
    # Best-Effort: Ergebnis wird trotzdem geliefert (Issue #15)
    assert sum(len(e.platzierungen) for e in ergebnis.einheiten) == 8


# --- Issue #13/#37: Toleranz ---


def test_artikel_exakt_an_der_toleranzgrenze_passt():
    # 198mm + Aufmaß max(2mm, 1%) = 200mm -> passt exakt in karton_s (200mm)
    karton_s = next(v for v in KATALOG if v.id == "karton_s")
    innerhalb = artikel(laenge_mm=198, breite_mm=146, hoehe_mm=96)
    assert passt_in_verpackung(innerhalb, karton_s, TOLERANZ)


def test_artikel_knapp_ueber_der_toleranzgrenze_passt_nicht():
    # 198.5mm + 2mm = 200.5mm > 200mm -> passt in keiner Rotation
    karton_s = next(v for v in KATALOG if v.id == "karton_s")
    ausserhalb = artikel(laenge_mm=198.5, breite_mm=146, hoehe_mm=96)
    assert not passt_in_verpackung(ausserhalb, karton_s, TOLERANZ)


def test_toleranz_ist_konfigurierbar():
    karton_s = next(v for v in KATALOG if v.id == "karton_s")
    grenzfall = artikel(laenge_mm=198.5, breite_mm=146, hoehe_mm=96)
    assert not passt_in_verpackung(grenzfall, karton_s, Toleranz(absolut_mm=2, relativ_prozent=1))
    assert passt_in_verpackung(grenzfall, karton_s, Toleranz(absolut_mm=1, relativ_prozent=0))


# --- Issue #14: Artikel zu groß ---


def test_artikel_groesser_als_jede_verpackung_bricht_ab():
    riese = artikel(artikel_id="riese", laenge_mm=1300, breite_mm=900, hoehe_mm=1900, gewicht_kg=40)
    with pytest.raises(PackFehler) as exc:
        berechne_packloesung([riese, artikel(artikel_id="klein")], KATALOG, TOLERANZ)
    assert "riese" in exc.value.meldung
    assert "euro_palette" in exc.value.meldung
    assert "nicht berechnet" in exc.value.meldung


def test_artikel_zu_schwer_fuer_jede_verpackung_bricht_ab():
    brocken = artikel(artikel_id="brocken", laenge_mm=100, breite_mm=100, hoehe_mm=100, gewicht_kg=600)
    with pytest.raises(PackFehler):
        berechne_packloesung([brocken], KATALOG, TOLERANZ)


# --- Issue #16: Restmengen ---


def test_restmenge_kommt_in_guenstigere_zusatzverpackung():
    # 13 Stück: 12 füllen einen karton_m, das 13. wandert in einen karton_s
    a = artikel(laenge_mm=150, breite_mm=100, hoehe_mm=80, menge=13)
    ergebnis = berechne_packloesung([a], KATALOG, TOLERANZ)
    assert ergebnis.anzahl_je_typ == {"karton_m": 1, "karton_s": 1}
    assert ergebnis.gesamtkosten_eur == pytest.approx(3.30)
    letzte = ergebnis.einheiten[-1]
    assert letzte.verpackung_id == "karton_s"
    assert letzte.auslastung_prozent < 50
    assert any("befüllt" in h for h in ergebnis.hinweise)


# --- Issue #30: Performance ---


def test_hundert_artikel_unter_zehn_sekunden():
    sendung = [
        artikel(artikel_id="T1", laenge_mm=90, breite_mm=70, hoehe_mm=45, gewicht_kg=0.5, menge=33),
        artikel(artikel_id="T2", laenge_mm=60, breite_mm=60, hoehe_mm=60, gewicht_kg=0.4, menge=33),
        artikel(artikel_id="T3", laenge_mm=120, breite_mm=80, hoehe_mm=50, gewicht_kg=0.8, menge=34),
    ]
    start = time.monotonic()
    ergebnis = berechne_packloesung(sendung, KATALOG, TOLERANZ)
    dauer = time.monotonic() - start
    print(f"\nPerformance: 100 Artikel in {dauer:.3f}s gepackt")
    assert dauer < 10.0
    assert sum(len(e.platzierungen) for e in ergebnis.einheiten) == 100
