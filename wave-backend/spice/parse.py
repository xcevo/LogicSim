# parse.py
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

from core.config import DEFAULT_HINTS, DEFAULT_PARAM_DEFAULTS
from core.utils import merge_hints, load_env_hints, to_lower_set


# --------- Regex ---------
SUBCKT_RE = re.compile(r"^\s*\.subckt\s+(\S+)\s+(.+)$", re.IGNORECASE)


# ---- split pins vs params; support commas; use supply hints if no 'params:' ----
def _split_pins_params(rest: str, merged_hints: dict):
    """
    Return (pins:list[str], params:list[str]) from the '.subckt ...' tail.
    - Split on commas OR whitespace, strip trailing commas/parentheses.
    - If 'params:' present → tokens before it = pins; after it = params (strip '=val').
    - Else: if any supply alias appears, consider pins = tokens up to the LAST supply token, rest = params.
      (common style: ... <IO pins> <VDD VSS> <WP WN L ...>)
    - Tokens containing '=' are param-like (not pins).
    """
    # split on comma or whitespace
    raw = re.split(r"[,\s]+", rest.strip())
    toks = [re.sub(r"^[\(\[]|[\)\]]$", "", t) for t in raw if t]  # remove () [] around tokens

    pins, params = [], []
    lower = [t.lower() for t in toks]

    # explicit 'params:'
    if "params:" in lower:
        i = lower.index("params:")
        pin_tokens = toks[:i]
        param_tokens = toks[i + 1:]
    else:
        pin_tokens = toks
        param_tokens = []

    # helper sets
    vdd_alias = to_lower_set(merged_hints["supplies"]["vdd"])
    vss_alias = to_lower_set(merged_hints["supplies"]["vss"])

    # remove k=v from pin candidates, bucket them into params
    pin_clean = []
    for t in pin_tokens:
        if "=" in t:
            params.append(t.split("=", 1)[0])
        else:
            pin_clean.append(t)

    # if no explicit params:, try heuristic using last supply position
    if not param_tokens:
        last_supply_idx = -1
        for idx, t in enumerate(pin_clean):
            tl = t.lower()
            if tl in vdd_alias or tl in vss_alias:
                last_supply_idx = idx
        if last_supply_idx >= 0 and last_supply_idx < len(pin_clean) - 1:
            # move trailing tokens after last supply to params
            params.extend([x for x in pin_clean[last_supply_idx + 1:]])
            pin_clean = pin_clean[: last_supply_idx + 1]

    # normalize final lists (de-dup preserving order)
    seen = set()
    pins_out = []
    for p in pin_clean:
        if p and p not in seen:
            pins_out.append(p)
            seen.add(p)

    seen = set()
    params_out = []
    for p in list(param_tokens) + params:
        p = p.split("=", 1)[0]  # strip '=val'
        if p and p not in seen:
            params_out.append(p)
            seen.add(p)

    return pins_out, params_out


# ---- scan .subckt lines from netlist text ----
def parse_subckts_from_text(text: str, hints: Optional[dict] = None):
    """Return list of {name, pins[]} found in a netlist text."""
    subckts = []
    merged = merge_hints(hints, load_env_hints(), DEFAULT_HINTS)
    for line in text.splitlines():
        m = SUBCKT_RE.match(line)
        if m:
            name = m.group(1)
            rest = m.group(2).strip()
            pins, _params = _split_pins_params(rest, merged)
            subckts.append({"name": name, "pins": pins})
    return subckts


# ---- guess roles (output / inputs / supplies) from pins ----
def guess_roles(pins: List[str], hints: Optional[dict] = None):
    """
    Heuristic using provided hints (request/env) with fallback to defaults.
    Returns: {"output": str, "inputs": [..], "vdd": str, "vss": str}
    """
    hints_final = merge_hints(hints, load_env_hints(), DEFAULT_HINTS)
    vdd_alias = to_lower_set(hints_final["supplies"]["vdd"])
    vss_alias = to_lower_set(hints_final["supplies"]["vss"])
    out_alias = to_lower_set(hints_final["outputs"])

    vdd = next((p for p in pins if p.lower() in vdd_alias), None)
    vss = next((p for p in pins if p.lower() in vss_alias), None)

    out_pin = next((p for p in pins if p.lower() in out_alias), None)
    if not out_pin:
        # first non-supply as output fallback
        non_supply = [p for p in pins if p.lower() not in (vdd_alias | vss_alias)]
        out_pin = non_supply[0] if non_supply else (pins[0] if pins else "Y")

    inputs = [p for p in pins if p != out_pin and p.lower() not in (vdd_alias | vss_alias)]
    return {"output": out_pin, "inputs": inputs, "vdd": vdd or "VDD", "vss": vss or "0"}


# ---- rewrite .SUBCKT headers to add PARAMS: so ngspice doesn't treat params as pins ----
def normalize_netlist_subckt_params(netlist_text: str, hints: Optional[dict] = None) -> str:
    merged = merge_hints(hints, load_env_hints(), DEFAULT_HINTS)
    out_lines = []
    for line in netlist_text.splitlines():
        m = SUBCKT_RE.match(line)
        if not m:
            out_lines.append(line)
            continue

        name = m.group(1)
        rest = m.group(2).strip()
        pins, params = _split_pins_params(rest, merged)

        # already explicit PARAMS: → keep original
        if " params:" in rest.lower():
            out_lines.append(line)
            continue

        # inject PARAMS: defaults
        if params:
            defaults = []
            for p in params:
                pv = DEFAULT_PARAM_DEFAULTS.get(p.upper(), "0")
                defaults.append(f"{p}={pv}")
            new_line = f".SUBCKT {name} {' '.join(pins)} PARAMS: {' '.join(defaults)}"
        else:
            new_line = f".SUBCKT {name} {' '.join(pins)}"

        out_lines.append(new_line)

    return "\n".join(out_lines)


