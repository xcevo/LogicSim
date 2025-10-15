// src/components/NodePicker.jsx
import { useMemo } from "react";

function Checkbox({ checked, onChange }) {
  return (
    <input
      type="checkbox"
      className="h-3.5 w-3.5 accent-blue-500"
      checked={!!checked}
      onChange={(e) => onChange(e.target.checked)}
    />
  );
}

export default function NodePicker({ pins = [], plotNodes = [], setPlotNodes }) {
  const orderedPins = useMemo(() => {
    const seen = new Set();
    return pins.filter((p) => (seen.has(p) ? false : (seen.add(p), true)));
  }, [pins]);

  const isChecked = (p) => plotNodes.includes(p);
  const toggle = (pin, on) => {
    setPlotNodes((prev) => {
      const set = new Set(prev);
      if (on) set.add(pin);
      else set.delete(pin);
      return Array.from(set);
    });
  };

  const selectAll = () => setPlotNodes(orderedPins);
  const selectNone = () => setPlotNodes([]);

  return (
    <div className="rounded-2xl border-[1.5px] border-emerald-500/50 bg-slate-900/40 p-3">
      {/* header (unchanged width) */}
      <div className="flex items-center justify-between px-4 py-2.5">
        <div className="text-[13px] font-medium text-slate-200">Plot nodes</div>
        <div className="flex items-center gap-2">
          <button
            onClick={selectAll}
            className="text-[11px] px-2.5 py-1 rounded-md border border-slate-700 text-slate-200 hover:bg-slate-800"
          >
            All
          </button>
          <button
            onClick={selectNone}
            className="text-[11px] px-2.5 py-1 rounded-md border border-slate-700 text-slate-200 hover:bg-slate-800"
          >
            None
          </button>
        </div>
      </div>

      {/* chips — smaller everything */}
      <div className="px-3 pb-3">
        <div
          className="
            grid gap-1.5
            [grid-template-columns:repeat(auto-fill,minmax(120px,1fr))]
          "
        >
          {orderedPins.map((pin) => (
            <label
              key={pin}
              className="flex items-center gap-1.5 rounded-lg border border-slate-800/80 bg-slate-900/60 px-2 py-1.5 text-[12px] text-slate-200 hover:border-slate-700 transition"
              title={`v(${pin})`}
            >
              <Checkbox checked={isChecked(pin)} onChange={(on) => toggle(pin, on)} />
              <span className="font-mono tracking-tight">v({pin})</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
