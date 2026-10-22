import ReactMarkdown from 'react-markdown'
import RouteActionCard from './RouteActionCard'
import ApprovalCard from './ApprovalCard'

export default function ChatMessageItem({
  message,
  index,
  onView,
  onSave,
  onActionResponse,
}) {
  const isStreaming = message.role === 'ai' && message.streaming

  return (
    <div className={`msg msg-${message.role}`}>
      <div className={`bubble ${message.role === 'ai' ? 'markdown-content' : ''}`}>
        {message.role === 'ai' ? (
          <>
            <ReactMarkdown>{message.text ?? ''}</ReactMarkdown>
            {isStreaming && <span className="streaming-cursor" aria-hidden="true" />}
            {message.streamError && (
              <div className="stream-warning">
                Kết nối gián đoạn, tin nhắn có thể chưa hoàn chỉnh.
              </div>
            )}
          </>
        ) : (
          message.text
        )}
      </div>

      {message.action_data && (
        <ApprovalCard
          data={message.action_data}
          onApprove={() => onActionResponse?.(message.threadId || message.thread_id, true, index)}
          onReject={() => onActionResponse?.(message.threadId || message.thread_id, false, index)}
          resolved={message.action_resolved}
        />
      )}

      {message.routeResult && (
        <RouteActionCard
          result={message.routeResult}
          onView={onView}
          onSave={onSave}
        />
      )}
    </div>
  )
}
