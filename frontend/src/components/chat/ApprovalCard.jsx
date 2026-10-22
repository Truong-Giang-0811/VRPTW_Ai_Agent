import { useState } from 'react'

export default function ApprovalCard({
  data,
  onApprove,
  onReject,
  resolved = null,
  disabled = false,
}) {
  const [submitting, setSubmitting] = useState(false)

  if (!data) return null

  const handleApprove = async () => {
    if (disabled || submitting || resolved) return
    setSubmitting(true)
    try {
      await onApprove?.()
    } finally {
      setSubmitting(false)
    }
  }

  const handleReject = async () => {
    if (disabled || submitting || resolved) return
    setSubmitting(true)
    try {
      await onReject?.()
    } finally {
      setSubmitting(false)
    }
  }

  if (resolved) {
    const isApproved = resolved === 'approved'
    return (
      <div className={`approval-card-resolved ${isApproved ? 'approved' : 'rejected'}`}>
        <span className="approval-status-icon">{isApproved ? '✅' : '❌'}</span>
        <span className="approval-status-text">
          {isApproved ? 'Bạn đã chấp thuận thực hiện thao tác này' : 'Bạn đã từ chối thao tác này'}
        </span>
      </div>
    )
  }

  const argsFormatted = data.args && Object.keys(data.args).length > 0
    ? JSON.stringify(data.args, null, 2)
    : null

  return (
    <div className="approval-card">
      <div className="approval-card-badge">
        <span className="badge-icon">⚠️</span>
        <span className="badge-text">Yêu cầu xác nhận hành động</span>
      </div>

      <div className="approval-card-body">
        <div className="approval-tool-name">
          Tác vụ: <b>{data.tool_name}</b>
        </div>
        {data.description && (
          <div className="approval-tool-desc">{data.description}</div>
        )}

        {argsFormatted && (
          <div className="approval-args-wrapper">
            <div className="approval-args-label">Tham số:</div>
            <pre className="approval-args-code">{argsFormatted}</pre>
          </div>
        )}
      </div>

      <div className="approval-card-actions">
        <button
          type="button"
          className="btn btn-sm btn-outline-danger approval-btn-reject"
          onClick={handleReject}
          disabled={disabled || submitting}
        >
          {submitting ? 'Đang gửi…' : '✕ Từ chối'}
        </button>
        <button
          type="button"
          className="btn btn-sm btn-primary approval-btn-approve"
          onClick={handleApprove}
          disabled={disabled || submitting}
        >
          {submitting ? 'Đang gửi…' : '✓ Chấp thuận'}
        </button>
      </div>
    </div>
  )
}
