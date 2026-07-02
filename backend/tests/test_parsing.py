import io

import openpyxl
import pytest

from app.parsing import UploadFehler, parse_sendung

KOPF = "artikel_id,bezeichnung,laenge_mm,breite_mm,hoehe_mm,gewicht_kg,menge,zerbrechlich"


def csv_bytes(*zeilen: str) -> bytes:
    return "\n".join([KOPF, *zeilen]).encode("utf-8")


def test_gueltige_csv_wird_geparst():
    ergebnis = parse_sendung(
        "sendung.csv",
        csv_bytes("A-1,Koffer,150,100,80,1.5,12,nein", "B-2,Box,90,70,45,0.8,24,ja"),
    )
    assert len(ergebnis.artikel) == 2
    a = ergebnis.artikel[0]
    assert a.artikel_id == "A-1"
    assert a.laenge_mm == 150
    assert a.menge == 12
    assert a.zerbrechlich is False
    assert ergebnis.artikel[1].zerbrechlich is True
    assert ergebnis.warnungen == []


def test_semikolon_csv_und_dezimalkomma():
    inhalt = (
        "artikel_id;bezeichnung;laenge_mm;breite_mm;hoehe_mm;gewicht_kg;menge\n"
        "A-1;Koffer;150;100;80;1,5;12\n"
    ).encode("utf-8")
    ergebnis = parse_sendung("sendung.csv", inhalt)
    assert ergebnis.artikel[0].gewicht_kg == 1.5


def test_xlsx_wird_geparst():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(KOPF.split(","))
    ws.append(["A-1", "Koffer", 150, 100, 80, 1.5, 12, "ja"])
    buffer = io.BytesIO()
    wb.save(buffer)
    ergebnis = parse_sendung("sendung.xlsx", buffer.getvalue())
    assert len(ergebnis.artikel) == 1
    assert ergebnis.artikel[0].menge == 12
    assert ergebnis.artikel[0].zerbrechlich is True


def test_unbekanntes_format_wird_abgelehnt():
    with pytest.raises(UploadFehler) as exc:
        parse_sendung("sendung.pdf", b"egal")
    assert "nicht unterstützt" in exc.value.fehler[0]["meldung"]


def test_fehlende_spalte_wird_benannt():
    inhalt = "artikel_id,bezeichnung,laenge_mm\nA-1,Koffer,150\n".encode("utf-8")
    with pytest.raises(UploadFehler) as exc:
        parse_sendung("sendung.csv", inhalt)
    assert "breite_mm" in exc.value.fehler[0]["meldung"]


def test_fehlendes_gewicht_ist_zeilenbezogen():
    with pytest.raises(UploadFehler) as exc:
        parse_sendung(
            "sendung.csv",
            csv_bytes("A-1,Koffer,150,100,80,1.5,12,nein", "B-2,Box,90,70,45,,24,nein"),
        )
    meldungen = [f["meldung"] for f in exc.value.fehler]
    assert any("Zeile 3" in m and "Gewicht" in m for m in meldungen)
    assert exc.value.fehler[0]["zeile"] == 3


def test_null_und_negative_werte_werden_abgelehnt():
    with pytest.raises(UploadFehler) as exc:
        parse_sendung(
            "sendung.csv",
            csv_bytes("A-1,Koffer,0,100,80,1.5,12,nein", "B-2,Box,90,70,45,-2,24,nein"),
        )
    meldungen = " | ".join(f["meldung"] for f in exc.value.fehler)
    assert "Zeile 2" in meldungen and "größer als 0" in meldungen
    assert "Zeile 3" in meldungen


def test_doppelte_artikel_id_fasst_mengen_zusammen():
    ergebnis = parse_sendung(
        "sendung.csv",
        csv_bytes("A-1,Koffer,150,100,80,1.5,12,nein", "A-1,Koffer,150,100,80,1.5,5,nein"),
    )
    assert len(ergebnis.artikel) == 1
    assert ergebnis.artikel[0].menge == 17
    assert any("mehrfach" in w for w in ergebnis.warnungen)


def test_leere_datei_meldet_keine_artikel():
    with pytest.raises(UploadFehler) as exc:
        parse_sendung("sendung.csv", (KOPF + "\n").encode("utf-8"))
    assert "Keine Artikel gefunden" in exc.value.fehler[0]["meldung"]


def test_menge_muss_ganzzahl_sein():
    with pytest.raises(UploadFehler) as exc:
        parse_sendung("sendung.csv", csv_bytes("A-1,Koffer,150,100,80,1.5,2.5,nein"))
    assert "ganze Zahl" in exc.value.fehler[0]["meldung"]


def test_ungueltiger_zerbrechlich_wert():
    with pytest.raises(UploadFehler) as exc:
        parse_sendung("sendung.csv", csv_bytes("A-1,Koffer,150,100,80,1.5,2,vielleicht"))
    assert "zerbrechlich" in exc.value.fehler[0]["meldung"]
