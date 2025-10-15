# tb.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Any, Optional

from core.config import TPL_PATH
from spice.parse import guess_roles, normalize_netlist_subckt_params


# ---------------- Template writer (for /prepare_tpl) ----------------

def write_tpl_from_netlist(netlist_text: str) -> None:
    """
    Uploaded .cir ko tb.tpl.cir me embed karta hai, aur neeche
    placeholders based auto-TB block lagata hai.
    """
    net = netlist_text.strip()
    tb_block = """
* === Auto Testbench Template (placeholders kept) ===
.param VDD={VDD}
.param TR={TR}
.param TF={TF}
.param PW={PW}
.param PER={PER}
.param CLOAD={CLOAD}
.temp {TEMP}

* Supplies
VDD_SRC VDD 0 {VDD}
VSS_SRC 0   0 0

* Drive
VIN   {A_NODE} 0 PULSE(0 {VDD} 0 {TR} {TF} {PW} {PER})

* XU1 DUT: subckt + pins are placeholders (filled at /simulate time)
XU1   {PIN_LIST} {SUBCKT_NAME}

Cload {Y_NODE} 0 {CLOAD}

.options method=trap reltol=1e-3 maxord=2
.tran {TSTEP} {TSTOP}
.save time {SAVE_VECTORS}

.control
  set noaskquit
  set nomoremode
  set wr_singlescale
  set filetype=ascii
  run
  wrdata {OUT_CSV} time {SAVE_VECTORS}
.endc

.end
""".lstrip("\n")

    tpl_text = "* === Uploaded Netlist (auto) ===\n" + net + "\n\n" + tb_block
    TPL_PATH.write_text(tpl_text)


# ---------------- Template renderer (legacy /simulate route) ----------------

def render_tb(params: Dict[str, float],
              nodes: List[str],
              out_csv: Path,
              tpl_vars: Optional[Dict[str, Any]] = None) -> str:
    """
    tb.tpl.cir ko fill karta hai. Optional tpl_vars:
      { "SUBCKT_NAME": "NAND2", "PIN_LIST": ["Y","A","B","VDD","0"] }
    """
    tpl = TPL_PATH.read_text()
    a_node = nodes[0] if len(nodes) >= 1 else "A"
    y_node = nodes[1] if len(nodes) >= 2 else "Y"

    # defaults (back-compat)
    subckt_name = "NOT1"
    pin_list = f"{y_node} {a_node} VDD 0"

    if tpl_vars:
        subckt_name = str(tpl_vars.get("SUBCKT_NAME", subckt_name))
        pl = tpl_vars.get("PIN_LIST", pin_list)
        if isinstance(pl, list):
            pin_list = " ".join(pl)
        elif isinstance(pl, str) and pl.strip():
            pin_list = pl.strip()

    save_vec = f"v({a_node}) v({y_node})"
    text = (
        tpl.replace("{VDD}", f"{params['VDD']}")
           .replace("{TR}", f"{params['TR']}")
           .replace("{TF}", f"{params['TF']}")
           .replace("{PW}", f"{params['PW']}")
           .replace("{PER}", f"{params['PER']}")
           .replace("{CLOAD}", f"{params['CLOAD']}")
           .replace("{TSTEP}", f"{params['TSTEP']}")
           .replace("{TSTOP}", f"{params['TSTOP']}")
           .replace("{TEMP}", f"{params['TEMP']}")
           .replace("{A_NODE}", a_node)
           .replace("{Y_NODE}", y_node)
           .replace("{SAVE_VECTORS}", save_vec)
           .replace("{OUT_CSV}", str(out_csv))
           .replace("{SUBCKT_NAME}", subckt_name)
           .replace("{PIN_LIST}", pin_list)
    )
    return text


# ---------------- Helpers ----------------

def _drive_line_for_pin(pin: str,
                        drive: Dict[str, Any],
                        vdd: float,
                        tr: float,
                        tf: float,
                        pw: float,
                        per: float) -> str:
    """
    'pin_drives' ko NGspice source line me convert karta hai.
    Accepts either:
      {type:"pulse", v1, v2, td, tr, tf, pw, per}
    or   {kind:"pulse", ...}  (back-compat)
      {type:"dc"/"const", v: <volt>} or {dc: <volt>}
      {type:"none"}   -> no source (commented)
    """
    # normalize keys
    t = (drive.get("type") or drive.get("kind") or "pulse").lower()

    if t in ("none", "off", "z"):
        return f"* VIN_{pin} {pin} 0 (none)"

    if t in ("dc", "const"):
        v = float(drive.get("v", drive.get("dc", 0.0)))
        return f"VIN_{pin} {pin} 0 {v}"

    # default: pulse
    v1 = float(drive.get("v1", 0.0))
    v2 = float(drive.get("v2", vdd))
    td = float(drive.get("td", 0.0))
    tr_ = float(drive.get("tr", tr))
    tf_ = float(drive.get("tf", tf))
    pw_ = float(drive.get("pw", pw))
    per_ = float(drive.get("per", per))
    return f"VIN_{pin} {pin} 0 PULSE({v1} {v2} {td} {tr_} {tf_} {pw_} {per_})"