# ===================== wrdata parsing =====================

def parse_csv(csv_path: Path) -> Dict[str, List[float]]:
    """
    Legacy helper: Parse ngspice 'wrdata' ASCII (whitespace-delimited) for fixed vectors v(a), v(y).
    Handles:
      - No header: numeric first line (3 cols: time v(a) v(y) OR 4 cols: Index time v(a) v(y))
      - Header present: 'Index time v(a) v(y)' OR 'time v(a) v(y)'
    """
    with csv_path.open() as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    if not lines:
        raise ValueError("empty wrdata file")

    def is_numeric_line(ln: str) -> bool:
        parts = re.split(r"\s+", ln)
        try:
            for p in parts:
                float(p)
            return True
        except Exception:
            return False

    first = lines[0]

    # numeric → no header
    if is_numeric_line(first):
        parts0 = re.split(r"\s+", first)
        ncol = len(parts0)
        if ncol >= 4:
            idx_time, idx_va, idx_vy = 1, 2, 3
        elif ncol == 3:
            idx_time, idx_va, idx_vy = 0, 1, 2
        else:
            raise ValueError(f"unexpected numeric format with {ncol} columns")

        t, va, vy = [], [], []
        for ln in lines:
            if not is_numeric_line(ln):
                continue
            parts = re.split(r"\s+", ln)
            if len(parts) <= max(idx_time, idx_va, idx_vy):
                continue
            try:
                t.append(float(parts[idx_time]))
                va.append(float(parts[idx_va]))
                vy.append(float(parts[idx_vy]))
            except Exception:
                continue

        if not t:
            raise ValueError("no numeric rows parsed (no-header path)")
        return {"time": t, "v(a)": va, "v(y)": vy}

    # header present
    headers = re.split(r"\s+", first)
    lower = [h.lower() for h in headers]
    data_start = 1

    if lower[0] == "index":
        if "time" in lower:
            i_time = lower.index("time")
        else:
            raise ValueError(f"unexpected header missing time: {headers}")
    else:
        if "time" in lower:
            i_time = lower.index("time")
        else:
            raise ValueError(f"unexpected header missing time: {headers}")

    def find_col(name: str) -> int:
        nm = name.lower()
        for i, h in enumerate(lower):
            if h.replace(" ", "") == nm:
                return i
        raise ValueError(f"column '{name}' not found in {headers}")

    i_va = find_col("v(a)")
    i_vy = find_col("v(y)")

    t, va, vy = [], [], []
    for ln in lines[data_start:]:
        parts = re.split(r"\s+", ln)
        if len(parts) <= max(i_time, i_va, i_vy):
            continue
        try:
            t.append(float(parts[i_time]))
            va.append(float(parts[i_va]))
            vy.append(float(parts[i_vy]))
        except Exception:
            continue

    if not t:
        raise ValueError("no numeric rows parsed (header path)")
    return {"time": t, "v(a)": va, "v(y)": vy}


def parse_wrdata_ordered(csv_path: Path, vec_labels: List[str]) -> Dict[str, List[float]]:
    """
    Read ngspice wrdata (whitespace-delimited) WITHOUT relying on headers.
    Columns expected:
      - If 'Index' present: [Index, time, v(node1), v(node2), ...]
      - Else:               [time, v(node1), v(node2), ...]
    vec_labels: e.g., ["v(A)","v(Y)"] in the SAME ORDER used in wrdata.
    """
    with csv_path.open() as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    if not lines:
        raise ValueError("empty wrdata")

    def is_numeric(ln: str) -> bool:
        try:
            [float(x) for x in re.split(r"\s+", ln)]
            return True
        except Exception:
            return False

    first = next((ln for ln in lines if is_numeric(ln)), None)
    if first is None:
        raise ValueError("no numeric data rows")

    parts0 = re.split(r"\s+", first)
    ncol = len(parts0)

    # infer if Index exists
    if ncol == len(vec_labels) + 2:
        idx_time = 1
        start_data = 2
    elif ncol == len(vec_labels) + 1:
        idx_time = 0
        start_data = 1
    else:
        # fallback heuristic: first tok int & second float → index present
        try:
            int(parts0[0])
            float(parts0[1])
            idx_time, start_data = 1, 2
        except Exception:
            idx_time, start_data = 0, 1

    t = []
    waves = {lbl: [] for lbl in vec_labels}

    for ln in lines:
        if not is_numeric(ln):
            continue
        parts = re.split(r"\s+", ln)
        if len(parts) < (start_data + len(vec_labels)):
            continue
        try:
            t.append(float(parts[idx_time]))
            for i, lbl in enumerate(vec_labels):
                waves[lbl].append(float(parts[start_data + i]))
        except Exception:
            continue

    if not t:
        raise ValueError("no numeric rows parsed")
    out = {"time": t}
    out.update(waves)
    return out
