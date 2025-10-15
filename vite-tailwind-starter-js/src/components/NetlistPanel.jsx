// src/components/NetlistPanel.jsx
import { useRef, useState } from 'react';

export default function NetlistPanel({ onAnalyze }) {
  const [fileInfo, setFileInfo] = useState(null);
  const [vddHint, setVddHint] = useState('VDD,VCC');
  const [vssHint, setVssHint] = useState('VSS,GND,0');
  const [outsHint, setOutsHint] = useState('Y,OUT,Z,Q');
  const inputRef = useRef(null);

  const buildHints = () => ({
    supplies: {
      vdd: vddHint.split(',').map(s=>s.trim()).filter(Boolean),
      vss: vssHint.split(',').map(s=>s.trim()).filter(Boolean),
    },
    outputs: outsHint.split(',').map(s=>s.trim()).filter(Boolean),
  });

  async function handleFiles(files) {
    if (!files || !files.length) return;
    const file = files[0];
    setFileInfo({ name: file.name, size: file.size });
    const text = await file.text();              // <-- read as text in browser
    onAnalyze(text, buildHints());               // <-- backend /analyze ko bhej do
  }

  function onDrop(e) {
    e.preventDefault();
    handleFiles(e.dataTransfer.files);
  }

  return (
    <div className="p-3 rounded-2xl border border-slate-700/60 bg-slate-900/40 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">Upload .cir file</h3>
        <div className="text-xs text-slate-400">{fileInfo ? `${fileInfo.name} (${Math.ceil(fileInfo.size/1024)} KB)` : 'no file selected'}</div>
      </div>

      {/* Dropzone + file input */}
      <div
        onDragOver={e=>e.preventDefault()}
        onDrop={onDrop}
        className="w-full rounded-xl bg-slate-950/60 border border-dashed border-slate-600 p-6 text-center"
      >
        <div className="text-sm text-slate-300 mb-3">Drag & drop your .cir here</div>
        <input
          ref={inputRef}
          type="file"
          accept=".cir,.sp,.spi,.spice,.txt"
          className="hidden"
          onChange={e=>handleFiles(e.target.files)}
        />
        <button
          className="rounded-xl px-3 py-1.5 bg-emerald-500/90 text-emerald-900 font-semibold hover:bg-emerald-400"
          onClick={()=>inputRef.current?.click()}
        >
          Choose file
        </button>
      </div>

      {/* Alias hints (optional) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <label className="text-xs text-slate-300">
          VDD aliases (csv)
          <input className="mt-1 w-full rounded-xl bg-slate-900/60 border border-slate-700 px-3 py-2 text-sm"
                 value={vddHint} onChange={e=>setVddHint(e.target.value)} />
        </label>
        <label className="text-xs text-slate-300">
          VSS/GND aliases (csv)
          <input className="mt-1 w-full rounded-xl bg-slate-900/60 border border-slate-700 px-3 py-2 text-sm"
                 value={vssHint} onChange={e=>setVssHint(e.target.value)} />
        </label>
        <label className="text-xs text-slate-300">
          Output pin hints (csv)
          <input className="mt-1 w-full rounded-xl bg-slate-900/60 border border-slate-700 px-3 py-2 text-sm"
                 value={outsHint} onChange={e=>setOutsHint(e.target.value)} />
        </label>
      </div>
    </div>
  );
}
