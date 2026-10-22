import { API_BASE_URL } from '../constants/config'

// Rút gọn thông báo lỗi của FastAPI: detail có thể là chuỗi (HTTPException)
// hoặc mảng lỗi validate (422) dạng [{ loc, msg }]
function parseErrorDetail(text, fallback) {
  try {
    const { detail } = JSON.parse(text)
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail.map((d) => `${(d.loc || []).slice(1).join('.')}: ${d.msg}`).join('; ')
    }
  } catch { /* body không phải JSON */ }
  return text || fallback
}

// Client fetch cơ sở: gắn base URL, JSON header, xử lý lỗi chung.
export async function request(path, { method = 'GET', body, signal } = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
    signal,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    const err = new Error(`HTTP ${res.status}: ${parseErrorDetail(text, res.statusText)}`)
    err.status = res.status
    throw err
  }
  return res.status === 204 ? null : res.json()
}
