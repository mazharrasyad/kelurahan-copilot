"""SI-DBD - legacy dengue (DBD) surveillance system (synthetic demo).

Run by the district health office: dengue cases are recorded per patient NIK and per
official village code (kode_kelurahan), plus weekly larva (jentik) inspections.
It shares no database with any other system. All data is synthetic.
"""
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from data import JENTIK, KASUS, WILAYAH

app = FastAPI(
    title="SI-DBD API",
    description="Dengue fever surveillance: cases by patient NIK and village code, larva inspections. Synthetic data.",
    version="1.0.0",
)


@app.get("/api/wilayah")
def list_wilayah():
    """List villages: official kode_kelurahan with village name, district and city."""
    return WILAYAH


@app.get("/api/kasus")
def list_kasus(kode_kelurahan: Optional[str] = Query(None, description="Official village code, e.g. 31.74.06.1002"),
               status: Optional[str] = Query(None, description="suspek, terkonfirmasi or sembuh"),
               aktif: bool = Query(False, description="Only active cases (suspek or terkonfirmasi)")):
    """List dengue cases with patient NIK, village code, onset date and status."""
    rows = KASUS
    if kode_kelurahan:
        rows = [r for r in rows if r["kode_kelurahan"] == kode_kelurahan]
    if status:
        rows = [r for r in rows if r["status"] == status]
    if aktif:
        rows = [r for r in rows if r["status"] != "sembuh"]
    return rows


@app.get("/api/kasus/nik/{nik}")
def get_kasus_by_nik(nik: str):
    """Look up dengue cases of one person by their 16-digit NIK (empty list if none)."""
    return [r for r in KASUS if r["nik"] == nik]


@app.get("/api/kasus/{kasus_id}")
def get_kasus(kasus_id: int):
    """Get one dengue case by id."""
    for r in KASUS:
        if r["id"] == kasus_id:
            return r
    raise HTTPException(404, "kasus not found")


@app.get("/api/jentik")
def list_jentik(kode_kelurahan: Optional[str] = Query(None, description="Official village code")):
    """Weekly larva inspections per village: houses checked, positive houses and larva-free index (ABJ %)."""
    return [r for r in JENTIK if not kode_kelurahan or r["kode_kelurahan"] == kode_kelurahan]


@app.get("/health")
def health():
    return {"ok": True, "system": "si-dbd"}
