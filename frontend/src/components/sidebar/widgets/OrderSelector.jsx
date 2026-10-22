export default function OrderSelector({ orders, selectedIds, onChange, onAdd }) {
  const toggle = (id) => {
    const next = new Set(selectedIds)
    next.has(id) ? next.delete(id) : next.add(id)
    onChange(next)
  }
  const allSelected = orders.length > 0 && selectedIds.size === orders.length
  return (
    <div className="order-selector">
      <div className="row between">
        <b>Đơn hàng pending ({selectedIds.size}/{orders.length})</b>
        <div className="row">
          <button className="link-btn" onClick={onAdd}>＋ Thêm đơn</button>
          <button className="link-btn" onClick={() => onChange(allSelected ? new Set() : new Set(orders.map((o) => o.id)))}>
          {allSelected ? 'Bỏ chọn' : 'Chọn tất cả'}
          </button>
        </div>
      </div>
      <div className="order-list">
        {orders.length === 0 && <div className="empty">Chưa có đơn nào — bấm “＋ Thêm đơn” để tạo</div>}
        {orders.map((o) => (
          <label key={o.id} className={`order-item ${selectedIds.has(o.id) ? 'selected' : ''}`}>
            <input type="checkbox" checked={selectedIds.has(o.id)} onChange={() => toggle(o.id)} />
            <div className="grow">
              <div className="order-name">#{o.id} · {o.customer}</div>
              <div className="muted">{o.demand} kg · {o.tw_start}–{o.tw_end} · phục vụ {o.service_min}′</div>
            </div>
          </label>
        ))}
      </div>
    </div>
  )
}
