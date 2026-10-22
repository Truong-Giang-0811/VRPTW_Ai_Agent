import { API_BASE_URL } from '../constants/config'

async function readResponse(response) {
  const text = await response.text()
  let payload = {}
  try { payload = text ? JSON.parse(text) : {} } catch { /* non-JSON error */ }
  if (!response.ok) {
    const detail = typeof payload.detail === 'string' ? payload.detail : `HTTP ${response.status}`
    throw new Error(detail)
  }
  return payload
}

export async function uploadRagDocument(file, userId = 'default') {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('user_id', userId)
  const response = await fetch(`${API_BASE_URL}/api/rag/upload`, {
    method: 'POST',
    body: formData,
  })
  return readResponse(response)
}

export async function listRagDocuments(userId = 'default') {
  const response = await fetch(`${API_BASE_URL}/api/rag/documents?user_id=${encodeURIComponent(userId)}`)
  return readResponse(response)
}

export async function deleteRagDocument(documentId, userId = 'default') {
  const response = await fetch(
    `${API_BASE_URL}/api/rag/documents/${encodeURIComponent(documentId)}?user_id=${encodeURIComponent(userId)}`,
    { method: 'DELETE' },
  )
  return readResponse(response)
}

export async function searchRagDocuments(query, userId = 'default', limit = 5) {
  const response = await fetch(`${API_BASE_URL}/api/rag/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, user_id: userId, limit }),
  })
  return readResponse(response)
}
