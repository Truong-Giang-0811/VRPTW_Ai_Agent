import { request } from './client'
import { API_BASE_URL } from '../constants/config'

/**
 * Gửi tin nhắn tới LangGraph Agent qua endpoint HTTP đồng bộ cũ.
 * Giữ lại để tương thích ngược và cho các nơi chưa dùng SSE.
 */
export async function sendChatMessage(
  message,
  _history = [],
  context = {},
  _ordersList = [],
  _vehiclesList = [],
) {
  const res = await request('/api/agent/chat', {
    method: 'POST',
    body: {
      message: message.trim(),
      thread_id: context.threadId || null,
      user_id: context.userId || 'default',
      active_route_plan_id: context.activeRoutePlanId ?? null,
    },
  })

  return {
    text: res.reply || 'Agent chưa trả về nội dung phản hồi.',
    threadId: res.thread_id || context.threadId || null,
    requiresAction: Boolean(res.requires_action),
    actionData: res.action_data || null,
    routeResult: null,
  }
}

function parseSSEBlock(block) {
  let event = 'message'
  const dataLines = []

  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trimStart())
    }
  }

  if (!dataLines.length) return null

  const rawData = dataLines.join('\n')
  let data = rawData
  try {
    data = JSON.parse(rawData)
  } catch {
    // Cho phép server gửi plain text trong tương lai.
  }

  return { event, data }
}

/**
 * Gọi Agent bằng POST + SSE streaming.
 * EventSource không dùng được vì payload chat là POST và có nhiều context.
 */
export async function streamChatMessage(message, context = {}, callbacks = {}) {
  const {
    onStatus,
    onToken,
    onActionRequired,
    onDone,
    onError,
  } = callbacks

  const response = await fetch(`${API_BASE_URL}/api/agent/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({
      message: message.trim(),
      thread_id: context.threadId || null,
      user_id: context.userId || 'default',
      active_route_plan_id: context.activeRoutePlanId ?? null,
    }),
  })

  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const payload = await response.json()
      detail = payload.detail || detail
    } catch {
      // Không làm gì nếu body không phải JSON.
    }
    const error = new Error(detail)
    onError?.(error)
    throw error
  }

  if (!response.body) {
    const error = new Error('Trình duyệt không hỗ trợ đọc response stream.')
    onError?.(error)
    throw error
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let receivedDone = false
  let receivedActionRequired = false

  const dispatch = (block) => {
    const parsed = parseSSEBlock(block)
    if (!parsed) return

    const { event, data } = parsed

    if (event === 'status') {
      onStatus?.(data?.message || 'Đang xử lý...')
    } else if (event === 'token') {
      onToken?.(data?.delta || '')
    } else if (event === 'action_required') {
      receivedActionRequired = true
      onActionRequired?.(data || {})
    } else if (event === 'done') {
      receivedDone = true
      onDone?.(data || {})
    } else if (event === 'error') {
      const error = new Error(data?.message || 'Agent gặp lỗi khi stream.')
      error.payload = data
      onError?.(error)
    }
  }

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // SSE frame kết thúc bằng một dòng trống.
      const blocks = buffer.split(/\r?\n\r?\n/)
      buffer = blocks.pop() || ''
      blocks.forEach(dispatch)
    }

    buffer += decoder.decode()
    if (buffer.trim()) dispatch(buffer)

    if (!receivedDone && !receivedActionRequired) {
      const error = new Error('Kết nối stream bị gián đoạn trước khi Agent hoàn tất.')
      onError?.(error)
      throw error
    }
  } catch (error) {
    onError?.(error)
    throw error
  } finally {
    reader.releaseLock()
  }
}

export async function resumeAgentAction(threadId, approved, reason = '', context = {}) {
  const res = await request('/api/agent/resume', {
    method: 'POST',
    body: {
      thread_id: threadId,
      approved: Boolean(approved),
      reason: reason || null,
      user_id: context.userId || 'default',
      active_route_plan_id: context.activeRoutePlanId ?? null,
    },
  })
  return {
    text: res.reply || '',
    threadId: res.thread_id || threadId,
    requiresAction: Boolean(res.requires_action),
    actionData: res.action_data || null,
    routeResult: null,
  }
}

export async function listChatThreads(userId = 'default') {
  return request(`/api/agent/threads?user_id=${encodeURIComponent(userId)}`)
}

export async function getChatThread(threadId, userId = 'default') {
  return request(`/api/agent/threads/${encodeURIComponent(threadId)}?user_id=${encodeURIComponent(userId)}`)
}
