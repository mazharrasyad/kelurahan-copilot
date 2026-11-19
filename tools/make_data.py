"""Generate one synthetic population and write each legacy system's own data file.

The two systems never share a database: SIPOS Posyandu only knows mothers by NIK and
villages by free-text name; SI-DBD knows patients by NIK and villages by official code.
The same people appear in both, which is exactly what the cross-system agent must join.
Deterministic (fixed seed), so demos and tests are repeatable.
"""
import json
import os
import random
from datetime import date, timedelta

R = random.Random(20261119)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Synthetic villages of one district (codes follow the Kemendagri format; data is fictional).
VILLAGES = [
    ("31.74.06.1001", "Kuningan Barat"),
    ("31.74.06.1002", "Pela Mampang"),
    ("31.74.06.1003", "Bangka"),
    ("31.74.06.1004", "Tegal Parang"),
    ("31.74.06.1005", "Mampang Prapatan"),
]
FEMALE = ["Siti", "Dewi", "Rina", "Ani", "Wulan", "Nur", "Indah", "Lestari", "Ayu", "Fitri", "Yuni", "Ratna", "Sri", "Maya", "Putri", "Dian"]
MALE = ["Budi", "Agus", "Rizki", "Dimas", "Fajar", "Hendra", "Joko", "Bayu", "Eko", "Arif"]
FAMILY = ["Santoso", "Wijaya", "Pratama", "Setiawan", "Hidayat", "Saputra", "Kurniawan", "Rahmawati", "Nugroho", "Permata", "Siregar", "Harahap", "Gunawan"]
KIDS = ["Aisyah", "Bima", "Citra", "Daffa", "Elsa", "Farel", "Gita", "Hafiz", "Intan", "Kenzo", "Laila", "Naufal", "Olivia", "Raka", "Salsa", "Zidan"]


def nik(code, birth, female, seq):
    """16-digit NIK: province+regency+district (6) + DDMMYY (female day + 40) + 4-digit sequence."""
    d = birth.day + (40 if female else 0)
    return f"{code.replace('.', '')[:6]}{d:02d}{birth.month:02d}{birth.year % 100:02d}{seq:04d}"


def rand_date(start, end):
    return start + timedelta(days=R.randint(0, (end - start).days))


people_seq = 1
mothers = []
for i in range(38):
    code, name = R.choice(VILLAGES)
    birth = rand_date(date(1988, 1, 1), date(2002, 12, 31))
    mothers.append({"nik": nik(code, birth, True, people_seq), "nama": f"{R.choice(FEMALE)} {R.choice(FAMILY)}",
                    "tgl_lahir": birth.isoformat(), "kode_kelurahan": code, "kelurahan": name,
                    "alamat": f"Jl. {R.choice(['Kenari', 'Melati', 'Mawar', 'Flamboyan', 'Cempaka'])} No. {R.randint(1, 120)}",
                    "rt": f"{R.randint(1, 12):03d}", "rw": f"{R.randint(1, 8):03d}"})
    people_seq += 1

# --- SIPOS Posyandu -------------------------------------------------------------
posyandu = [{"id": i + 1, "nama_posyandu": f"Posyandu {n}", "kelurahan": v, "kecamatan": "Mampang Prapatan"}
            for i, (n, (_, v)) in enumerate(zip(["Mawar", "Melati", "Anggrek", "Kenanga", "Teratai"], VILLAGES))]
balita, penimbangan = [], []
months = [date(2026, 8, 10), date(2026, 9, 10), date(2026, 10, 10), date(2026, 11, 10)]
bid = 1
for m in mothers:
    for _ in range(2 if R.random() < 0.2 else 1):
        female = R.random() < 0.5
        birth = rand_date(date(2022, 1, 1), date(2025, 10, 1))
        pos = next(p for p in posyandu if p["kelurahan"] == m["kelurahan"])
        balita.append({"id": bid, "nama_balita": f"{R.choice(KIDS)} {m['nama'].split()[-1]}", "tgl_lahir": birth.isoformat(),
                       "jk": "P" if female else "L", "nik_ibu": m["nik"], "nama_ibu": m["nama"],
                       "alamat": m["alamat"], "rt": m["rt"], "rw": m["rw"], "kelurahan": m["kelurahan"], "posyandu_id": pos["id"]})
        risk = R.random() < 0.3
        w = R.uniform(9, 14)
        for k, t in enumerate(months):
            w += R.uniform(-0.4, 0.1) if risk else R.uniform(0.1, 0.4)
            status = "normal"
            if risk and k >= 2:
                status = R.choice(["gizi kurang", "gizi kurang", "stunting", "gizi buruk"])
            penimbangan.append({"balita_id": bid, "tanggal": t.isoformat(), "berat_kg": round(w, 1),
                                "tinggi_cm": round(75 + (t - birth).days / 30 * 0.9 - (4 if risk else 0), 1), "status_gizi": status})
        bid += 1

