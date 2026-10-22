import { colorOf } from '../../constants/colors'

export default function MapLegend({ routes, hidden, focusedId, onToggle, onFocus }) {
  if (!routes?.length) return null
  return (
    <div className="map-legend glass">
      <div className="legend-title">Tuyến xe</div>
      {routes.map((r, i) => (
        <div key={r.vehicle_id} className={`legend-row ${focusedId === r.vehicle_id ? 'active' : ''}`}>
          <input type="checkbox" checked={!hidden.has(r.vehicle_id)} onChange={() => onToggle(r.vehicle_id)} />
          <span className="swatch" style={{ background: colorOf(i) }} />
          <button className="link-btn" onClick={() => onFocus(r.vehicle_id)}>{r.vehicle_name}</button>
          <span className="muted">{r.distance_km} km</span>
        </div>
      ))}
    </div>
  )
}
