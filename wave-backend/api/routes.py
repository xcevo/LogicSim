# api/routes.py
from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import JSONResponse

from core.config import TPL_PATH, new_run_dir, KEEP_RUNS
from core.utils import norm_params, tail_warnings, run_ngspice
from spice.parse import (
    parse_subckts_from_text,
    parse_wrdata_ordered,
    parse_csv,
)
from spice.tb import render_uploaded_tb, render_tb, write_tpl_from_netlist

# Expose only the router here; FastAPI app is created in server.py
router = APIRouter()


@router.get("/health")
def health():
    """ngspice version quick check."""
    try:
        vtxt = subprocess.check_output(["ngspice", "-v"], text=True, timeout=5)
        version = vtxt.strip().splitlines()[0]
    except Exception as e:
        version = f"unavailable ({e})"
    return {"ok": True, "ngspice": version}


@router.post("/analyze")
def analyze(payload: Dict[str, Any] = Body(...)):
    """
    Body: { "netlist": "<...>", "hints"?: {supplies:{vdd:[], vss:[]}, outputs:[] } }
    Resp: { "subckts": [ { "name": str, "pins": [..] } ] }
    """
    text = payload.get("netlist", "")
    hints = payload.get("hints") or {}
    if not text.strip():
        raise HTTPException(400, "empty netlist")

    subs = parse_subckts_from_text(text, hints=hints)
    if not subs:
        raise HTTPException(400, "no .subckt found in netlist")
    return {"subckts": subs}


@router.post("/prepare_tpl")
def prepare_tpl(payload: Dict[str, Any] = Body(...)):
    """
    Body: { "netlist": "<full .cir text>" }
    Effect: tb.tpl.cir is overwritten to contain uploaded netlist + templated TB block.
    """
    netlist = payload.get("netlist", "").strip()
    if not netlist:
        raise HTTPException(400, "empty netlist")

    write_tpl_from_netlist(netlist)
    return {"ok": True, "tpl_path": str(TPL_PATH)}


@router.post("/simulate_uploaded")
def simulate_uploaded(payload: Dict[str, Any] = Body(...)):
    """
    Body:
    {
      "netlist": "<full .cir text>",
      "subckt":   { "name": "NAND2", "pins": ["Y","A","B","VDD","VSS"] },
      "plot_nodes": ["A","Y"],
      "params": { VDD, TEMP, TR, TF, PW, PER, CLOAD, TSTEP, TSTOP },
      "roles": { ... },           # optional
      "pin_drives": { ... },      # optional (front-end chooses pulse/dc/etc per input pin)
      "hints": { ... }            # optional alias hints
    }
    """
    t0 = time.time()
    netlist: str = payload.get("netlist", "")
    sub = payload.get("subckt") or {}
    sub_name: Optional[str] = sub.get("name")
    pin_order: List[str] = sub.get("pins") or []
    plot_nodes: List[str] = payload.get("plot_nodes") or []
    hints: Dict[str, Any] = payload.get("hints") or {}
    roles_override: Optional[Dict[str, Any]] = payload.get("roles")
    pin_drives: Optional[Dict[str, Dict[str, Any]]] = payload.get("pin_drives")

    if not netlist.strip():
        raise HTTPException(400, "empty netlist")
    if not sub_name or not pin_order:
        raise HTTPException(400, "subckt name/pins required")
    if not plot_nodes:
        plot_nodes = pin_order[:2]

    params = norm_params(payload.get("params", {}))

    # Single, predictable run dir
    run_dir = new_run_dir(prefix="u_")
    out_csv = run_dir / "sim.csv"
    cir = run_dir / "tb.cir"
    log = run_dir / "run.log"

    tb_text = render_uploaded_tb(
        netlist_text=netlist,
        subckt_name=sub_name,
        pin_order=pin_order,
        params=params,
        plot_nodes=plot_nodes,
        out_csv=out_csv.resolve(),
        roles=roles_override,
        pin_drives=pin_drives,
        hints=hints,
    )
    cir.write_text(tb_text)

    try:
        _ = run_ngspice(cir, log, timeout_s=25)
    except subprocess.TimeoutExpired:
        return JSONResponse(
            {"error": "ngspice timeout (reduce TSTOP or increase TSTEP)",
             "paths": {"run_dir": str(run_dir), "tb": str(cir), "log": str(log)}},
            status_code=504
        )
    except Exception as e:
        return JSONResponse(
            {"error": f"spawn failed: {e}",
             "paths": {"run_dir": str(run_dir), "tb": str(cir), "log": str(log)}},
            status_code=500
        )

    if not out_csv.exists():
        return JSONResponse(
            {"error": "simulation failed (no CSV)",
             "paths": {"run_dir": str(run_dir), "tb": str(cir), "log": str(log)},
             "log": log.read_text(errors="ignore")},
            status_code=500
        )

    vec_labels = [f"v({n})" for n in plot_nodes]
    try:
        parsed = parse_wrdata_ordered(out_csv, vec_labels)
    except Exception as e:
        return JSONResponse(
            {"error": f"parse failed: {e}",
             "paths": {"run_dir": str(run_dir), "tb": str(cir), "log": str(log)},
             "log": log.read_text(errors="ignore")},
            status_code=500
        )

    elapsed = int((time.time() - t0) * 1000)
    warns = tail_warnings(log.read_text(errors="ignore"))
    waves = {lbl: parsed[lbl] for lbl in vec_labels if lbl in parsed}

    # Clean up unless KEEP_RUNS=1
    if not KEEP_RUNS:
        try:
            shutil.rmtree(run_dir)
        except Exception:
            pass

    return {
        "time": parsed["time"],
        "waveforms": waves,
        "meta": {
            "points": len(parsed["time"]),
            "elapsed_ms": elapsed,
            "warnings": warns,
            "run_dir": str(run_dir),
        },
    }


