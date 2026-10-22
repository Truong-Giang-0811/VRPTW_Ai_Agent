import { useMemo, useState } from 'react'
import ManagementShell, { KpiCard } from './ManagementShell'
import LocationPicker from '../map/LocationPicker'
import AddressSearchInput from '../common/AddressSearchInput'
import { reverseGeocode, searchAddress } from '../../api/geocodeApi'
import { DEFAULT_CENTER, DEFAULT_ZOOM } from '../../constants/config'

const blank = { name: '', address: '', lat: '', lng: '', open: '07:00', close: '18:00' }

function DepotModal({ depot, onClose, onSave }) {
  const [form, setForm] = useState(() => depot ? { ...depot } : { ...blank })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [focus, setFocus] = useState(null)
  const point = form.lat !== '' && form.lng !== '' ? { lat: Number(form.lat), lng: Number(form.lng) } : null
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))
  const setPoint = (lat, lng) => setForm((f) => ({ ...f, lat: Number(lat).toFixed(6), lng: Number(lng).toFixed(6) }))

  const pick = async (lat, lng) => {
    setPoint(lat, lng)
    const addr = await reverseGeocode(lat, lng)
    if (addr) setForm((f) => ({ ...f, address: addr }))
  }
  const selectAddress = (r) => { setForm((f) => ({ ...f, address: r.label, lat: r.lat.toFixed(6), lng: r.lng.toFixed(6) })); setFocus({ lat: r.lat, lng: r.lng, zoom: 17 }) }

  const submit = async (e) => {
    e.preventDefault(); setError('')
    if (!form.name.trim() || !form.address.trim()) return setError('Tên kho và địa chỉ là bắt buộc.')
    if (!point) return setError('Hãy tìm địa chỉ hoặc chọn vị trí trên bản đồ.')
    if (form.open >= form.close) return setError('Giờ mở cửa phải trước giờ đóng cửa.')
    setSaving(true)
    try { await onSave(form) } catch (err) { setError(err.message) } finally { setSaving(false) }
  }

  return <div className="modal-backdrop" onClick={saving ? undefined : onClose}>
    <form className="modal modal-wide glass" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
      <div className="modal-head"><div><h3>{depot ? 'Chỉnh sửa điểm kho' : 'Thêm điểm kho'}</h3><div className="muted small">Điểm kho là điểm xuất phát/kết thúc của các tuyến VRPTW.</div></div><button type="button" className="icon-btn" onClick={onClose}>✕</button></div>
      <div className="order-form">
        <div className="order-form-fields">
          <label className="field-col"><span>Tên kho</span><input value={form.name} onChange={set('name')} placeholder="Kho Hà Nội" /></label>
          <div className="field-col"><span>Địa chỉ</span><AddressSearchInput value={form.address} onChange={(address) => setForm((f) => ({ ...f, address, lat: '', lng: '' }))} onSelect={selectAddress} placeholder="Tìm địa chỉ trên OpenStreetMap" hint="Chọn gợi ý hoặc click/kéo marker." /></div>
          <div className="grid-2"><label className="field-col"><span>Mở cửa</span><input type="time" value={form.open} onChange={set('open')} /></label><label className="field-col"><span>Đóng cửa</span><input type="time" value={form.close} onChange={set('close')} /></label></div>
          <div className="muted small">Tọa độ: {point ? `${form.lat}, ${form.lng}` : 'chưa chọn'}</div>
          {error && <div className="form-error">{error}</div>}
        </div>
        <LocationPicker value={point} focus={focus} center={point || DEFAULT_CENTER} zoom={point ? 16 : DEFAULT_ZOOM} onPick={pick} />
      </div>
      <div className="row modal-actions"><button type="button" className="btn" onClick={onClose}>Hủy</button><button className="btn btn-primary" disabled={saving}>{saving ? 'Đang lưu…' : 'Lưu điểm kho'}</button></div>
    </form>
  </div>
}

export default function DepotManagement({ depots, onCreate, onUpdate, onDelete, notify }) {
  const [query, setQuery] = useState('')
  const [editing, setEditing] = useState(null)
  const [open, setOpen] = useState(false)
  const filtered = useMemo(() => depots.filter((d) => `${d.name} ${d.address}`.toLowerCase().includes(query.toLowerCase())), [depots, query])
  const save = async (form) => { if (editing) await onUpdate(editing.id, form); else await onCreate(form); setOpen(false); setEditing(null) }
  const remove = async (d) => { if (!window.confirm(`Xóa điểm kho "${d.name}"? Nếu kho đang được tham chiếu bởi kế hoạch, hệ thống sẽ từ chối xóa.`)) return; try { await onDelete(d.id) } catch (e) { notify('error', e.message) } }

  return <ManagementShell title="Điểm kho" description="Quản lý các depot dùng làm điểm xuất phát và kết thúc cho bài toán định tuyến."
    actions={<button className="btn btn-primary" onClick={() => { setEditing(null); setOpen(true) }}>＋ Thêm điểm kho</button>}>
    <div className="management-kpis"><KpiCard label="Tổng điểm kho" value={depots.length} hint="Nguồn dữ liệu từ DB" /><KpiCard label="Đang hiển thị" value={filtered.length} hint="Theo bộ lọc" /><KpiCard label="Khung giờ chuẩn" value="07:00–18:00" hint="Có thể cấu hình từng kho" /></div>
    <div className="management-panel glass"><div className="toolbar"><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Tìm theo tên hoặc địa chỉ…" /><span className="muted small">{filtered.length} điểm kho</span></div>
      <div className="entity-grid">{filtered.map((d) => <article className="entity-card" key={d.id}><div className="entity-icon">🏭</div><div className="entity-main"><div className="entity-title"><strong>{d.name}</strong><span className="status-chip status-info">Kho #{d.id}</span></div><div className="muted">{d.address}</div><div className="entity-meta"><span>📍 {d.lat.toFixed(5)}, {d.lng.toFixed(5)}</span><span>🕐 {d.open}–{d.close}</span></div></div><div className="entity-actions"><button className="btn btn-sm" onClick={() => { setEditing(d); setOpen(true) }}>Sửa</button><button className="btn btn-sm danger-outline" onClick={() => remove(d)}>Xóa</button></div></article>)}{filtered.length === 0 && <div className="empty">Không có điểm kho phù hợp.</div>}</div>
    </div>
    {open && <DepotModal depot={editing} onClose={() => { setOpen(false); setEditing(null) }} onSave={save} />}
  </ManagementShell>
}
