import { useCallback, useEffect, useState } from 'react'
import * as ordersApi from '../../api/ordersApi'
import ManagementShell, { KpiCard } from './ManagementShell'
import LocationPicker from '../map/LocationPicker'
import AddressSearchInput from '../common/AddressSearchInput'
import { reverseGeocode } from '../../api/geocodeApi'
import { DEFAULT_CENTER, DEFAULT_ZOOM } from '../../constants/config'

const statuses = { pending: 'Chờ xử lý', assigned: 'Đã phân xe', delivering: 'Đang giao', delivered: 'Đã giao', cancelled: 'Đã hủy' }
const blank = { code: '', name: '', address: '', lat: '', lng: '', demand: '', service_min: '10', delivery_date: new Date().toISOString().slice(0, 10), tw_start: '08:00', tw_end: '17:00', status: 'pending' }

function OrderModal({ order, onClose, onSave }) {
  const [form, setForm] = useState(() => order ? { ...order } : { ...blank, code: `ORD-${Date.now().toString().slice(-8)}` })
  const [error, setError] = useState(''); const [saving, setSaving] = useState(false); const [focus, setFocus] = useState(null)
  const point = form.lat !== '' && form.lng !== '' ? { lat: Number(form.lat), lng: Number(form.lng) } : null
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const pick = async (lat, lng) => { setForm((f) => ({ ...f, lat: lat.toFixed(6), lng: lng.toFixed(6), address: '' })); const a = await reverseGeocode(lat, lng); if (a) setForm((f) => ({ ...f, address: a })) }
  const select = (r) => { setForm((f) => ({ ...f, address: r.label, lat: r.lat.toFixed(6), lng: r.lng.toFixed(6) })); setFocus({ lat: r.lat, lng: r.lng, zoom: 17 }) }
  const submit = async (e) => { e.preventDefault(); setError(''); if (!form.name.trim() || !form.address.trim() || !point || !(Number(form.demand) > 0) || !form.delivery_date || form.tw_start >= form.tw_end) return setError('Kiểm tra khách hàng, địa chỉ/tọa độ, khối lượng và khung giờ.'); setSaving(true); try { await onSave(form) } catch (err) { setError(err.message) } finally { setSaving(false) } }
  return <div className="modal-backdrop" onClick={saving ? undefined : onClose}><form className="modal modal-wide glass" onClick={(e) => e.stopPropagation()} onSubmit={submit}><div className="modal-head"><div><h3>{order ? 'Chỉnh sửa đơn hàng' : 'Tiếp nhận đơn hàng'}</h3><div className="muted small">Địa chỉ và tọa độ được đồng bộ qua OpenStreetMap.</div></div><button type="button" className="icon-btn" onClick={onClose}>✕</button></div><div className="order-form"><div className="order-form-fields"><div className="grid-2"><label className="field-col"><span>Mã đơn</span><input value={form.code} disabled={!!order} onChange={set('code')} /></label><label className="field-col"><span>Ngày giao</span><input type="date" value={form.delivery_date} onChange={set('delivery_date')} /></label></div><label className="field-col"><span>Khách hàng</span><input value={form.name} onChange={set('name')} /></label><div className="field-col"><span>Địa chỉ giao</span><AddressSearchInput value={form.address} onChange={(address) => setForm((f) => ({ ...f, address, lat: '', lng: '' }))} onSelect={select} placeholder="Nhập địa chỉ khách hàng…" hint="Chọn gợi ý hoặc click/kéo marker." /></div><div className="grid-2"><label className="field-col"><span>Khối lượng (kg)</span><input type="number" min="0.1" value={form.demand} onChange={set('demand')} /></label><label className="field-col"><span>Phục vụ (phút)</span><input type="number" min="0" value={form.service_min} onChange={set('service_min')} /></label></div><div className="grid-2"><label className="field-col"><span>Mở cửa</span><input type="time" value={form.tw_start} onChange={set('tw_start')} /></label><label className="field-col"><span>Đóng cửa</span><input type="time" value={form.tw_end} onChange={set('tw_end')} /></label></div>{order && <label className="field-col"><span>Trạng thái</span><select value={form.status} onChange={set('status')}>{Object.entries(statuses).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>}<div className="muted small">Tọa độ: {point ? `${form.lat}, ${form.lng}` : 'chưa chọn'}</div>{error && <div className="form-error">{error}</div>}</div><LocationPicker value={point} focus={focus} center={point || DEFAULT_CENTER} zoom={point ? 16 : DEFAULT_ZOOM} onPick={pick} /></div><div className="row modal-actions"><button type="button" className="btn" onClick={onClose}>Hủy</button><button className="btn btn-primary" disabled={saving}>{saving ? 'Đang lưu…' : order ? 'Cập nhật đơn' : 'Tiếp nhận đơn'}</button></div></form></div>
}

export default function OrderManagement({ orders, onCreate, onUpdate, onDelete, onStatus, notify }) {
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('all')
  const [date, setDate] = useState('')
  const [editing, setEditing] = useState(null)
  const [open, setOpen] = useState(false)
  const [page, setPage] = useState(0)
  const [pageData, setPageData] = useState({ items: [], total: 0, pages: 0 })
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState('')
  const pageSize = 25

  const loadPage = useCallback(async () => {
    setLoading(true)
    setLoadError('')
    try {
      const result = await ordersApi.listPage({
        skip: page * pageSize,
        limit: pageSize,
        delivery_date: date || undefined,
        status: status === 'all' ? undefined : status,
        q: query.trim() || undefined,
      })
      setPageData(result)
      // If the current page became invalid after delete/filter, move to the last valid page.
      const lastPage = Math.max(0, result.pages - 1)
      if (page > lastPage) setPage(lastPage)
    } catch (error) {
      setLoadError(error.message || 'Không tải được danh sách đơn hàng.')
    } finally {
      setLoading(false)
    }
  }, [page, date, status, query])

  useEffect(() => { loadPage() }, [loadPage])

  const refreshAfterMutation = async (action) => {
    await action()
    await loadPage()
  }
  const pending = pageData.items.filter((o) => o.status === 'pending').length
  const assigned = pageData.items.filter((o) => o.status === 'assigned').length
  const weight = pageData.items.reduce((sum, o) => sum + o.demand, 0)
  const save = async (form) => {
    if (editing) await refreshAfterMutation(() => onUpdate(editing.id, form))
    else await refreshAfterMutation(() => onCreate(form))
    setOpen(false)
    setEditing(null)
  }
  const remove = async (o) => {
    if (!window.confirm(`Xóa đơn ${o.code}?`)) return
    try { await refreshAfterMutation(() => onDelete(o.id)) }
    catch (e) { notify('error', e.message) }
  }
  const statusChange = async (o, value) => {
    try { await refreshAfterMutation(() => onStatus(o.id, value)) }
    catch (e) { notify('error', e.message) }
  }
  const updateFilter = (setter, value) => { setter(value); setPage(0) }
  const firstRow = pageData.total === 0 ? 0 : page * pageSize + 1
  const lastRow = Math.min((page + 1) * pageSize, pageData.total)

  return <ManagementShell title="Đơn đã nhận" description="Tiếp nhận, kiểm tra và theo dõi đơn giao hàng trước khi đưa vào bài toán VRPTW."
    actions={<button className="btn btn-primary" onClick={() => { setEditing(null); setOpen(true) }}>＋ Tiếp nhận đơn</button>}>
    <div className="management-kpis">
      <KpiCard label="Tổng đơn phù hợp" value={pageData.total} hint="Tổng số kết quả sau bộ lọc phía máy chủ" />
      <KpiCard label="Chờ phân tuyến (trang này)" value={pending} hint={`${assigned} đơn đã phân xe trên trang hiện tại`} />
      <KpiCard label="Tổng nhu cầu (trang này)" value={`${weight.toLocaleString('vi-VN')} kg`} hint="Khối lượng của các đơn trên trang hiện tại" />
    </div>
    <div className="management-panel glass">
      <div className="toolbar toolbar-orders">
        <input value={query} onChange={(e) => updateFilter(setQuery, e.target.value)} placeholder="Tìm mã đơn, khách hàng, địa chỉ…" />
        <select value={status} onChange={(e) => updateFilter(setStatus, e.target.value)}>
          <option value="all">Tất cả trạng thái</option>
          {Object.entries(statuses).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <input type="date" value={date} onChange={(e) => updateFilter(setDate, e.target.value)} />
        <span className="muted small">{pageData.total} đơn</span>
      </div>
      {loadError && <div className="form-error">{loadError}</div>}
      <div className="table-wrap">
        <table className="management-table">
          <thead><tr><th>Mã đơn</th><th>Khách hàng</th><th>Giao ngày</th><th>Nhu cầu</th><th>Khung giờ</th><th>Trạng thái</th><th></th></tr></thead>
          <tbody>
            {pageData.items.map((o) => <tr key={o.id}>
              <td><strong>{o.code}</strong><div className="muted small">#{o.id}</div></td>
              <td><div>{o.name}</div><div className="muted small ellipsis" title={o.address}>{o.address}</div></td>
              <td>{o.delivery_date}</td><td>{o.demand.toLocaleString('vi-VN')} kg</td><td>{o.tw_start}–{o.tw_end}</td>
              <td><select className={`status-select status-${o.status}`} value={o.status} onChange={(e) => statusChange(o, e.target.value)}>{Object.entries(statuses).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></td>
              <td className="actions-cell"><button className="btn btn-sm" onClick={() => { setEditing(o); setOpen(true) }}>Sửa</button><button className="btn btn-sm danger-outline" onClick={() => remove(o)}>Xóa</button></td>
            </tr>)}
          </tbody>
        </table>
        {loading && <div className="empty">Đang tải đơn hàng…</div>}
        {!loading && !loadError && pageData.items.length === 0 && <div className="empty">Không có đơn phù hợp.</div>}
      </div>
      <div className="toolbar" style={{ justifyContent: 'space-between', alignItems: 'center', marginTop: 12 }}>
        <span className="muted small">Hiển thị {firstRow}–{lastRow} / {pageData.total}</span>
        <div className="row" style={{ gap: 8, alignItems: 'center' }}>
          <button className="btn btn-sm" disabled={page <= 0 || loading} onClick={() => setPage(0)}>Đầu</button>
          <button className="btn btn-sm" disabled={page <= 0 || loading} onClick={() => setPage((p) => Math.max(0, p - 1))}>Trước</button>
          <span className="small">Trang {pageData.pages === 0 ? 0 : page + 1} / {pageData.pages}</span>
          <button className="btn btn-sm" disabled={page + 1 >= pageData.pages || loading} onClick={() => setPage((p) => p + 1)}>Sau</button>
          <button className="btn btn-sm" disabled={page + 1 >= pageData.pages || loading} onClick={() => setPage(Math.max(0, pageData.pages - 1))}>Cuối</button>
        </div>
      </div>
    </div>
    {open && <OrderModal order={editing} onClose={() => { setOpen(false); setEditing(null) }} onSave={save} />}
  </ManagementShell>
}
