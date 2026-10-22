// Geocoding bằng Nominatim (OpenStreetMap) — nằm trong hệ sinh thái OSM, không cần API key.
// Lưu ý chính sách Nominatim: tối đa ~1 request/giây, nên phía UI phải debounce.
// Mọi hàm đều không ném lỗi: thất bại/huỷ trả về null hoặc [] để người dùng nhập tay.
const BASE = 'https://nominatim.openstreetmap.org'

// Toạ độ -> địa chỉ chữ (khi click bản đồ)
export async function reverseGeocode(lat, lng, signal) {
  try {
    const res = await fetch(`${BASE}/reverse?format=jsonv2&accept-language=vi&lat=${lat}&lon=${lng}`, { signal })
    if (!res.ok) return null
    const data = await res.json()
    return data.display_name || null
  } catch {
    return null
  }
}

// Địa chỉ chữ -> danh sách { label, lat, lng }. bias = { lat, lng } ưu tiên kết quả gần khu vực đó (không giới hạn cứng).
export async function searchAddress(query, { signal, bias, limit = 5 } = {}) {
  const q = (query || '').trim()
  if (!q) return []
  const params = new URLSearchParams({ format: 'jsonv2', 'accept-language': 'vi', countrycodes: 'vn', limit: String(limit), q })
  if (bias) {
    const d = 0.4
    params.set('viewbox', [bias.lng - d, bias.lat + d, bias.lng + d, bias.lat - d].join(','))
  }
  try {
    const res = await fetch(`${BASE}/search?${params}`, { signal })
    if (!res.ok) return []
    const data = await res.json()
    return data.map((r) => ({ label: r.display_name, lat: Number(r.lat), lng: Number(r.lon) }))
  } catch {
    return []
  }
}
