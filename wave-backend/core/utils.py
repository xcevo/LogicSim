# core/utils.py
from __future__ import annotations

import os
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple

from core.config import (
    LIMITS,        # dict: param -> (lo, hi)
    DEFAULTS,      # dict: param -> default
    DEFAULT_HINTS, # supplies/output hints
)

# ------------------ basic helpers ------------------

def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))

def norm_params(p: Dict[str, Any]) -> Dict[str, float]:
    """
    Clamp + sanitize all simulation params using LIMITS/DEFAULTS.
    Also enforce PER >= PW and TSTOP >= 3*PER.
    """
    out: Dict[str, float] = {}
    for k, (lo, hi) in LIMITS.items():
        v = p.get(k, DEFAULTS[k])
        try:
            fv = float(v)
        except Exception:
            fv = DEFAULTS[k]
        out[k] = clamp(fv, lo, hi)

    # sanity coupling
    if out["PER"] < out["PW"]:
        out["PER"] = out["PW"] * 2.0
    if out["TSTOP"] < 3 * out["PER"]:
        out["TSTOP"] = 3 * out["PER"]
    return out

def to_lower_set(items) -> set[str]:
    return {str(x).lower() for x in items}

# ------------------ hint loading/merging ------------------

def load_env_hints() -> dict:
    """
    Optional env override:
      SUPPLY_ALIASES_JSON='{"supplies":{"vdd":["VDD","VCCA"],"vss":["VSS","GND","0"]},"outputs":["Y","OUT","Q"]}'
    """
    txt = os.environ.get("SUPPLY_ALIASES_JSON", "").strip()
    if not txt:
        return {}
    try:
        obj = json.loads(txt)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}

def merge_hints(*objs) -> dict:
    """
    Merge hints from (request, env, defaults). Order matters — earlier wins on empties.
    Output schema:
      {"supplies":{"vdd":[...], "vss":[...]}, "outputs":[...]}
    """
    out = {"supplies": {"vdd": [], "vss": []}, "outputs": []}
    for o in objs:
        if not o:
            continue
        sup = o.get("supplies", {})
        if "vdd" in sup: out["supplies"]["vdd"].extend(sup["vdd"])
        if "vss" in sup: out["supplies"]["vss"].extend(sup["vss"])
        outs = o.get("outputs", [])
        out["outputs"].extend(outs)

    def uniq(seq):
        seen = set(); res = []
        for s in seq:
            k = str(s).lower()
            if k not in seen:
                seen.add(k); res.append(str(s))
        return res

    # backfill with defaults if empty
    def_vdd = DEFAULT_HINTS["supplies"]["vdd"]
    def_vss = DEFAULT_HINTS["supplies"]["vss"]
    def_out = DEFAULT_HINTS["outputs"]

    out["supplies"]["vdd"] = uniq(out["supplies"]["vdd"]) or def_vdd
    out["supplies"]["vss"] = uniq(out["supplies"]["vss"]) or def_vss
    out["outputs"] = uniq(out["outputs"]) or def_out
    return out

# ------------------ ngspice run + logs ------------------

def tail_warnings(log_text: str) -> List[str]:
    warns: List[str] = []
    for line in log_text.splitlines()[-200:]:
        if re.search(r"(warning|converg|error)", line, re.IGNORECASE):
            warns.append(line.strip())
    # de-dup preserve order
    seen = set(); uniq = []
    for w in warns:
        if w not in seen:
            uniq.append(w); seen.add(w)
    return uniq[:20]

def run_ngspice(cir_path: Path, log_path: Path, timeout_s: int = 20) -> int:
    """
    Run ngspice in batch; write stdout/stderr to log_path (handled by -o).
    Returns process returncode.
    """
    proc = subprocess.run(
        ["ngspice", "-b", "-o", str(log_path), str(cir_path)],
        cwd=cir_path.parent,
        text=True,
        capture_output=False,
        timeout=timeout_s
    )
    return proc.returncode
