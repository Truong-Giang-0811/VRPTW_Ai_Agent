import OrderSelector from '../widgets/OrderSelector'
import AlgorithmConfig from '../widgets/AlgorithmConfig'

export default function DispatchTab({
  date, onDate, depots, depotId, onDepot, orders, selectedIds, onSelect,
  algo, onAlgo, loading, saving, hasResult, onOptimize, onSave, onAddOrder,
}) {
  return (
    <div className="tab-body">
      <div className="grid-2">
        <label className="field-col"><span>Ngày giao</span>
          <input type="date" value={date} onChange={(e) => onDate(e.target.value)} />
        </label>
        <label className="field-col"><span>Kho</span>
          <select value={depotId ?? ''} onChange={(e) => onDepot(Number(e.target.value))}>
            {depots.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </label>
      </div>
      <OrderSelector orders={orders} selectedIds={selectedIds} onChange={onSelect} onAdd={onAddOrder} />
      <AlgorithmConfig value={algo} onChange={onAlgo} />
      <div className="actions">
        <button className="btn btn-primary" disabled={loading || selectedIds.size === 0} onClick={onOptimize}>
          {loading ? '⏳ Đang tối ưu…' : '🚀 Tối ưu hóa (Preview)'}
        </button>
        <button className="btn btn-success" disabled={!hasResult || saving} onClick={onSave}>
          {saving ? 'Đang lưu…' : '💾 Xác nhận & Lưu kế hoạch'}
        </button>
      </div>
    </div>
  )
}
