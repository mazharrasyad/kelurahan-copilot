"""Loads SI-DBD's own synthetic records (data.json)."""
import json
import os

_D = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json"), encoding="utf-8"))
WILAYAH = _D["wilayah"]
KASUS = _D["kasus"]
JENTIK = _D["jentik"]
FOGGING = _D["fogging"]  # stored by the legacy system, but no API exposes it yet (added live in the demo)