@router.post("/simulate")
def simulate(payload: Dict[str, Any] = Body(...)):
    """
    Template path: tb.tpl.cir
    Optional: tpl_vars = {"SUBCKT_NAME": "...", "PIN_LIST": ["...", "...", "VDD", "0"]}
    """
    t0 = time.time()
    params_in = payload.get("params", {})
    nodes = payload.get("nodes", ["a", "y"])
    tpl_vars = payload.get("tpl_vars") or {}

    params = norm_params(params_in)

    run_dir = new_run_dir(prefix="")
    out_csv = run_dir / "sim.csv"
    cir = run_dir / "tb.cir"
    log = run_dir / "run.log"

    cir_text = render_tb(params, nodes, out_csv.resolve(), tpl_vars=tpl_vars)
    cir.write_text(cir_text)

    try:
        _ = run_ngspice(cir, log, timeout_s=25)
    except subprocess.TimeoutExpired:
        return JSONResponse(
            {"error": "ngspice timeout (reduce TSTOP or increase TSTEP)",
             "log": log.read_text(errors="ignore")},
            status_code=504
        )
    except Exception as e:
        return JSONResponse({"error": f"spawn failed: {e}"}, status_code=500)

    if not out_csv.exists():
        log_txt = log.read_text(errors="ignore") if log.exists() else ""
        return JSONResponse({"error": "simulation failed (no CSV)", "log": log_txt}, status_code=500)

    data = parse_csv(out_csv)
    elapsed = int((time.time() - t0) * 1000)
    log_txt = log.read_text(errors="ignore") if log.exists() else ""
    warns = tail_warnings(log_txt)

    if not KEEP_RUNS:
        try:
            shutil.rmtree(run_dir)
        except Exception:
            pass

    return {
        "time": data["time"],
        "waveforms": {"v(a)": data["v(a)"], "v(y)": data["v(y)"]},
        "meta": {
            "points": len(data["time"]),
            "elapsed_ms": elapsed,
            "warnings": warns,
            "run_dir": str(run_dir),
        },
    }
