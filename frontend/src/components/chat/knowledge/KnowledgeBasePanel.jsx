import { useCallback, useEffect, useRef, useState } from 'react'
import { deleteRagDocument, listRagDocuments, uploadRagDocument } from '../../../api/ragApi'

const ACCEPTED = '.pdf,.docx,.csv,.xlsx,.xls,.txt,.md,.py'
const MAX_BYTES = 20 * 1024 * 1024

function formatBytes(bytes = 0) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function KnowledgeBasePanel({ userId = 'default', onClose }) {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const inputRef = useRef(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const result = await listRagDocuments(userId)
      setDocuments(result.documents || [])
      setError('')
    } catch (err) {
      setError(err.message || 'Không thể tải danh sách tài liệu.')
    } finally {
      setLoading(false)
    }
  }, [userId])

  useEffect(() => {
    let active = true
    listRagDocuments(userId)
      .then((result) => {
        if (!active) return
        setDocuments(result.documents || [])
        setError('')
        setLoading(false)
      })
      .catch((err) => {
        if (!active) return
        setError(err.message || 'Không thể tải danh sách tài liệu.')
        setLoading(false)
      })
    return () => { active = false }
  }, [userId])

  const handleFiles = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    if (file.size > MAX_BYTES) {
      setError('File vượt quá giới hạn 20 MB.')
      return
    }

    setUploading(true)
    setError('')
    setNotice(`Đang đọc và lập chỉ mục: ${file.name}`)
    try {
      const result = await uploadRagDocument(file, userId)
      setNotice(`Đã lập chỉ mục ${result.document.filename} (${result.document.chunk_count} chunks).`)
      await refresh()
    } catch (err) {
      setNotice('')
      setError(err.message || 'Upload tài liệu thất bại.')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (document) => {
    if (!window.confirm(`Xóa tài liệu "${document.filename}" và các vector liên quan?`)) return
    setError('')
    try {
      await deleteRagDocument(document.document_id, userId)
      setDocuments((current) => current.filter((item) => item.document_id !== document.document_id))
      setNotice(`Đã xóa ${document.filename}.`)
    } catch (err) {
      setError(err.message || 'Không thể xóa tài liệu.')
    }
  }

  return (
    <section className="knowledge-panel">
      <div className="knowledge-panel-head">
        <div>
          <strong>Kho tri thức</strong>
          <div className="knowledge-subtitle">Tài liệu được dùng làm ngữ cảnh cho AI Agent</div>
        </div>
        <button className="icon-btn" onClick={onClose} title="Quay lại chat">✕</button>
      </div>

      <input ref={inputRef} type="file" accept={ACCEPTED} hidden onChange={handleFiles} />
      <button
        className="btn btn-primary knowledge-upload"
        disabled={uploading}
        onClick={() => inputRef.current?.click()}
      >
        {uploading ? 'Đang lập chỉ mục…' : '＋ Tải tài liệu lên'}
      </button>
      <div className="knowledge-hint">PDF, DOCX, CSV, XLSX, XLS, TXT, MD, PY · tối đa 20 MB</div>

      {error && <div className="knowledge-message knowledge-error">{error}</div>}
      {notice && <div className="knowledge-message">{notice}</div>}

      <div className="knowledge-list-heading">
        <strong>Tài liệu đã tải</strong>
        <button className="pill" onClick={refresh} disabled={loading || uploading}>Làm mới</button>
      </div>
      {loading ? <div className="knowledge-empty">Đang tải danh sách…</div> : documents.length === 0 ? (
        <div className="knowledge-empty">Chưa có tài liệu. Tải PDF hoặc tài liệu khác lên để bắt đầu dùng RAG.</div>
      ) : (
        <div className="knowledge-documents">
          {documents.map((document) => (
            <div className="knowledge-document" key={document.document_id}>
              <div className="knowledge-file-icon">{document.file_type?.toUpperCase().slice(0, 4) || 'FILE'}</div>
              <div className="knowledge-file-info">
                <strong title={document.filename}>{document.filename}</strong>
                <span>{formatBytes(document.file_size)} · {document.chunk_count} chunks</span>
                <span className="knowledge-indexed">Đã lập chỉ mục</span>
              </div>
              <button className="icon-btn knowledge-delete" title={`Xóa ${document.filename}`} onClick={() => handleDelete(document)}>×</button>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