# --- SI-DBD (dengue surveillance) ---------------------------------------------------
at_risk_mothers = {b["nik_ibu"] for b in balita
                   if [p for p in penimbangan if p["balita_id"] == b["id"]][-1]["status_gizi"] != "normal"}
infected_mothers = R.sample(sorted(at_risk_mothers), 4) + R.sample([m["nik"] for m in mothers if m["nik"] not in at_risk_mothers], 3)
cases, cid = [], 1
for n in infected_mothers:
    m = next(x for x in mothers if x["nik"] == n)
    cases.append({"nik": m["nik"], "nama_pasien": m["nama"], "jenis_kelamin": "P", "tgl_lahir": m["tgl_lahir"],
                  "alamat": m["alamat"], "kode_kelurahan": m["kode_kelurahan"]})
for _ in range(11):  # other residents (not in SIPOS)
    code, _ = R.choice(VILLAGES)
    female = R.random() < 0.5
    birth = rand_date(date(1965, 1, 1), date(2015, 12, 31))
    cases.append({"nik": nik(code, birth, female, people_seq), "nama_pasien": f"{R.choice(FEMALE if female else MALE)} {R.choice(FAMILY)}",
                  "jenis_kelamin": "P" if female else "L", "tgl_lahir": birth.isoformat(),
                  "alamat": f"Jl. {R.choice(['Duren', 'Bangka Raya', 'Kemang', 'Tegal Parang Utara'])} No. {R.randint(1, 90)}", "kode_kelurahan": code})
    people_seq += 1
kasus = []
for c in cases:
    onset = rand_date(date(2026, 10, 1), date(2026, 11, 15))
    status = "sembuh" if onset < date(2026, 10, 20) else R.choice(["suspek", "terkonfirmasi", "terkonfirmasi"])
    kasus.append({"id": cid, **c, "tgl_onset": onset.isoformat(), "status": status,
                  "faskes_pelapor": R.choice(["Puskesmas Mampang Prapatan", "RS Siaga Raya", "RSUD Mampang"])})
    cid += 1
jentik = []
for code, _ in VILLAGES:
    for wk in range(4):
        d = date(2026, 10, 26) + timedelta(days=7 * wk)
        rumah = R.randint(80, 140)
        positif = R.randint(3, 25)
        jentik.append({"kode_kelurahan": code, "tgl_periksa": d.isoformat(), "rumah_diperiksa": rumah,
                       "rumah_positif_jentik": positif, "abj_persen": round(100 * (rumah - positif) / rumah, 1)})
fogging = []
for code, _ in VILLAGES:
    active = [k for k in kasus if k["kode_kelurahan"] == code and k["status"] != "sembuh"]
    if active:
        fogging.append({"kode_kelurahan": code, "tanggal": (date(2026, 11, 21) + timedelta(days=R.randint(0, 6))).isoformat(),
                        "jam": R.choice(["07:00", "08:00", "15:30"]), "rw_sasaran": sorted({f"{R.randint(1, 8):03d}" for _ in range(3)}),
                        "petugas": "Sudin Kesehatan Jakarta Selatan"})

wilayah = [{"kode_kelurahan": c, "nama_kelurahan": n, "kecamatan": "Mampang Prapatan", "kota": "Jakarta Selatan"} for c, n in VILLAGES]

os.makedirs(os.path.join(ROOT, "systems", "sipos-posyandu"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "systems", "si-dbd"), exist_ok=True)
json.dump({"posyandu": posyandu, "balita": balita, "penimbangan": penimbangan},
          open(os.path.join(ROOT, "systems", "sipos-posyandu", "data.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump({"wilayah": wilayah, "kasus": kasus, "jentik": jentik, "fogging": fogging},
          open(os.path.join(ROOT, "systems", "si-dbd", "data.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"balita={len(balita)} at-risk-mothers={len(at_risk_mothers)} kasus={len(kasus)} fogging={len(fogging)}")
