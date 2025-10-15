// src/App.jsx
import { useEffect, useMemo, useState } from 'react';
import ControlsBar from './components/ControlsBar.jsx';
import WaveformChart from './components/WaveformChart.jsx';
import SubcktPicker from './components/SubcktPicker.jsx';
import NodePicker from './components/NodePicker.jsx';
import PinRoleTable from './components/PinRoleTable.jsx';
import { useSimulate, useUploadedSim } from './hooks/useSimulate.js';
import axios from 'axios';


export default function App() {

  const [verified, setVerified] = useState(null); // null = loading
  const [error, setError] = useState(null);
  const API_BASE_URL = "https://icurate.logicknots.com"

  useEffect(() => {
    if (window.location.hostname === "localhost") {
      console.log("Debug: verification skipped in development");
      setVerified(true); // Skip verification
      return;
    }

    const urlParams = new URLSearchParams(window.location.search);
    const urlToken = urlParams.get("token");
    const accessToken = localStorage.getItem("access_token");

    const cleanURL = () => {
      window.history.replaceState({}, document.title, window.location.pathname);
    };

    const verifyWithUrlToken = async () => {
      try {
        const res = await axios.post(
          `${API_BASE_URL}/auth/verify-token`,
          { token: urlToken },
          { withCredentials: true }
        );
        localStorage.setItem("access_token", res.data.access_token);
        setVerified(true);
        cleanURL();
      } catch (err) {
        setError(err.response?.data?.msg || "Token verification failed");
        setVerified(false);
      }
    };

    const verifyWithAccessToken = async () => {
      try {
        await axios.post(`${API_BASE_URL}/auth/verify-token`, {
          token: accessToken,
        });
        setVerified(true);
      } catch (err) {
        if (err.response?.status === 401) {
          await refreshAccessToken();
        } else {
          setError(err.response?.data?.msg || "Invalid access token");
          setVerified(false);
        }
      }
    };

    const refreshAccessToken = async () => {
      try {
        const res = await axios.post(
          `${API_BASE_URL}/auth/refresh`,
          {},
          { withCredentials: true }
        );
        localStorage.setItem("access_token", res.data.access_token);
        setVerified(true);
      } catch (err) {
        setError("Session expired. Please login again.");
        setVerified(false);
      }
    };

    const runVerification = async () => {
      if (urlToken) {
        await verifyWithUrlToken();
      } else if (accessToken) {
        await verifyWithAccessToken();
      } else {
        setError("No token provided");
        setVerified(false);
      }
    };

    runVerification();
  }, [API_BASE_URL]);

  useEffect(() => {
    if (verified === true) {
      (async () => {
        await layerLibrary.ensureLoaded();
        console.log("✅ layers ready:", layerLibrary.getAllLayers());
      })();
    }
  }, [verified]);


  // keep pulse params in state (not shown in header)
  const [params, setParams] = useState({
    VDD: '1.2',
    // pulse params (defaults set by model)
    TR: '1e-11',
    TF: '1e-11',
    PW: '5e-10',
    PER: '1e-9',
    // non-pulse
    CLOAD: '5e-15',
    TSTEP: '1e-12',
    TSTOP: '3e-9',
    TEMP: '25',
  });

  const [pulsePreset, setPulsePreset] = useState({ name: 'Standard', tr: '1e-11', tf: '1e-11', pw: '5e-10', per: '1e-9' });

  const [auto, setAuto] = useState(false);
  const [status, setStatus] = useState({ state: 'idle', runId: 0 });
  const [data, setData] = useState({ time: [], waveforms: {} });

  // uploaded flow state
  const [netlist, setNetlist] = useState('');
  const [hints, setHints] = useState({
    supplies: { vdd: ['VDD', 'VCC'], vss: ['VSS', 'GND', '0'] },
    outputs: ['Y', 'OUT', 'Z', 'Q'],
  });
  const [subckts, setSubckts] = useState([]);
  const [chosen, setChosen] = useState(null);
  const [plotNodes, setPlotNodes] = useState([]);
  const [pinRoles, setPinRoles] = useState({}); // { PIN: { role, drive, params{...} } }

  const { runDebounced } = useSimulate(); // legacy demo
  const { analyze, simulateUploaded } = useUploadedSim();

  const traces = useMemo(() => {
    const t = data.time || [];
    const entries = data.waveforms ? Object.entries(data.waveforms) : [];
    return entries.map(([k, y]) => ({ name: k, x: t, y: y || [] }));
  }, [data]);

  const runLegacy = () => runDebounced({ setStatus, setData }, params, false);

  async function doAnalyze(text, userHints = hints) {
    setNetlist(text);
    setHints(userHints);
    setStatus({ state: 'running' });
    try {
      const res = await analyze(text, userHints);
      setSubckts(res.subckts || []);
      setChosen(null);
      setPlotNodes([]);
      setPinRoles({});
      setStatus({ state: 'idle' });
    } catch (e) {
      setStatus({ state: 'error', error: String(e) });
    }
  }

  // roles from pinRoles
  function computeRoles() {
    const vdd = Object.keys(pinRoles).find((p) => pinRoles[p]?.role === 'vdd') || 'VDD';
    const vss = Object.keys(pinRoles).find((p) => pinRoles[p]?.role === 'vss') || '0';
    const outputs = Object.keys(pinRoles).filter((p) => pinRoles[p]?.role === 'output');
    const inputs = Object.keys(pinRoles).filter((p) => pinRoles[p]?.role === 'input');
    const output = outputs[0] || (chosen?.pins?.find((p) => ![vdd, vss].includes(p)) || 'Y');
    return { vdd, vss, output, inputs };
  }

  // drives from pinRoles (pulse params come from row OR fall back to current preset)
  function computePinDrives() {
    const drives = {};
    for (const [pin, cfg] of Object.entries(pinRoles || {})) {
      if (cfg.role !== 'input') continue;
      if (cfg.drive === 'PULSE') {
        const p = cfg.params || {};
        drives[pin] = {
          kind: 'pulse',
          v1: p.v1 ?? '0',
          v2: p.v2 ?? params.VDD,
          td: p.td ?? '0',
          tr: p.tr ?? params.TR,
          tf: p.tf ?? params.TF,
          pw: p.pw ?? params.PW,
          per: p.per ?? params.PER,
        };
      } else {
        drives[pin] = { kind: 'dc', dc: cfg.params?.dc ?? '0' };
      }
    }
    return drives;
  }

  async function runUploaded() {
    if (!netlist || !chosen || plotNodes.length === 0) return;
    setStatus({ state: 'running' });
    try {
      const roles = computeRoles();
      const pin_drives = computePinDrives();
      const body = {
        netlist,
        subckt: { name: chosen.name, pins: chosen.pins },
        plot_nodes: plotNodes,
        params: Object.fromEntries(Object.entries(params).map(([k, v]) => [k, Number(v)])),
        roles,
        pin_drives,
        hints,
      };
      const res = await simulateUploaded(body);
      setData(res);
      setStatus({ state: 'idle' });
    } catch (e) {
      setStatus({ state: 'error', error: String(e) });
    }
  }

  // apply preset → update hidden pulse params (TR/TF/PW/PER)
  function handlePresetChange(p) {
    setPulsePreset(p);
    setParams((prev) => ({
      ...prev,
      TR: p.tr,
      TF: p.tf,
      PW: p.pw,
      PER: p.per,
    }));
  }

  useEffect(() => {
    if (auto && netlist && chosen && plotNodes.length) runUploaded();
  }, [params, auto, netlist, chosen, plotNodes, pinRoles]);

  if (window.location.hostname !== "localhost") {
    if (verified === null)
      return (
        <div style={{ padding: 20, color: "white" }}>🔒 Verifying token...</div>
      );
    if (!verified)
      return <div style={{ padding: 20, color: "red" }}>❌ {error}</div>;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <ControlsBar
        params={params}
        onChange={(k, v) => setParams((p) => ({ ...p, [k]: v }))}
        onRun={chosen ? runUploaded : runLegacy}
        auto={auto}
        setAuto={setAuto}
        onPresetChange={handlePresetChange}
        onUploadFileText={(txt) => doAnalyze(txt)}
      />

      <main className="p-4 space-y-3">
        <div className="text-sm text-slate-400">
          {status.state === 'running' ? 'Simulating…' : status.state === 'error' ? 'Error' :""}
          {data.meta?.dummy ? ' (demo)' : ''}{' '}
          <span className="text-xs text-slate-600 ml-2">Model: {pulsePreset.name}</span>
        </div>

        {subckts.length > 0 && (
          <>
            <SubcktPicker
              subckts={subckts}
              chosen={chosen}
              setChosen={(s) => {
                setChosen(s);
                setPlotNodes(s ? s.pins.slice(0, 2) : []);
                setPinRoles({});
              }}
            />

            {chosen && (
              <>
                <PinRoleTable
                  pins={chosen.pins}
                  pinRoles={pinRoles}
                  setPinRoles={setPinRoles}
                  pulseDefaults={{
                    v1: '0',
                    v2: params.VDD,
                    td: '0',
                    tr: params.TR,
                    tf: params.TF,
                    pw: params.PW,
                    per: params.PER,
                  }}
                />
                <NodePicker pins={chosen?.pins || []} plotNodes={plotNodes} setPlotNodes={setPlotNodes} />
              </>
            )}
          </>
        )}

        <WaveformChart traces={traces} title={chosen ? `Subckt: ${chosen.name}` : 'Demo (INV)'} />
      </main>
    </div>
  );
}
