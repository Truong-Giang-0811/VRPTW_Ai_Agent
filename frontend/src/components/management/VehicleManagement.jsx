import { useMemo, useState } from 'react'
import ManagementShell, { KpiCard } from './ManagementShell'

const blank = { code: '', name: '', capacity: '', status: 'available' }
const labels = { available: 'Sẵn sàng', busy: 'Đang chạy', maintenance: 'Bảo trì', inactive: 'Ngừng hoạt động' }

function VehicleModal({ vehicle, onClose, onSave }) {
  const [form, setForm] = useState(vehicle ? { ...vehicle } : blank)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const submit = async (e) => { e.preventDefault(); setError(''); if (!form.code.trim() || !form.name.trim() || !(Number(form.capacity) > 0)) return setError('Mã xe, tên xe và tải trọng > 0 là bắt buộc.'); setSaving(true); try { await onSave(form) } catch (err) { setError(err.message) } finally { setSaving(false) } }
  return <div className="modal-backdrop" onClick={saving ? undefined : onClose}><form className="modal glass" onClick={(e) => e.stopPropagation()} onSubmit={submit}><div className="modal-head"><h3>{vehicle ? 'Chỉnh sửa xe' : 'Thêm xe'}</h3><button type="button" className="icon-btn" onClick={onClose}>✕</button></div><div className="management-form"><label className="field-col"><span>Mã xe</span><input value={form.code} onChange={set('code')} disabled={!!vehicle} placeholder="XE-001" /></label><label className="field-col"><span>Tên xe</span><input value={form.name} onChange={set('name')} placeholder="Xe tải 1" /></label><label className="field-col"><span>Tải trọng (kg)</span><input type="number" min="1" step="0.1" value={form.capacity} onChange={set('capacity')} /></label><label className="field-col"><span>Trạng thái</span><select value={form.status} onChange={set('status')}><option value="available">Sẵn sàng</option><option value="busy">Đang chạy</option><option value="maintenance">Bảo trì</option><option value="inactive">Ngừng hoạt động</option></select></label>{error && <div className="form-error">{error}</div>}</div><div className="row modal-actions"><button type="button" className="btn" onClick={onClose}>Hủy</button><button className="btn btn-primary" disabled={saving}>{saving ? 'Đang lưu…' : 'Lưu xe'}</button></div></form></div>
}

export default function VehicleManagement({ vehicles, onCreate, onUpdate, onDelete, notify }) {
  const [query, setQuery] = useState(''); const [status, setStatus] = useState('all'); const [editing, setEditing] = useState(null); const [open, setOpen] = useState(false)
  const filtered = useMemo(() => vehicles.filter((v) => (status === 'all' || v.status === status) && `${v.code} ${v.name}`.toLowerCase().includes(query.toLowerCase())), [vehicles, status, query])
  const available = vehicles.filter((v) => v.status === 'available').length; const capacity = vehicles.reduce((s, v) => s + v.capacity, 0)
  const save = async (form) => { if (editing) await onUpdate(editing.id, form); else await onCreate(form); setOpen(false); setEditing(null) }
  const remove = async (v) => { if (!window.confirm(`Xóa xe ${v.code}?`)) return; try { await onDelete(v.id) } catch (e) { notify('error', e.message) } }
  return <ManagementShell title="Quản lý xe" description="Quản lý đội xe, tải trọng và trạng thái sẵn sàng trước khi phân tuyến."
    actions={<button className="btn btn-primary" onClick={() => { setEditing(null); setOpen(true) }}>＋ Thêm xe</button>}>
    <div className="management-kpis"><KpiCard label="Tổng xe" value={vehicles.length} hint="Phương tiện trong DB" /><KpiCard label="Sẵn sàng" value={available} hint="Có thể tham gia tối ưu" /><KpiCard label="Tổng tải trọng" value={`${capacity.toLocaleString('vi-VN')} kg`} hint="Tất cả phương tiện" /></div>
    <div className="management-panel glass"><div className="toolbar"><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Tìm theo mã hoặc tên xe…" /><select value={status} onChange={(e) => setStatus(e.target.value)}><option value="all">Tất cả trạng thái</option><option value="available">Sẵn sàng</option><option value="busy">Đang chạy</option><option value="maintenance">Bảo trì</option><option value="inactive">Ngừng hoạt động</option></select><span className="muted small">{filtered.length} xe</span></div><div className="table-wrap"><table className="management-table"><thead><tr><th>Mã xe</th><th>Phương tiện</th><th>Tải trọng</th><th>Trạng thái</th><th></th></tr></thead><tbody>{filtered.map((v) => <tr key={v.id}><td><strong>{v.code}</strong></td><td>{v.name}</td><td>{v.capacity.toLocaleString('vi-VN')} kg</td><td><span className={`status-chip status-${v.status}`}>{labels[v.status] || v.status}</span></td><td className="actions-cell"><button className="btn btn-sm" onClick={() => { setEditing(v); setOpen(true) }}>Sửa</button><button className="btn btn-sm danger-outline" onClick={() => remove(v)}>Xóa</button></td></tr>)}</tbody></table>{filtered.length === 0 && <div className="empty">Không có xe phù hợp.</div>}</div></div>
    {open && <VehicleModal vehicle={editing} onClose={() => { setOpen(false); setEditing(null) }} onSave={save} />}
  </ManagementShell>
}
