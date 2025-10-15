# run.py
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Dict, List


def run_ngspice(cir_path: Path, log_path: Path, timeout_s: int = 20) -> int:
    """
    Execute ngspice in batch mode on the given circuit file.
    Writes stdout/stderr to log_path. Returns process return code.
    """
    proc = subprocess.run(
        ["ngspice", "-b", "-o", str(log_path), str(cir_path)],
        cwd=cir_path.parent,
        text=True,
        capture_output=False,
        timeout=timeout_s,
    )
    return proc.returncode


def tail_warnings(log_text: str) -> List[str]:
    """
    Return up to 20 unique warning/error/convergence lines from the tail of the log.
    """
    warns: List[str] = []
    for line in log_text.splitlines()[-200:]:
        if re.search(r"(warning|converg|error)", line, re.IGNORECASE):
            warns.append(line.strip())
    seen = set()
    uniq: List[str] = []
    for w in warns:
        if w not in seen:
            uniq.append(w)
            seen.add(w)
    return uniq[:20]


def parse_csv(csv_path: Path) -> Dict[str, List[float]]:
    """
    Parse ngspice 'wrdata' ASCII (whitespace-delimited) for known v(a), v(y).
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

    # Case 1: First line numeric → no header
    if is_numeric_line(first):
        parts0 = re.split(r"\s+", first)
        ncol = len(parts0)
        if ncol >= 4:
            idx_time, idx_va, idx_vy = 1, 2, 3
        elif ncol == 3:
            idx_time, idx_va, idx_vy = 0, 1, 2
        else:
            raise ValueError(f"unexpected numeric format with {ncol} columns")

        t: List[float] = []
        va: List[float] = []
        vy: List[float] = []
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

    # Case 2: Header present
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

    t: List[float] = []
    va: List[float] = []
    vy: List[float] = []
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

    t: List[float] = []
    waves: Dict[str, List[float]] = {lbl: [] for lbl in vec_labels}

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
    out: Dict[str, List[float]] = {"time": t}
    out.update(waves)
    return out
