import { useState } from 'react'
import RouteTimelineItem from '../widgets/RouteTimelineItem'
import { colorOf } from '../../../constants/colors'

export default function RoutesDetailTab({ result, focusedRouteId, onFocusRoute }) {
  const [open, setOpen] = useState(null)
  if (!result) return <div className="tab-body"><div className="empty">Chạy tối ưu để xem chi tiết từng xe.</div></div>
  return (
    <div className="tab-body">
      {result.routes.map((r, i) => {
        const pct = Math.min(100, Math.round((r.load / r.capacity) * 100))
        const isOpen = open === r.vehicle_id
        return (
          <div key={r.vehicle_id} className={`vehicle-card ${focusedRouteId === r.vehicle_id ? 'focused' : ''}`}>
            <div className="vehicle-head" onClick={() => { setOpen(isOpen ? null : r.vehicle_id); onFocusRoute(r.vehicle_id) }}>
              <span className="swatch" style={{ background: colorOf(i) }} />
              <b className="grow">{r.vehicle_name}</b>
              <span className="muted">{r.distance_km} km · về {r.end_time}</span>
              <span>{isOpen ? '▾' : '▸'}</span>
            </div>
            <div className="load-bar"><div className={pct > 90 ? 'full' : ''} style={{ width: `${pct}%`, background: colorOf(i) }} /></div>
            <div className="muted small">Tải {r.load}/{r.capacity} kg ({pct}%) · {r.stops.length} trạm</div>
            {isOpen && <div className="timeline">{r.stops.map((s, k) => <RouteTimelineItem key={s.order_id} stop={s} index={k + 1} color={colorOf(i)} />)}</div>}
          </div>
        )
      })}
    </div>
  )
}
