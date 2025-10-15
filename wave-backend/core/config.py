# core/config.py
from pathlib import Path
import os, time
from uuid import uuid4

# ---- Project roots ----
ROOT = Path(__file__).resolve().parents[1]          # repo root (wave-backend/)
TPL_PATH = ROOT / "tb.tpl.cir"                      # testbench template (root par)
RUN_ROOT = ROOT / "runs"                            # single workspace
RUN_ROOT.mkdir(parents=True, exist_ok=True)

# ---- CORS ----
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "").split(",") if os.environ.get("ALLOWED_ORIGINS") else []

# ---- Sim parameter bounds + defaults (unchanged; move your old values here if needed) ----
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
DEFAULTS = {
    "VDD": 1.2, "TEMP": 25.0,
    "TR": 1e-11, "TF": 1e-11,
    "PW": 5e-10, "PER": 1e-9,
    "CLOAD": 5e-15,
    "TSTEP": 1e-12, "TSTOP": 3e-9,
}

# ---- Hints (unchanged defaults) ----
DEFAULT_HINTS = {
    "supplies": {"vdd": ["VDD", "VCC"], "vss": ["VSS", "GND", "0"]},
    "outputs": ["Y", "OUT", "Z", "Q", "QO", "QBAR", "Y0", "Y1"],
}
DEFAULT_PARAM_DEFAULTS = {
    "WP": "2e-6", "WN": "1e-6", "W": "1e-6", "L": "1e-6",
    "M": "1", "NF": "1",
    "AD": "0", "AS": "0", "PD": "0", "PS": "0",
}

# ---- Run-dir helpers ----
KEEP_RUNS = os.environ.get("KEEP_RUNS", "0") in ("1", "true", "True")

def new_run_dir(prefix: str = "run_"):
    """Create a predictable folder name under RUN_ROOT, one per run."""
    ts = time.strftime("%Y%m%d-%H%M%S")
    name = f"{prefix}{ts}-{uuid4().hex[:6]}"
    d = RUN_ROOT / name
    d.mkdir(parents=True, exist_ok=True)
    return d
