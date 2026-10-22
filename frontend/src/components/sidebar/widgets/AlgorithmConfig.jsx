const FIELDS = [
  ['population', 'Quần thể (GA)', 10, 500, 10],
  ['generations', 'Số thế hệ', 10, 1000, 10],
  ['mutation_rate', 'Tỉ lệ đột biến', 0, 1, 0.01],
  ['capacity', 'Tải trọng xe (kg)', 100, 5000, 50],
  ['time_weight', 'Trọng số thời gian', 0, 1, 0.05],
]

export default function AlgorithmConfig({ value, onChange }) {
  const set = (k, v) => onChange({ ...value, [k]: v })
  return (
    <details className="algo-config">
      <summary>⚙ Cấu hình thuật toán</summary>
      <div className="seg">
        {['distance', 'spatiotemporal'].map((m) => (
          <button key={m} className={value.mode === m ? 'on' : ''} onClick={() => set('mode', m)}>{m === 'distance' ? 'Distance' : 'Spatiotemporal'}</button>
        ))}
      </div>
      {FIELDS.map(([k, label, min, max, step]) => (
        <label key={k} className="field">
          <span>{label}</span>
          <input type="range" min={min} max={max} step={step} value={value[k]} onChange={(e) => set(k, Number(e.target.value))} />
          <b>{value[k]}</b>
        </label>
      ))}
    </details>
  )
}
