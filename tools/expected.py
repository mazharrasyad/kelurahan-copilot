"""Ground truth for the demo questions, computed straight from both systems' data files.
Used to check that the agent's answers combine the two systems correctly."""
import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = json.load(open(os.path.join(ROOT, "systems", "sipos-posyandu", "data.json"), encoding="utf-8"))
D = json.load(open(os.path.join(ROOT, "systems", "si-dbd", "data.json"), encoding="utf-8"))
AT_RISK = {"gizi kurang", "gizi buruk", "stunting"}


def latest(bid):
    return max((p for p in S["penimbangan"] if p["balita_id"] == bid), key=lambda p: p["tanggal"])["status_gizi"]


risky = [b for b in S["balita"] if latest(b["id"]) in AT_RISK]
active = [k for k in D["kasus"] if k["status"] != "sembuh"]
active_nik = {k["nik"]: k for k in active}
name_to_code = {w["nama_kelurahan"].lower(): w["kode_kelurahan"] for w in D["wilayah"]}

print("Q1 at-risk toddlers whose mother is an ACTIVE dengue case:")
for b in risky:
    if b["nik_ibu"] in active_nik:
        k = active_nik[b["nik_ibu"]]
        print(f"  - {b['nama_balita']} (#{b['id']}, {latest(b['id'])}), mother {b['nama_ibu']} {b['nik_ibu']}: DBD {k['status']} since {k['tgl_onset']}")
print("  (mothers with ANY dengue case incl. recovered:",
      sorted({b['nama_ibu'] for b in risky if any(k['nik'] == b['nik_ibu'] for k in D['kasus'])}), ")")

print("Q2 villages with at-risk toddlers AND active dengue cases:")
rc = Counter(name_to_code[b["kelurahan"].lower()] for b in risky)
ac = Counter(k["kode_kelurahan"] for k in active)
for w in D["wilayah"]:
    c = w["kode_kelurahan"]
    if rc[c] and ac[c]:
        print(f"  - {w['nama_kelurahan']} ({c}): {rc[c]} at-risk toddlers, {ac[c]} active cases")

print("Q4 fogging schedule in villages with at-risk toddlers:")
for f in D["fogging"]:
    if rc[f["kode_kelurahan"]]:
        print(f"  - {f['kode_kelurahan']}: {f['tanggal']} {f['jam']} RW {', '.join(f['rw_sasaran'])}")
