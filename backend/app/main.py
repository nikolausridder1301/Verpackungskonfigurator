from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ConfigError, load_packaging_catalog

app = FastAPI(title="Verpackungskonfigurator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    packaging_catalog = load_packaging_catalog()
except ConfigError as exc:
    raise SystemExit(f"Fehler beim Laden der Verpackungs-Config: {exc}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/packaging-catalog")
def get_packaging_catalog():
    return packaging_catalog
