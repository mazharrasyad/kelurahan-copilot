"""Loads SIPOS Posyandu's own de-identified synthetic records (data.json)."""
import json
import os

_D = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json"), encoding="utf-8"))
POSYANDU = _D["posyandu"]
BALITA = _D["balita"]
PENIMBANGAN = _D["penimbangan"]
