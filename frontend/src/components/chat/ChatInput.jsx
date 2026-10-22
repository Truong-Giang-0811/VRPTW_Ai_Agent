import { useState } from 'react'

export default function ChatInput({ disabled, onSend }) {
  const [text, setText] = useState('')
  const submit = () => { if (text.trim() && !disabled) { onSend(text.trim()); setText('') } }
  return (
    <div className="chat-input">
      <input value={text} placeholder="Nhập yêu cầu cho AI…" disabled={disabled}
        onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && submit()} />
      <button className="btn btn-primary" disabled={disabled || !text.trim()} onClick={submit}>Gửi</button>
    </div>
  )
}
