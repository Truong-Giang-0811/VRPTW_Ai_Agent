import StatBadge from './StatBadge'

// data: { distance: result, spatiotemporal: result } | null
export default function CompareModal({ open, loading, data, onClose, onPick }) {
  if (!open) return null
  const cols = data ? [['Distance', data.distance, 'distance'], ['Spatiotemporal', data.spatiotemporal, 'spatiotemporal']] : []
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal glass" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head"><h3>So sánh chế độ tối ưu</h3><button className="icon-btn" onClick={onClose}>✕</button></div>
        {loading && <div className="empty">Đang chạy 2 chế độ…</div>}
        {data && (
          <div className="compare-grid">
            {cols.map(([title, r, key]) => (
              <div key={key} className="compare-col">
                <h4>{title}</h4>
                <StatBadge icon="📏" label="Tổng quãng đường" value={`${r.total_distance_km} km`} />
                <StatBadge icon="⏱" label="Tổng thời gian" value={`${r.total_time_min} phút`} />
                <StatBadge icon="🚚" label="Số xe" value={r.routes.length} />
                <StatBadge icon="⚠️" label="Vi phạm khung giờ" value={r.violations ?? 0} tone={r.violations ? 'danger' : 'ok'} />
                <button className="btn btn-primary" onClick={() => { onPick(r); onClose() }}>Dùng kết quả này</button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
