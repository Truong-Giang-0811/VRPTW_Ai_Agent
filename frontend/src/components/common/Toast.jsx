import { useEffect } from 'react'

// toast: { type: 'success' | 'warning' | 'error', message } | null
export default function Toast({ toast, onClose }) {
  useEffect(() => {
    if (!toast) return
    const t = setTimeout(onClose, 3500)
    return () => clearTimeout(t)
  }, [toast, onClose])
  if (!toast) return null
  return <div className={`toast toast-${toast.type}`} onClick={onClose}>{toast.message}</div>
}
