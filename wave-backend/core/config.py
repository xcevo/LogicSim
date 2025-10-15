# config.py
import os
from pathlib import Path

# ---------- Paths ----------
ROOT = Path(__file__).parent.resolve()
TPL_PATH = ROOT / "tb.tpl.cir"          # legacy/template simulate ke liye
WORK_ROOT = ROOT / "run_workspace"
WORK_ROOT.mkdir(parents=True, exist_ok=True)

# ---------- CORS / Dev Origins ----------
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# ---------- Simulation Param Bounds (safety & perf) ----------
LIMITS = {
    "VDD":   (0.5, 5.0),
    "TEMP":  (-40.0, 125.0),
    "TR":    (1e-13, 1e-8),
    "TF":    (1e-13, 1e-8),
    "PW":    (1e-12, 1e-2),
    "PER":   (1e-12, 1e-2),
    "CLOAD": (1e-16, 1e-11),
    "TSTEP": (1e-13, 1e-9),
    "TSTOP": (1e-10, 5e-6),
}

# ---------- Simulation Param Defaults ----------
DEFAULTS = {
    "VDD": 1.2, "TEMP": 25.0,
    "TR": 1e-11, "TF": 1e-11,
    "PW": 5e-10, "PER": 1e-9,
    "CLOAD": 5e-15,
    "TSTEP": 1e-12, "TSTOP": 3e-9,
}

# ---------- Pin/Role Guess Hints (can be extended via env) ----------
# Request-level overrides → Env-level → Built-in defaults
DEFAULT_HINTS = {
    "supplies": {
        "vdd": ["VDD", "VCC"],
        "vss": ["VSS", "GND", "0"],
    },
    "outputs": ["Y", "OUT", "Z", "Q", "QO", "QBAR", "Y0", "Y1"],
}

# ---------- Reasonable defaults for device/subckt PARAMS when missing ----------
# ye values header normalize karte time inject ho jaati hain (PARAMS: ...)
DEFAULT_PARAM_DEFAULTS = {
    "WP": "2e-6",
    "WN": "1e-6",
    "W":  "1e-6",
    "L":  "1e-6",
    "M":  "1",
    "NF": "1",
    "AD": "0", "AS": "0", "PD": "0", "PS": "0",
}

# ---------- Optional: env overrides JSON for hints ----------
# Example:
# export SUPPLY_ALIASES_JSON='{"supplies":{"vdd":["VDD","VCCA"],"vss":["VSS","GND","0"]},"outputs":["Y","OUT","Q"]}'
SUPPLY_ALIASES_JSON = os.environ.get("SUPPLY_ALIASES_JSON", "").strip()
