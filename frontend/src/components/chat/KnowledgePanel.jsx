import { useEffect, useRef, useState, useCallback } from 'react'
import {
  uploadRagDocument,
  listRagDocuments,
  deleteRagDocument,
  searchRagDocuments,
} from '../../api/ragApi'

/* ---- helpers ---- */
const EXT_ICON = {
  pdf: { icon: 'PDF', color: '#ef4444' },
  docx: { icon: 'DOC', color: '#3b82f6' },
  doc: { icon: 'DOC', color: '#3b82f6' },
  csv: { icon: 'CSV', color: '#10b981' },
  xlsx: { icon: 'XLS', color: '#22c55e' },
  xls: { icon: 'XLS', color: '#22c55e' },
  txt: { icon: 'TXT', color: '#8b5cf6' },
  md: { icon: 'MD', color: '#6366f1' },
  py: { icon: 'PY', color: '#f59e0b' },
}

function fileIcon(filename) {
  const ext = (filename || '').split('.').pop().toLowerCase()
  return EXT_ICON[ext] || { icon: ext.toUpperCase().slice(0, 3) || '?', color: '#94a3b8' }
}

function fmtBytes(b) {
  if (b == null) return ''
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1024 / 1024).toFixed(1)} MB`
}

function fmtDate(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleDateString('vi-VN', {
      day: '2-digit', month: '2-digit', year: 'numeric',
    })
  } catch {
    return iso.slice(0, 10)
  }
}

/* ---- component ---- */
export default function KnowledgePanel({ userId = 'default', onClose }) {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState(null) // { ok, text }
  const [deletingId, setDeletingId] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState(null)
  const [searching, setSearching] = useState(false)
  const fileRef = useRef()

  const loadDocs = useCallback(async () => {
    setLoading(true)
    try {
      const res = await listRagDocuments(userId)
      setDocuments(res.documents || [])
    } catch (e) {
      setUploadMsg({ ok: false, text: `Không tải được danh sách: ${e.message}` })
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => { loadDocs() }, [loadDocs])

  const handleFiles = async (files) => {
    if (!files?.length) return
    setUploading(true)
    setUploadMsg(null)
    let successCount = 0
    const errors = []
    for (const file of files) {
      try {
        await uploadRagDocument(file, userId)
        successCount++
      } catch (e) {
        errors.push(`${file.name}: ${e.message}`)
      }
    }
    await loadDocs()
    if (errors.length) {
      setUploadMsg({ ok: false, text: errors.join(' | ') })
    } else {
      setUploadMsg({ ok: true, text: `Đã nạp thành công ${successCount} tài liệu vào Knowledge Base.` })
    }
    setUploading(false)
  }

  const onFileInput = (e) => {
    handleFiles([...e.target.files])
    e.target.value = ''
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    handleFiles([...e.dataTransfer.files])
  }

  const handleDelete = async (doc) => {
    if (!window.confirm(`Xóa tài liệu "${doc.filename}" khỏi Knowledge Base?`)) return
    setDeletingId(doc.document_id)
    try {
      await deleteRagDocument(doc.document_id, userId)
      setDocuments((prev) => prev.filter((d) => d.document_id !== doc.document_id))
      setSearchResults(null)
    } catch (e) {
      setUploadMsg({ ok: false, text: `Xóa thất bại: ${e.message}` })
    } finally {
      setDeletingId(null)
    }
  }

  const handleSearch = async () => {
    if (!query.trim()) return
    setSearching(true)
    setSearchResults(null)
    try {
      const res = await searchRagDocuments(query, userId, 4)
      setSearchResults(res.results || [])
    } catch (e) {
      setUploadMsg({ ok: false, text: `Tìm kiếm thất bại: ${e.message}` })
    } finally {
      setSearching(false)
    }
  }

  return (
    <div className="knowledge-panel">
      {/* Header */}
      <div className="knowledge-panel-head">
        <div>
          <strong>📚 Knowledge Base</strong>
          <div className="knowledge-subtitle">Tài liệu Agent sẽ tra cứu khi trả lời</div>
        </div>
        <button className="btn btn-sm" onClick={onClose} title="Đóng" style={{ padding: '4px 10px' }}>✕</button>
      </div>

      {/* Upload zone */}
      <div
        className={`knowledge-upload${dragging ? ' dragging' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        style={{
          border: `2px dashed ${dragging ? 'var(--primary)' : 'var(--border)'}`,
          borderRadius: 12,
          padding: '14px 12px',
          textAlign: 'center',
          background: dragging ? 'var(--primary-soft)' : 'var(--surface)',
          transition: 'all .2s ease',
          cursor: 'pointer',
        }}
        onClick={() => !uploading && fileRef.current?.click()}
      >
        <input
          ref={fileRef}
          type="file"
          multiple
          accept=".pdf,.docx,.csv,.xlsx,.xls,.txt,.md,.py"
          style={{ display: 'none' }}
          onChange={onFileInput}
        />
        {uploading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, color: 'var(--primary)' }}>
            <span className="thinking-spinner" />
            <span style={{ fontSize: 13 }}>Đang xử lý và lập chỉ mục...</span>
          </div>
        ) : (
          <>
            <div style={{ fontSize: 24, marginBottom: 4 }}>📂</div>
            <div style={{ fontSize: 13, fontWeight: 600 }}>Kéo file vào đây hoặc click để chọn</div>
            <div className="knowledge-hint" style={{ marginTop: 4 }}>
              PDF · DOCX · CSV · XLSX · TXT · MD · PY — tối đa 20 MB
            </div>
          </>
        )}
      </div>

      {/* Upload result message */}
      {uploadMsg && (
        <div className={`knowledge-message ${uploadMsg.ok ? '' : 'knowledge-error'}`}
          style={{ background: uploadMsg.ok ? 'rgba(34,197,94,.08)' : undefined, color: uploadMsg.ok ? '#16a34a' : undefined }}
        >
          {uploadMsg.ok ? '✅ ' : '❌ '}{uploadMsg.text}
        </div>
      )}

      {/* Document list */}
      <div className="knowledge-list-heading">
        <strong style={{ fontSize: 13 }}>Tài liệu đã nạp ({documents.length})</strong>
        <button className="btn btn-sm" onClick={loadDocs} disabled={loading} style={{ padding: '3px 9px', fontSize: 11 }}>
          {loading ? '...' : '↻ Làm mới'}
        </button>
      </div>

      {loading && documents.length === 0 ? (
        <div className="knowledge-empty">Đang tải...</div>
      ) : documents.length === 0 ? (
        <div className="knowledge-empty">
          Chưa có tài liệu nào.<br />
          Hãy upload PDF, DOCX, CSV... để Agent có thể tra cứu.
        </div>
      ) : (
        <div className="knowledge-documents">
          {documents.map((doc) => {
            const fi = fileIcon(doc.filename)
            const isDeleting = deletingId === doc.document_id
            return (
              <div key={doc.document_id} className="knowledge-document">
                <div className="knowledge-file-icon" style={{ color: fi.color, background: `${fi.color}18` }}>
                  {fi.icon}
                </div>
                <div className="knowledge-file-info">
                  <strong title={doc.filename}>{doc.filename}</strong>
                  <span>
                    {fmtBytes(doc.file_size)}
                    {doc.chunk_count ? ` · ${doc.chunk_count} chunk` : ''}
                    {doc.created_at ? ` · ${fmtDate(doc.created_at)}` : ''}
                    {doc.status === 'indexed' && (
                      <span className="knowledge-indexed"> · ✓ Đã lập chỉ mục</span>
                    )}
                  </span>
                </div>
                <button
                  className="btn btn-sm knowledge-delete"
                  title="Xóa tài liệu"
                  disabled={isDeleting}
                  onClick={() => handleDelete(doc)}
                  style={{ background: 'transparent', border: 'none', color: 'var(--muted)', cursor: 'pointer' }}
                >
                  {isDeleting ? '...' : '🗑️'}
                </button>
              </div>
            )
          })}
        </div>
      )}

      {/* Search test section */}
      <div style={{ borderTop: '1px solid var(--border)', paddingTop: 12 }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>🔍 Thử tìm kiếm</div>
        <div style={{ display: 'flex', gap: 6 }}>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Nhập từ khóa để tìm trong tài liệu..."
            style={{ flex: 1, fontSize: 12, padding: '6px 10px' }}
          />
          <button className="btn btn-sm btn-primary" onClick={handleSearch} disabled={searching || !query.trim()}>
            {searching ? '...' : 'Tìm'}
          </button>
        </div>

        {searchResults !== null && (
          <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {searchResults.length === 0 ? (
              <div className="knowledge-empty" style={{ padding: '10px 0' }}>
                Không tìm thấy đoạn phù hợp.
              </div>
            ) : searchResults.map((r, i) => (
              <div key={i} style={{
                border: '1px solid var(--border)',
                borderRadius: 10,
                padding: '9px 11px',
                fontSize: 12,
                background: 'var(--surface)',
              }}>
                <div style={{ fontWeight: 700, color: 'var(--primary)', marginBottom: 4 }}>
                  📄 {r.filename}{r.page ? ` — trang ${r.page}` : ''}{r.sheet ? ` — sheet ${r.sheet}` : ''}
                </div>
                <div style={{ color: 'var(--text)', lineHeight: 1.55, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {r.content?.length > 280 ? r.content.slice(0, 280) + '…' : r.content}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
