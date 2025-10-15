// src/components/SubcktPicker.jsx
export default function SubcktPicker({ subckts, chosen, setChosen }) {
  return (
    <div className="rounded-2xl border-[1.5px] border-emerald-500/50 bg-slate-900/40 p-3">
      <div className="flex items-center gap-3">
        <span className="text-sm text-slate-300">Subckt</span>
        <select
          className="bg-slate-900/60 border border-slate-700 rounded-xl px-3 py-2 text-sm"
          value={chosen?.name || ''}
          onChange={e=>{
            const s = subckts.find(x => x.name === e.target.value);
            setChosen(s || null);
          }}
        >
          <option value="">-- select --</option>
          {subckts.map(s => (
            <option key={s.name} value={s.name}>
              {s.name}  ({s.pins.join(', ')})
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
