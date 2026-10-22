export default function RouteActionCard({ result, onView, onSave }) {
  return (
    <div className="action-card">
      <b>Kết quả lộ trình</b>
      <div className="muted">{result.routes.length} xe · {result.total_distance_km} km · {result.total_time_min} phút</div>
      <div className="row">
        <button className="btn btn-sm btn-primary" onClick={() => onView(result)}>🗺 Xem tuyến này</button>
        <button className="btn btn-sm btn-success" onClick={() => onSave(result)}>💾 Lưu vào DB</button>
      </div>
    </div>
  )
}
