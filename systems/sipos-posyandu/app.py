"""SIPOS Posyandu - legacy health-post information system (synthetic demo).

A small "legacy" backend in the style of many Indonesian local-government apps:
toddlers (balita) are registered with their mother's national ID (nik_ibu), villages
are stored as free-text names, and nutrition status comes from monthly weighings.
All data is synthetic and generated deterministically at startup.
"""
from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from data import BALITA, PENIMBANGAN, POSYANDU, latest_status

app = FastAPI(
    title="SIPOS Posyandu API",
    description="Health-post (posyandu) records: toddlers, mothers' NIK and monthly weighings. Synthetic data.",
    version="1.0.0",
)

AT_RISK = {"gizi kurang", "gizi buruk", "stunting"}


def _with_status(b: dict) -> dict:
    s = latest_status(b["id"])
    return {**b, "status_gizi_terakhir": s["status_gizi"] if s else None, "tgl_timbang_terakhir": s["tanggal"] if s else None}


@app.get("/api/posyandu")
def list_posyandu():
    """List all posyandu (health posts) with their village name (free text) and district."""
    return POSYANDU


@app.get("/api/balita")
def list_balita(kelurahan: Optional[str] = Query(None, description="Village name, e.g. 'Pela Mampang'"),
                status_gizi: Optional[str] = Query(None, description="Latest nutrition status: normal, gizi kurang, gizi buruk, stunting")):
    """List registered toddlers with their mother's NIK, village and latest nutrition status."""
    rows = [_with_status(b) for b in BALITA]
    if kelurahan:
        rows = [r for r in rows if r["kelurahan"].lower() == kelurahan.lower()]
    if status_gizi:
        rows = [r for r in rows if (r["status_gizi_terakhir"] or "").lower() == status_gizi.lower()]
    return rows


@app.get("/api/balita-berisiko")
def list_balita_berisiko(kelurahan: Optional[str] = Query(None, description="Optional village name filter")):
    """List at-risk toddlers: latest weighing shows gizi kurang, gizi buruk or stunting."""
    rows = [_with_status(b) for b in BALITA]
    rows = [r for r in rows if r["status_gizi_terakhir"] in AT_RISK]
    if kelurahan:
        rows = [r for r in rows if r["kelurahan"].lower() == kelurahan.lower()]
    return rows


@app.get("/api/balita/{balita_id}")
def get_balita(balita_id: int):
    """Get one toddler by id, including mother's NIK and latest nutrition status."""
    for b in BALITA:
        if b["id"] == balita_id:
            return _with_status(b)
    raise HTTPException(404, "balita not found")


@app.get("/api/balita/{balita_id}/penimbangan")
def get_penimbangan(balita_id: int):
    """Monthly weighing history (weight kg, height cm, nutrition status) of one toddler."""
    if not any(b["id"] == balita_id for b in BALITA):
        raise HTTPException(404, "balita not found")
    return [p for p in PENIMBANGAN if p["balita_id"] == balita_id]


@app.get("/api/ibu/{nik_ibu}/balita")
def get_balita_by_ibu(nik_ibu: str):
    """List the toddlers registered under a mother's 16-digit NIK."""
    return [_with_status(b) for b in BALITA if b["nik_ibu"] == nik_ibu]


@app.get("/health")
def health():
    return {"ok": True, "system": "sipos-posyandu", "today": date.today().isoformat()}
