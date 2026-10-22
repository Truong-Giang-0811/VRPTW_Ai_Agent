import { useEffect, useRef } from 'react'
import ChatMessageItem from './ChatMessageItem'

export default function ChatMessageList({ messages, thinking, thinkingStatus, onView, onSave, onActionResponse }) {
  const endRef = useRef(null)
  const streamingMessage = [...messages].reverse().find((message) => message.role === 'ai' && message.streaming)
  const hasStreamedText = Boolean(streamingMessage?.text?.trim())

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking, thinkingStatus])

  return (
    <div className="chat-list">
      {messages.map((m, i) => (
        <ChatMessageItem
          key={i}
          index={i}
          message={m}
          onView={onView}
          onSave={onSave}
          onActionResponse={onActionResponse}
        />
      ))}

      {thinking && !hasStreamedText && (
        <div className="thinking-bubble" role="status" aria-live="polite">
          <span className="thinking-spinner" aria-hidden="true" />
          <span>{thinkingStatus || 'Đang xử lý...'}</span>
        </div>
      )}

      <div ref={endRef} />
    </div>
  )
}
