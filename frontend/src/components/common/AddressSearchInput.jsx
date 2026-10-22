import { useEffect, useRef, useState } from 'react'
import { searchAddress } from '../../api/geocodeApi'

const DEBOUNCE_MS = 600 // giữ dưới giới hạn ~1 req/s của Nominatim
const MIN_CHARS = 3

// Ô nhập địa chỉ có gợi ý. Người dùng gõ -> gợi ý từ OSM -> chọn thì gọi onSelect({ label, lat, lng }).
// value/onChange do cha quản lý để cha có thể ghi đè địa chỉ (vd khi click bản đồ).
export default function AddressSearchInput({ value, onChange, onSelect, bias, placeholder, hint }) {
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [active, setActive] = useState(0)
  const [empty, setEmpty] = useState(false)
  const timer = useRef(null)
  const abort = useRef(null)

  useEffect(() => () => { clearTimeout(timer.current); abort.current?.abort() }, [])

  const run = async (text) => {
    abort.current?.abort()
    abort.current = new AbortController()
    const signal = abort.current.signal
    setLoading(true)
    const found = await searchAddress(text, { signal, bias })
    if (signal.aborted) return
    setLoading(false)
    setResults(found)
    setActive(0)
    setEmpty(found.length === 0)
    setOpen(true)
    return found
  }

  const handleChange = (e) => {
    const text = e.target.value
    onChange(text)
    clearTimeout(timer.current)
    if (text.trim().length < MIN_CHARS) {
      abort.current?.abort()
      setResults([]); setOpen(false); setLoading(false); setEmpty(false)
      return
    }
    timer.current = setTimeout(() => run(text), DEBOUNCE_MS)
  }

  const choose = (r) => {
    setOpen(false)
    onSelect(r)
  }

  const handleKeyDown = async (e) => {
    if (e.key === 'ArrowDown' && open) { e.preventDefault(); setActive((i) => Math.min(i + 1, results.length - 1)) }
    else if (e.key === 'ArrowUp' && open) { e.preventDefault(); setActive((i) => Math.max(i - 1, 0)) }
    else if (e.key === 'Escape') setOpen(false)
    else if (e.key === 'Enter') {
      e.preventDefault() // không submit form khi đang tìm địa chỉ
      clearTimeout(timer.current)
      if (open && results[active]) return choose(results[active])
      if (value.trim().length >= MIN_CHARS) {
        const found = await run(value)
        if (found?.[0]) choose(found[0])
      }
    }
  }

  return (
    <div className="addr-search">
      <input
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onFocus={() => results.length && setOpen(true)}
        onBlur={() => setOpen(false)}
        maxLength={255}
        placeholder={placeholder}
        autoComplete="off"
      />
      {loading && <span className="addr-spinner">Đang tìm…</span>}
      {open && (
        <ul className="addr-results">
          {empty && <li className="addr-empty">Không tìm thấy — thử gõ cụ thể hơn hoặc click bản đồ</li>}
          {results.map((r, i) => (
            <li key={`${r.lat}-${r.lng}-${i}`} className={i === active ? 'on' : ''}
              onMouseDown={(e) => { e.preventDefault(); choose(r) }} onMouseEnter={() => setActive(i)}>
              {r.label}
            </li>
          ))}
        </ul>
      )}
      {hint && <div className="muted small">{hint}</div>}
    </div>
  )
}
