export default function RouteTimelineItem({ stop, index, color }) {
  return (
    <div className="timeline-item">
      <div className="tl-dot" style={{ background: stop.isViolated ? '#ef4444' : color }}>{index}</div>
      <div className="grow">
        <div className="order-name">
          {stop.name} <span className="muted">· {stop.demand} kg</span>
          {stop.isViolated && <span style={{ color: '#ef4444', fontWeight: 700, marginLeft: 6, fontSize: 11 }}>⚠ Trễ hạn</span>}
        </div>
        <div className="tl-times">
          <span>Đến <b>{stop.arrival}</b></span>
          <span className={stop.waiting > 0 ? 'warn' : ''}>Chờ <b>{stop.waiting}′</b></span>
          <span>Giao <b>{stop.service_start}</b></span>
          <span>Đi <b>{stop.departure}</b></span>
          {stop.tw_end && <span className="muted">(Khung: {stop.tw_start || '08:00'} - {stop.tw_end})</span>}
        </div>
      </div>
    </div>
  )
}
