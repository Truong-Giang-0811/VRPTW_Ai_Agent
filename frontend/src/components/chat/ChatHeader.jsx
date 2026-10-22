export default function ChatHeader({ thinking, thinkingStatus, onClose, onHistory, onNewChat, onKnowledge }) {
  const statusText = thinking ? (thinkingStatus || 'Đang xử lý...') : 'Online'

  return (
    <div className="chat-header">
      <div className={`avatar ${thinking ? 'avatar-thinking' : ''}`}>🤖</div>
      <div className="grow">
        <b>AI Copilot</b>
        <div className={`status ${thinking ? 'thinking' : 'online'}`}>
          {thinking && <span className="status-spinner" aria-hidden="true" />}
          <span>{statusText}</span>
        </div>
      </div>
      <button className="icon-btn" onClick={onNewChat} title="Cuộc trò chuyện mới">＋</button>
      <button className="icon-btn" onClick={onKnowledge} title="Kho tài liệu">📚</button>
      <button className="icon-btn" onClick={onHistory} title="Lịch sử hội thoại">☰</button>
      <button className="icon-btn" onClick={onClose} title="Đóng">✕</button>
    </div>
  )
}
