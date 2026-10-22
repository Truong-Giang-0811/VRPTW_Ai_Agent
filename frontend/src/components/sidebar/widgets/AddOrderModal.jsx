import { useRef, useState } from 'react'
import LocationPicker from '../../map/LocationPicker'
import AddressSearchInput from '../../common/AddressSearchInput'
import { reverseGeocode, searchAddress } from '../../../api/geocodeApi'
import { emptyOrderForm, validateOrderForm } from '../../../utils/orderForm'
import { DEFAULT_CENTER, DEFAULT_ZOOM } from '../../../constants/config'

// Vỏ modal: chỉ mount form khi mở, nên mỗi lần mở form được khởi tạo mới (mã đơn mới, ngày đang chọn)
export default function AddOrderModal({ open, ...props }) {
  return open ? <AddOrderForm {...props} /> : null
}

// onSubmit(form) trả Promise; reject => hiển thị lỗi tại form, không đóng modal.
function AddOrderForm({ defaultDate, anchor, onClose, onSubmit }) {
  const [form, setForm] = useState(() => emptyOrderForm(defaultDate))
  const [errors, setErrors] = useState({})
  const [submitError, setSubmitError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [geocoding, setGeocoding] = useState(false)
  const [focus, setFocus] = useState(null)
  const geoAbort = useRef(null)

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))
  const hasPoint = form.lat !== '' && form.lng !== ''
  const point = hasPoint ? { lat: Number(form.lat), lng: Number(form.lng) } : null

  const setPoint = (lat, lng) => setForm((f) => ({ ...f, lat: Number(lat).toFixed(6), lng: Number(lng).toFixed(6) }))

  // Click/kéo marker: toạ độ đổi ngay, địa chỉ luôn được cập nhật theo điểm mới (reverse geocode OSM)
  const handlePick = async (lat, lng) => {
    setPoint(lat, lng)
    setErrors((er) => ({ ...er, location: undefined }))
    geoAbort.current?.abort()
    geoAbort.current = new AbortController()
    const { signal } = geoAbort.current
    setGeocoding(true)
    setForm((f) => ({ ...f, address: '' })) // tránh giữ địa chỉ cũ lệch với điểm mới
    const addr = await reverseGeocode(lat, lng, signal)
    if (signal.aborted) return // đã có click mới hơn
    setGeocoding(false)
    setForm((f) => ({ ...f, address: addr || '' }))
    if (!addr) setErrors((er) => ({ ...er, address: 'Không lấy được địa chỉ cho điểm này, hãy nhập tay' }))
  }

  // Chọn một gợi ý tìm kiếm: điền địa chỉ + toạ độ và đưa bản đồ tới đó
  const handleSelectAddress = (r) => {
    geoAbort.current?.abort()
    setGeocoding(false)
    setForm((f) => ({ ...f, address: r.label }))
    setPoint(r.lat, r.lng)
    setFocus({ lat: r.lat, lng: r.lng, zoom: 17 })
    setErrors((er) => ({ ...er, address: undefined, location: undefined }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setSubmitError('')
    let data = form
    // Có địa chỉ chữ nhưng chưa có toạ độ: tự đổi địa chỉ thành toạ độ (kết quả đầu tiên)
    if (!hasPoint && form.address.trim()) {
      const [first] = await searchAddress(form.address, { bias: anchor && { lat: anchor[0], lng: anchor[1] } })
      if (first) {
        data = { ...form, lat: first.lat.toFixed(6), lng: first.lng.toFixed(6) }
        setForm(data)
        setFocus({ lat: first.lat, lng: first.lng, zoom: 17 })
      }
    }
    const found = validateOrderForm(data)
    setErrors(found)
    if (Object.keys(found).length) { setSubmitting(false); return }
    try {
      await onSubmit(data)
    } catch (err) {
      if (err.status === 409) setErrors({ code: 'Mã đơn đã tồn tại, hãy đổi mã khác' })
      else setSubmitError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const err = (k) => errors[k] && <span className="field-error">{errors[k]}</span>

  return (
    <div className="modal-backdrop" onClick={submitting ? undefined : onClose}>
      <form className="modal modal-wide glass" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit} noValidate>
        <div className="modal-head">
          <h3>Thêm đơn hàng</h3>
          <button type="button" className="icon-btn" onClick={onClose} disabled={submitting}>✕</button>
        </div>

        <div className="order-form">
          <div className="order-form-fields">
            <div className="grid-2">
              <label className="field-col"><span>Mã đơn</span>
                <input value={form.code} onChange={set('code')} maxLength={30} />{err('code')}
              </label>
              <label className="field-col"><span>Ngày giao</span>
                <input type="date" value={form.delivery_date} onChange={set('delivery_date')} />{err('delivery_date')}
              </label>
            </div>
            <label className="field-col"><span>Tên khách hàng</span>
              <input value={form.name} onChange={set('name')} maxLength={150} placeholder="VD: Cửa hàng Minh Anh" />{err('name')}
            </label>
            <div className="field-col"><span>Địa chỉ giao hàng {geocoding && '· đang lấy địa chỉ…'}</span>
              <AddressSearchInput
                value={form.address}
                onChange={(text) => setForm((f) => ({ ...f, address: text, lat: '', lng: '' }))}
                onSelect={handleSelectAddress}
                bias={anchor && { lat: anchor[0], lng: anchor[1] }}
                placeholder="Gõ địa chỉ để tìm (VD: 1 Đại Cồ Việt, Hà Nội) hoặc click bản đồ"
                hint="Gõ rồi chọn gợi ý, hoặc click/kéo marker trên bản đồ — địa chỉ và toạ độ tự đồng bộ."
              />{err('address')}
            </div>
            <div className="grid-2">
              <label className="field-col"><span>Khối lượng (kg)</span>
                <input type="number" min="0" step="any" value={form.demand} onChange={set('demand')} />{err('demand')}
              </label>
              <label className="field-col"><span>Thời gian phục vụ (phút)</span>
                <input type="number" min="0" step="1" value={form.service_min} onChange={set('service_min')} />{err('service_min')}
              </label>
            </div>
            <div className="grid-2">
              <label className="field-col"><span>Giờ mở cửa</span>
                <input type="time" value={form.tw_start} onChange={set('tw_start')} />
              </label>
              <label className="field-col"><span>Giờ đóng cửa</span>
                <input type="time" value={form.tw_end} onChange={set('tw_end')} />
              </label>
            </div>
            {err('time')}
            <div className="muted small">
              Toạ độ: {hasPoint ? `${form.lat}, ${form.lng}` : 'chưa chọn'}
            </div>
            {err('location')}
          </div>

          <LocationPicker value={point} focus={focus} center={anchor || DEFAULT_CENTER} zoom={anchor ? 14 : DEFAULT_ZOOM} onPick={handlePick} />
        </div>

        {submitError && <div className="form-error">{submitError}</div>}
        <div className="row modal-actions">
          <button type="button" className="btn" onClick={onClose} disabled={submitting}>Huỷ</button>
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? 'Đang lưu…' : '💾 Lưu đơn hàng'}
          </button>
        </div>
      </form>
    </div>
  )
}
