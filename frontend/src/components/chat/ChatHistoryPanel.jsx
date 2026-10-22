import { useEffect, useState } from 'react'
import { listChatThreads } from '../../api/chatApi'

const formatDate = (value) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function ChatHistoryPanel({ userId, activeThreadId, onSelect, onNewChat, onClose }) {
  const [threads, setThreads] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadThreads = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await listChatThreads(userId)
      setThreads(Array.isArray(data) ? data : [])
    } catch (e) {
      setError(e.message || 'Không thể tải lịch sử hội thoại')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadThreads() }, [userId])

  return (
    <div className="chat-history-panel">
      <div className="chat-history-head">
        <div>
          <b>Lịch sử hội thoại</b>
          <div className="status">Các thread đã lưu trong SQLite</div>
        </div>
        <button className="icon-btn" onClick={onClose} title="Đóng lịch sử">✕</button>
      </div>

      <button className="btn btn-primary chat-new-btn" onClick={() => { onNewChat?.(); onClose?.() }}>
        ＋ Cuộc trò chuyện mới
      </button>

      <div className="chat-history-list">
        {loading && <div className="chat-history-empty">Đang tải lịch sử…</div>}
        {!loading && error && <div className="chat-history-empty">{error}</div>}
        {!loading && !error && threads.length === 0 && (
          <div className="chat-history-empty">Chưa có cuộc trò chuyện nào được lưu.</div>
        )}
        {!loading && !error && threads.map((thread) => (
          <button
            key={thread.thread_id}
            className={`chat-history-item ${activeThreadId === thread.thread_id ? 'active' : ''}`}
            onClick={() => { onSelect?.(thread.thread_id); onClose?.() }}
          >
            <div className="chat-history-title">{thread.title || 'Cuộc trò chuyện'}</div>
            <div className="chat-history-preview">{thread.preview}</div>
            <div className="chat-history-meta">
              <span>{thread.message_count} tin nhắn</span>
              <span>{formatDate(thread.updated_at)}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
