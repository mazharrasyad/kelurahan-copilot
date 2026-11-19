"""Generate de-identified synthetic records for both legacy systems.

Privacy by design (UU 27/2022 on Personal Data Protection): no NIK, no names, no addresses.
Records carry only a random internal id, the village and non-identifying attributes, and the
agent is only ever given village-level aggregates. The two systems still disagree on how they
store a village (SIPOS: free-text name, SI-DBD: official code), which the agent must bridge.
Deterministic (fixed seed) so demos and tests are repeatable.
"""
import json
import os
import random
from datetime import date, timedelta

R = random.Random(20261119)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Fictional villages of one district (codes follow the Kemendagri format only).
VILLAGES = [
    ("31.74.06.1001", "Kuningan Barat", 0.10, 1),   # (code, name, share of at-risk toddlers, dengue intensity)
    ("31.74.06.1002", "Pela Mampang", 0.32, 5),
    ("31.74.06.1003", "Bangka", 0.18, 0),
    ("31.74.06.1004", "Tegal Parang", 0.36, 7),
    ("31.74.06.1005", "Mampang Prapatan", 0.12, 3),
]
MONTHS = [date(2026, 8, 10), date(2026, 9, 10), date(2026, 10, 10), date(2026, 11, 10)]


def rand_date(a, b):
    return a + timedelta(days=R.randint(0, (b - a).days))


# --- SIPOS Posyandu -------------------------------------------------------------
posyandu = [{"id": i + 1, "nama_posyandu": f"Posyandu {n}", "kelurahan": v[1], "kecamatan": "Mampang Prapatan"}
            for i, (n, v) in enumerate(zip(["Mawar", "Melati", "Anggrek", "Kenanga", "Teratai"], VILLAGES))]
balita, penimbangan = [], []
bid = 1
for (code, vname, risk_share, _), pos in zip(VILLAGES, posyandu):
    for _ in range(R.randint(28, 40)):
        risk = R.random() < risk_share
        birth = rand_date(date(2022, 1, 1), date(2025, 9, 1))
        balita.append({"id": f"BLT-{bid:04d}", "bulan_lahir": birth.strftime("%Y-%m"), "jk": R.choice("LP"),
                       "kelurahan": vname, "posyandu_id": pos["id"]})
        w = R.uniform(9, 14)
        for k, t in enumerate(MONTHS):
            if R.random() < 0.12:  # did not come to the posyandu that month
                continue
            w += R.uniform(-0.4, 0.1) if risk else R.uniform(0.1, 0.4)
            status = R.choice(["gizi kurang", "gizi kurang", "stunting", "gizi buruk"]) if risk and k >= 1 else "normal"
            penimbangan.append({"balita_id": f"BLT-{bid:04d}", "tanggal": t.isoformat(), "berat_kg": round(w, 1), "status_gizi": status})
        bid += 1

# --- SI-DBD (dengue surveillance) ---------------------------------------------------
kasus, kid = [], 1
for code, _, _, intensity in VILLAGES:
    for _ in range(intensity * 2 + R.randint(0, 2)):
        onset = rand_date(date(2026, 10, 1), date(2026, 11, 16))
        status = "sembuh" if onset < date(2026, 10, 25) else R.choice(["suspek", "terkonfirmasi", "terkonfirmasi"])
        kasus.append({"id": f"DBD-{kid:04d}", "kode_kelurahan": code, "kelompok_umur": R.choice(["0-4", "5-14", "15-44", "45+"]),
                      "jk": R.choice("LP"), "tgl_onset": onset.isoformat(), "status": status})
        kid += 1
jentik = []
for code, _, _, intensity in VILLAGES:
    for wk in range(4):
        d = date(2026, 10, 26) + timedelta(days=7 * wk)
        rumah = R.randint(90, 140)
        positif = max(1, int(rumah * R.uniform(0.02, 0.06) * (1 + intensity / 3)))
        jentik.append({"kode_kelurahan": code, "tgl_periksa": d.isoformat(), "rumah_diperiksa": rumah,
                       "rumah_positif_jentik": positif, "abj_persen": round(100 * (rumah - positif) / rumah, 1)})
fogging = []
for code, _, _, intensity in VILLAGES:
    if intensity >= 3:
        fogging.append({"kode_kelurahan": code, "tanggal": (date(2026, 11, 21) + timedelta(days=R.randint(0, 6))).isoformat(),
                        "jam": R.choice(["07:00", "08:00", "15:30"]), "jumlah_rw_sasaran": R.randint(2, 4),
                        "pelaksana": "Sudin Kesehatan Jakarta Selatan"})
wilayah = [{"kode_kelurahan": c, "nama_kelurahan": n, "kecamatan": "Mampang Prapatan", "kota": "Jakarta Selatan"} for c, n, _, _ in VILLAGES]

json.dump({"posyandu": posyandu, "balita": balita, "penimbangan": penimbangan},
          open(os.path.join(ROOT, "systems", "sipos-posyandu", "data.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump({"wilayah": wilayah, "kasus": kasus, "jentik": jentik, "fogging": fogging},
          open(os.path.join(ROOT, "systems", "si-dbd", "data.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"balita={len(balita)} kasus={len(kasus)} fogging={len(fogging)}")
