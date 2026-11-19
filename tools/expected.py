"""Ground truth for the demo questions, computed through each system's own recap code.
Used to check that the agent's answers combine the two systems correctly."""
import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(system):
    folder = os.path.join(ROOT, "systems", system)
    cwd = os.getcwd()
    os.chdir(folder)
    import sys
    sys.path.insert(0, folder)
    for m in ("data", "app"):
        sys.modules.pop(m, None)
    spec = importlib.util.spec_from_file_location(f"{system}_app", os.path.join(folder, "app.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.path.remove(folder)
    os.chdir(cwd)
    return mod


sipos, sidbd = load("sipos-posyandu"), load("si-dbd")
gizi = {r["kelurahan"].lower(): r for r in sipos.rekap_gizi(None)}
kasus = {r["kode_kelurahan"]: r for r in sidbd.rekap_kasus()}
wil = sidbd.list_wilayah()
abj = {}
for j in sorted(sidbd.list_jentik(None), key=lambda j: j["tgl_periksa"]):
    abj[j["kode_kelurahan"]] = j["abj_persen"]

print("Per village (SIPOS name -> SI-DBD code):")
rows = []
for w in wil:
    g, k = gizi[w["nama_kelurahan"].lower()], kasus[w["kode_kelurahan"]]
    rows.append((w, g, k))
    print(f"  {w['nama_kelurahan']:17} {w['kode_kelurahan']}  at-risk {g['berisiko']:2}/{g['ditimbang']:2} ({g['persen_berisiko']:4}%)  "
          f"active DBD {k['aktif']:2} (new 14d {k['baru_14_hari']})  ABJ {abj[w['kode_kelurahan']]}%")

print("Q1 priority (both signals high):", [w["nama_kelurahan"] for w, g, k in sorted(rows, key=lambda r: -(r[1]["persen_berisiko"] / 100 + r[2]["aktif"] / 10))][:3])
print("Q2 ABJ < 95%:", [(w["nama_kelurahan"], g["berisiko"], k["aktif"]) for w, g, k in rows if abj[w["kode_kelurahan"]] < 95])
print("Q3 Tegal Parang trend:", [(r["bulan"], r["berisiko"]) for r in sipos.rekap_gizi_tren() if r["kelurahan"] == "Tegal Parang"],
      [(r["minggu_mulai"], r["kasus_baru"]) for r in sidbd.rekap_kasus_mingguan() if r["kode_kelurahan"] == "31.74.06.1004"])
import json
fog = json.load(open(os.path.join(ROOT, "systems", "si-dbd", "data.json"), encoding="utf-8"))["fogging"]
print("Q4 fogging:", [(f["kode_kelurahan"], f["tanggal"], f["jam"]) for f in fog])
