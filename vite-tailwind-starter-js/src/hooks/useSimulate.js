// src/hooks/useSimulate.js
import axios from 'axios';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

function dummySim(params) {
  const VDD = parseFloat(params.VDD ?? '1.2');
  const PER = parseFloat(params.PER ?? '1e-9');
  const PW  = parseFloat(params.PW  ?? '5e-10');
  const TR  = parseFloat(params.TR  ?? '1e-11');
  const tau = Math.max(1e-11, TR * 2);
  const TSTOP = parseFloat(params.TSTOP ?? '3e-9');
  const N = 2000;
  const dt = TSTOP / N;
  const t = [], va = [], vy = [];
  for (let i=0;i<N;i++) {
    const time = i * dt;
    const phase = time % PER;
    const a = phase < PW ? VDD : 0;
    t.push(time); va.push(a);
    const target = a > VDD/2 ? 0 : VDD;
    const last = vy.length ? vy[vy.length-1] : (VDD - a);
    const dy = (target - last) * (1 - Math.exp(-dt / tau));
    vy.push(last + dy);
  }
  return { time: t, waveforms: { 'v(a)': va, 'v(y)': vy }, meta: { points: N, dummy: true } };
}

export function useSimulate() {
  let currentController = null;
  let lastRunId = 0;

  async function simulate(params, { signal } = {}) {
    const base = import.meta.env.VITE_API_URL;
    if (!base) {
      await sleep(150);
      return dummySim(params);
    }
    const body = { params, nodes: ['a','y'] };
    try {
      const res = await axios.post(`${base}/simulate`, body, {
        signal,
        headers: { 'Content-Type': 'application/json' },
        timeout: 20000,
      });
      return res.data;
    } catch (e) {
      return { ...dummySim(params), error: e.message || 'simulate failed (fallback to dummy)' };
    }
  }

  function runDebounced(setters, params, auto=false) {
    const runId = ++lastRunId;
    if (currentController) currentController.abort();
    const controller = new AbortController();
    currentController = controller;

    const doRun = async () => {
      try {
        setters.setStatus({ state: 'running', runId });
        const data = await simulate(params, { signal: controller.signal });
        if (runId !== lastRunId) return;
        setters.setData(data);
        setters.setStatus({ state: 'idle', runId });
      } catch (err) {
        if (axios.isCancel(err)) return;
        setters.setStatus({ state: 'error', runId, error: String(err) });
      }
    };

    if (auto) {
      clearTimeout(runDebounced._t);
      runDebounced._t = setTimeout(doRun, 300);
    } else {
      doRun();
    }
  }

  return { runDebounced };
}

/* -------- NEW: uploaded .cir flow -------- */

export function useUploadedSim() {
  async function analyze(netlist, hints) {
    const base = import.meta.env.VITE_API_URL;
    if (!base) throw new Error('VITE_API_URL not set');
    const res = await axios.post(`${base}/analyze`, { netlist, hints }, {
      headers: { 'Content-Type': 'application/json' }, timeout: 15000
    });
    return res.data; // { subckts: [{ name, pins }] }
  }

  // UPDATED: now accepts pin_drives and forwards it to backend
  async function simulateUploaded({ netlist, subckt, plot_nodes, params, hints, roles, pin_drives }) {
    const base = import.meta.env.VITE_API_URL;
    if (!base) throw new Error('VITE_API_URL not set');
    const body = { netlist, subckt, plot_nodes, params, hints, roles, pin_drives };
    const res = await axios.post(`${base}/simulate_uploaded`, body, {
      headers: { 'Content-Type': 'application/json' }, timeout: 30000
    });
    return res.data; // { time, waveforms, meta }
  }

  return { analyze, simulateUploaded };
}