# ---------------- Rich testbench builder (for /simulate_uploaded) ----------------

def render_uploaded_tb(netlist_text: str,
                       subckt_name: str,
                       pin_order: List[str],
                       params: Dict[str, float],
                       plot_nodes: List[str],
                       out_csv: Path,
                       roles: Optional[Dict[str, Any]] = None,
                       pin_drives: Optional[Dict[str, Dict[str, Any]]] = None,
                       hints: Optional[dict] = None) -> str:
    """
    Final TB jo ngspice ko jayega.
    """
    # 1) Normalize .SUBCKT headers so width/length jaise params pins na ban jayen
    netlist_text = normalize_netlist_subckt_params(netlist_text, hints=hints)

    # 2) Roles: supplies + IO
    if roles is None:
        auto = guess_roles(pin_order, hints=hints)
        roles = {
            "vdd": auto["vdd"],
            "vss": auto["vss"],
            "outputs": [auto["output"]],
            "inputs": auto["inputs"],
        }
    else:
        roles.setdefault("outputs", [])
        roles.setdefault("inputs", [])

    vdd_node = roles.get("vdd", "VDD")
    vss_node = roles.get("vss", "0")

    # be safe: never treat supplies as inputs accidentally
    supplies = {vdd_node, vss_node, "VDD", "VSS", "0", "GND"}
    inputs = [p for p in roles.get("inputs", []) if p not in supplies]
    outputs = [p for p in roles.get("outputs", []) if p not in supplies]

    # 3) Sources
    src_lines: List[str] = [
        f"VDD_SRC {vdd_node} 0 {params['VDD']}",  # VDD tie
        f"VSS_SRC {vss_node} 0 0",               # VSS tie  <<< IMPORTANT
    ]

    # user-specified drives (default: pulse 0->VDD)
    pin_drives = pin_drives or {}
    for p in inputs:
        drv = pin_drives.get(p, {"type": "pulse"})
        src_lines.append(
            _drive_line_for_pin(
                pin=p,
                drive=drv,
                vdd=params["VDD"],
                tr=params["TR"],
                tf=params["TF"],
                pw=params["PW"],
                per=params["PER"],
            )
        )

    # 4) Loads on outputs (at least one load so nodes aren't floating)
    load_lines: List[str] = []
    if outputs:
        for outp in outputs:
            load_lines.append(f"CLOAD_{outp} {outp} 0 {params['CLOAD']}")
    else:
        # fallback: pick first non-supply pin
        fallback = next((p for p in pin_order if p not in supplies), None)
        if fallback:
            load_lines.append(f"CLOAD_{fallback} {fallback} 0 {params['CLOAD']}")

    # 5) DUT instance — strictly nodes only; params header me defaulted
    pinlist = " ".join(pin_order)
    xu_line = f"XU1 {pinlist} {subckt_name}"

    # 6) SAVE vectors
    # ensure we don't duplicate
    uniq_nodes = []
    seen = set()
    for n in plot_nodes:
        if n not in seen:
            uniq_nodes.append(n)
            seen.add(n)
    save_vecs = " ".join([f"v({n})" for n in uniq_nodes])

    # 7) TB text
    return f"""
* === Uploaded Netlist ===
{netlist_text}

* === Auto-generated Testbench ===
.options method=trap reltol=1e-3 maxord=2
.temp {params['TEMP']}

* Sources
{os.linesep.join(src_lines)}

* DUT
{xu_line}

* Loads
{os.linesep.join(load_lines) if load_lines else "* (no extra loads)"}

.tran {params['TSTEP']} {params['TSTOP']}
.save time {save_vecs}

.control
  set noaskquit
  set nomoremode
  set wr_singlescale
  set filetype=ascii
  run
  wrdata {out_csv} time {save_vecs}
.endc


.end
""".strip()
