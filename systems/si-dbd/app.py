"""SI-DBD - legacy dengue (DBD) surveillance system (synthetic, de-identified demo).

Run by the district health office: cases are recorded per official village code
(kode_kelurahan), plus weekly larva (jentik) inspections. It shares no database with any
other system. Record-level routes exist for surveillance staff; recap routes are for others.
"""
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from fastapi import FastAPI, Query

from data import JENTIK, KASUS, WILAYAH

app = FastAPI(
    title="SI-DBD API",
    description="Dengue fever surveillance: village-level case recaps and larva inspections. Synthetic, de-identified data.",
    version="1.0.0",
)
REPORT_DATE = date(2026, 11, 19)


@app.get("/api/wilayah")
def list_wilayah():
    """List villages: official kode_kelurahan with village name, district and city."""
    return WILAYAH


@app.get("/api/rekap/kasus")
def rekap_kasus():
    """Dengue recap per village code: active cases (suspek + terkonfirmasi), confirmed, suspected, recovered, and new cases in the last 14 days."""
    since = (REPORT_DATE - timedelta(days=14)).isoformat()
    rows = defaultdict(lambda: {"aktif": 0, "terkonfirmasi": 0, "suspek": 0, "sembuh": 0, "baru_14_hari": 0})
    for w in WILAYAH:
        rows[w["kode_kelurahan"]]
    for k in KASUS:
        r = rows[k["kode_kelurahan"]]
        r[k["status"]] += 1
        r["aktif"] += k["status"] != "sembuh"
        r["baru_14_hari"] += k["tgl_onset"] >= since
    return [{"kode_kelurahan": c, **v, "per_tanggal": REPORT_DATE.isoformat()} for c, v in sorted(rows.items())]


@app.get("/api/rekap/kasus/mingguan")
def rekap_kasus_mingguan():
    """Weekly new dengue cases per village code (week starting Monday), by onset date."""
    rows = defaultdict(int)
    for k in KASUS:
        d = date.fromisoformat(k["tgl_onset"])
        rows[(k["kode_kelurahan"], (d - timedelta(days=d.weekday())).isoformat())] += 1
    return [{"kode_kelurahan": c, "minggu_mulai": w, "kasus_baru": n} for (c, w), n in sorted(rows.items())]


@app.get("/api/jentik")
def list_jentik(kode_kelurahan: Optional[str] = Query(None, description="Official village code")):
    """Weekly larva inspections per village: houses checked, houses with larvae and larva-free index (ABJ %, target >= 95)."""
    return [r for r in JENTIK if not kode_kelurahan or r["kode_kelurahan"] == kode_kelurahan]


# --- Record-level route for surveillance staff (de-identified ids). Not exposed to the agent. ---
@app.get("/api/kasus")
def list_kasus(kode_kelurahan: Optional[str] = None):
    """Record-level dengue case list (internal ids only)."""
    return [k for k in KASUS if not kode_kelurahan or k["kode_kelurahan"] == kode_kelurahan]


@app.get("/health")
def health():
    return {"ok": True, "system": "si-dbd"}
