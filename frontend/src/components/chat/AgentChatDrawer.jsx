import { useState } from 'react'
import ChatHeader from './ChatHeader'
import ChatMessageList from './ChatMessageList'
import QuickPrompts from './QuickPrompts'
import ChatInput from './ChatInput'
import ChatHistoryPanel from './ChatHistoryPanel'
import KnowledgePanel from './KnowledgePanel'

export default function AgentChatDrawer({
  open,
  onToggle,
  messages,
  thinking,
  thinkingStatus,
  onSend,
  onViewRoute,
  onSaveRoute,
  threadId,
  userId = 'default',
  onSelectThread,
  onNewChat,
  onActionResponse,
}) {
  // 'chat' | 'history' | 'knowledge'
  const [panel, setPanel] = useState('chat')

  return (
    <>
      {!open && <button className="fab" onClick={onToggle} title="Mở AI Copilot">🤖</button>}
      <div className={`chat-drawer glass ${open ? 'open' : ''}`}>
        <ChatHeader
          thinking={thinking}
          thinkingStatus={thinkingStatus}
          onClose={onToggle}
          onHistory={() => setPanel(panel === 'history' ? 'chat' : 'history')}
          onNewChat={() => { onNewChat?.(); setPanel('chat') }}
          onKnowledge={() => setPanel(panel === 'knowledge' ? 'chat' : 'knowledge')}
        />

        {panel === 'history' && (
          <ChatHistoryPanel
            userId={userId}
            activeThreadId={threadId}
            onSelect={(tid) => { onSelectThread?.(tid); setPanel('chat') }}
            onNewChat={() => { onNewChat?.(); setPanel('chat') }}
            onClose={() => setPanel('chat')}
          />
        )}

        {panel === 'knowledge' && (
          <KnowledgePanel
            userId={userId}
            onClose={() => setPanel('chat')}
          />
        )}

        {panel === 'chat' && (
          <>
            <ChatMessageList
              messages={messages}
              thinking={thinking}
              thinkingStatus={thinkingStatus}
              onView={onViewRoute}
              onSave={onSaveRoute}
              onActionResponse={onActionResponse}
            />
            {messages.length <= 1 && <QuickPrompts onPick={onSend} />}
            <ChatInput disabled={thinking} onSend={onSend} />
          </>
        )}
      </div>
    </>
  )
}
