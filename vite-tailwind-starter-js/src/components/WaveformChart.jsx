import Plot from 'react-plotly.js';

export default function WaveformChart({ traces, title = 'Waveforms' }) {
  return (
    <div className="h-[70vh] w-full rounded-2xl border border-emerald-500/40 bg-black/30 p-3">
      <Plot
        data={traces.map(t => ({
          x: t.x, y: t.y, name: t.name,
          type: 'scatter', mode: 'lines', line: { width: 1 },
        }))}
        layout={{
          title: { text: title, font: { size: 14 } },
          paper_bgcolor: '#0b1220',
          plot_bgcolor: '#0b1220',
          font: { color: '#e5e7eb' },
          margin: { l: 60, r: 20, t: 30, b: 40 },
          xaxis: { title: 'time (s)' },
          yaxis: { title: 'V (V)' },
          legend: { orientation: 'h', x: 0.5, xanchor: 'center', y: 1.1 }
        }}
        useResizeHandler
        style={{ width: '100%', height: '100%' }}
        config={{ displayModeBar: false, responsive: true }}
      />
    </div>
  );
}
