from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import ConfigError, load_config
from app.models import Artikel
from app.packer import Packergebnis, PackFehler, berechne_packloesung
from app.parsing import UploadFehler, parse_sendung

# Harter Timeout für die Berechnung (SPEC 6.3 / Issue #18)
BERECHNUNGS_TIMEOUT_S = 30.0

app = FastAPI(title="Verpackungskonfigurator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    config = load_config()
except ConfigError as exc:
    raise SystemExit(f"Fehler beim Laden der Verpackungs-Config: {exc}")

_executor = ThreadPoolExecutor(max_workers=2)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/packaging-catalog")
def get_packaging_catalog():
    return config.verpackungen


class UploadAntwort(BaseModel):
    artikel: list[Artikel]
    warnungen: list[str]


@app.post("/upload", response_model=UploadAntwort)
async def upload_sendung(datei: UploadFile = File(...)):
    """Nimmt eine CSV/XLSX-Sendungsdatei entgegen und liefert die geparste,
    validierte Artikelliste zurück (Issues #4, #5)."""
    inhalt = await datei.read()
    try:
        ergebnis = parse_sendung(datei.filename or "upload", inhalt)
    except UploadFehler as exc:
        raise HTTPException(status_code=422, detail={"fehler": exc.fehler})
    return UploadAntwort(artikel=ergebnis.artikel, warnungen=ergebnis.warnungen)


class BerechnungsAnfrage(BaseModel):
    artikel: list[Artikel]


@app.post("/calculate", response_model=Packergebnis)
def calculate(anfrage: BerechnungsAnfrage):
    """Berechnet die vollständige Packlösung inkl. Positionsdaten (Issue #17).
    Bricht nach 30 Sekunden kontrolliert ab (Issue #18)."""
    if not anfrage.artikel:
        raise HTTPException(
            status_code=422,
            detail={"fehler": [{"zeile": None, "meldung": "Keine Artikel übergeben – bitte zuerst eine Sendungsdatei hochladen."}]},
        )
    future = _executor.submit(
        berechne_packloesung, anfrage.artikel, config.verpackungen, config.toleranz
    )
    try:
        return future.result(timeout=BERECHNUNGS_TIMEOUT_S)
    except FutureTimeoutError:
        future.cancel()
        raise HTTPException(
            status_code=504,
            detail={
                "meldung": (
                    "Die Berechnung wurde nach 30 Sekunden abgebrochen – "
                    "diese Sendung ist zu komplex für die aktuelle Version."
                )
            },
        )
    except PackFehler as exc:
        raise HTTPException(status_code=422, detail={"meldung": exc.meldung})
