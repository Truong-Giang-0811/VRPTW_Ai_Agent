export default function HistoryTab({ plans, loading, onLoadPlan }) {
  return (
    <div className="tab-body">
      {loading && <div className="empty">Đang tải…</div>}
      {!loading && plans.length === 0 && <div className="empty">Chưa có kế hoạch nào được lưu.</div>}
      {plans.map((p) => (
        <div key={p.id} className="history-item">
          <div className="grow">
            <b>Plan #{p.id} · {p.date}</b>
            <div className="muted">{p.depot} · {p.vehicles} xe · {p.orders} đơn · {p.distance_km} km · {p.mode}</div>
          </div>
          <button className="btn btn-sm" onClick={() => onLoadPlan(p)}>Xem lại</button>
        </div>
      ))}
    </div>
  )
}
