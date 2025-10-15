// src/components/ControlsBar.jsx
import UploadIconButton from "./UploadIconButton.jsx";

const PRESETS = [
  { name: "Standard", tr: "1e-11", tf: "1e-11", pw: "5e-10",  per: "1e-9"  },
  { name: "Slow IO",  tr: "5e-11", tf: "5e-11", pw: "1e-9",   per: "2e-9"  },
  { name: "Fast IO",  tr: "5e-12", tf: "5e-12", pw: "2.5e-10", per: "5e-10" },
  { name: "Ultra",    tr: "1e-12", tf: "1e-12", pw: "1e-10",  per: "2e-10" },
];

function SmallNum({ label, value, onChange, width = "w-28" }) {
  return (
    <label className="flex items-center gap-2 text-xs text-slate-300">
      <span className="opacity-70">{label}</span>
      <input
        type="text"
        inputMode="decimal"
        value={value ?? ""}
        onChange={(e) => onChange?.(e.target.value)}
        className={`h-9 ${width} rounded-lg bg-slate-900/70 border border-slate-700/70 px-2.5
                    font-mono text-[13px] outline-none focus:ring-2 focus:ring-sky-600/40
                    focus:border-sky-600/40 hover:border-slate-600`}
      />
    </label>
  );
}

export default function ControlsBar({
  params,                 // { VDD, CLOAD, TSTEP, TSTOP, TEMP, TR/TF/PW/PER hidden }
  onChange,               // (key, value) => void
  onRun,                  // () => void
  auto, setAuto,          // boolean, setter
  onPresetChange,         // (presetObj) => void    // NEW
  onUploadFileText,       // (fileText) => void     // NEW
}) {
  return (
   <header className="sticky top-0 z-40 bg-slate-950/75 ... border-b-[1.5px] border-emerald-500/50">
      <div className="mx-auto max-w-[1400px] px-4 py-3 flex flex-wrap items-center gap-3">
        {/* Left: run & auto */}
        <div className="flex items-center gap-3">
          <button
            onClick={onRun}
            className="h-9 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm shadow"
          >
            Run
          </button>

          <label className="flex items-center gap-2 text-xs text-slate-300">
            <input
              type="checkbox"
              checked={auto}
              onChange={(e) => setAuto(e.target.checked)}
              className="accent-sky-500"
            />
            Auto
          </label>
        </div>

        {/* Middle: non-pulse globals only */}
        <div className="flex items-center gap-4 flex-wrap">
          <SmallNum label="VDD"   value={params.VDD}   onChange={(v)=>onChange("VDD", v)} />
          <SmallNum label="Cload" value={params.CLOAD} onChange={(v)=>onChange("CLOAD", v)} />
          <SmallNum label="TSTOP" value={params.TSTOP} onChange={(v)=>onChange("TSTOP", v)} />
          <SmallNum label="TSTEP" value={params.TSTEP} onChange={(v)=>onChange("TSTEP", v)} />
          <SmallNum label="TEMP"  value={params.TEMP}  onChange={(v)=>onChange("TEMP", v)}  />
        </div>

        {/* Right: PULSE Model + Upload */}
        <div className="ml-auto flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-slate-300">
            <span className="opacity-70">Model</span>
            <select
              onChange={(e) => {
                const p = PRESETS.find(x => x.name === e.target.value) || PRESETS[0];
                onPresetChange?.(p);          // updates hidden TR/TF/PW/PER in App.jsx
              }}
              className="h-9 rounded-lg bg-slate-900/70 border border-slate-700/70 px-2.5 pr-7 text-[13px]
                         outline-none hover:border-slate-600 focus:ring-2 focus:ring-sky-600/40 focus:border-sky-600/40"
              defaultValue={PRESETS[0].name}
            >
              {PRESETS.map(p => <option key={p.name} value={p.name}>{p.name}</option>)}
            </select>
          </label>

          {/* upload icon lives in the header now */}
          <UploadIconButton onFileText={onUploadFileText} />
        </div>
      </div>
    </header>
  );
}
