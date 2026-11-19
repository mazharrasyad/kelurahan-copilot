"""SIPOS Posyandu - legacy health-post information system (synthetic, de-identified demo).

In the style of many Indonesian local-government apps: villages are stored as free-text
names and nutrition status comes from monthly weighings. Record-level routes exist for the
health-post staff; village-level recap routes (rekap) are what other agencies should use.
"""
from collections import defaultdict
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from data import BALITA, PENIMBANGAN, POSYANDU

app = FastAPI(
    title="SIPOS Posyandu API",
    description="Health-post (posyandu) records and village-level nutrition recaps. Synthetic, de-identified data.",
    version="1.0.0",
)

AT_RISK = ("gizi kurang", "gizi buruk", "stunting")


def _latest(month: Optional[str] = None) -> dict:
    """Latest weighing per toddler, optionally only up to a month (YYYY-MM)."""
    out = {}
    for p in sorted(PENIMBANGAN, key=lambda p: p["tanggal"]):
        if month and p["tanggal"][:7] > month:
            continue
        out[p["balita_id"]] = p
    return out


@app.get("/api/posyandu")
def list_posyandu():
    """List posyandu (health posts) with their village name (free text) and district."""
    return POSYANDU


@app.get("/api/rekap/gizi")
def rekap_gizi(bulan: Optional[str] = Query(None, description="Month YYYY-MM; default the latest")):
    """Village-level nutrition recap from the latest weighing: registered toddlers, counts per status and percent at risk."""
    latest = _latest(bulan)
    rows = defaultdict(lambda: {"terdaftar": 0, "ditimbang": 0, "normal": 0, "gizi kurang": 0, "gizi buruk": 0, "stunting": 0})
    for b in BALITA:
        r = rows[b["kelurahan"]]
        r["terdaftar"] += 1
        p = latest.get(b["id"])
        if p:
            r["ditimbang"] += 1
            r[p["status_gizi"]] += 1
    out = []
    for kel, r in sorted(rows.items()):
        berisiko = sum(r[s] for s in AT_RISK)
        out.append({"kelurahan": kel, **r, "berisiko": berisiko,
                    "persen_berisiko": round(100 * berisiko / r["ditimbang"], 1) if r["ditimbang"] else None})
    return out


@app.get("/api/rekap/gizi/tren")
def rekap_gizi_tren():
    """Monthly trend per village: number of toddlers weighed and number at risk in each month."""
    rows = defaultdict(lambda: defaultdict(lambda: {"ditimbang": 0, "berisiko": 0}))
    kel = {b["id"]: b["kelurahan"] for b in BALITA}
    for p in PENIMBANGAN:
        r = rows[kel[p["balita_id"]]][p["tanggal"][:7]]
        r["ditimbang"] += 1
        r["berisiko"] += p["status_gizi"] in AT_RISK
    return [{"kelurahan": k, "bulan": m, **v} for k in sorted(rows) for m, v in sorted(rows[k].items())]


@app.get("/api/rekap/penimbangan")
def rekap_penimbangan():
    """Posyandu attendance per month (D/S): toddlers weighed (D) out of registered (S), per health post."""
    reg = defaultdict(int)
    for b in BALITA:
        reg[b["posyandu_id"]] += 1
    pos_of = {b["id"]: b["posyandu_id"] for b in BALITA}
    came = defaultdict(int)
    for p in PENIMBANGAN:
        came[(pos_of[p["balita_id"]], p["tanggal"][:7])] += 1
    out = []
    for (pid, month), d in sorted(came.items()):
        pos = next(x for x in POSYANDU if x["id"] == pid)
        out.append({"posyandu": pos["nama_posyandu"], "kelurahan": pos["kelurahan"], "bulan": month,
                    "ditimbang_D": d, "terdaftar_S": reg[pid], "persen_DS": round(100 * d / reg[pid], 1)})
    return out


# --- Record-level routes for posyandu staff (de-identified ids). Not exposed to the agent. ---
@app.get("/api/balita")
def list_balita(kelurahan: Optional[str] = None):
    """Record-level list of registered toddlers (internal ids only)."""
    return [b for b in BALITA if not kelurahan or b["kelurahan"].lower() == kelurahan.lower()]


@app.get("/api/balita/{balita_id}/penimbangan")
def get_penimbangan(balita_id: str):
    """Weighing history of one toddler record."""
    rows = [p for p in PENIMBANGAN if p["balita_id"] == balita_id]
    if not rows:
        raise HTTPException(404, "balita not found")
    return rows


@app.get("/health")
def health():
    return {"ok": True, "system": "sipos-posyandu"}
