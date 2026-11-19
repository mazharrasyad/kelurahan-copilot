"""Loads SIPOS Posyandu's own synthetic records (data.json)."""
import json
import os

_D = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json"), encoding="utf-8"))
POSYANDU = _D["posyandu"]
BALITA = _D["balita"]
PENIMBANGAN = _D["penimbangan"]


def latest_status(balita_id: int):
    rows = [p for p in PENIMBANGAN if p["balita_id"] == balita_id]
    return max(rows, key=lambda p: p["tanggal"]) if rows else None
