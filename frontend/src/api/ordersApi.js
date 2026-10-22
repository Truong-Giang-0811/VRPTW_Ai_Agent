import { request } from './client'
import { USE_MOCK } from '../constants/config'
import { MOCK_ORDERS } from '../constants/mockData'

// Chuẩn hóa 1 bản ghi backend (DeliveryOrderRead) sang shape UI dùng
export const normalizeOrder = (o) => ({
  id: o.id,
  code: o.code,
  name: o.name,
  customer: o.name,
  address: o.address,
  lat: Number(o.latitude ?? o.lat ?? 0),
  lng: Number(o.longitude ?? o.lng ?? 0),
  demand: Number(o.demand_weight_kg ?? o.demand ?? 0),
  service_min: Number(o.service_duration_min ?? o.service_min ?? 10),
  delivery_date: o.delivery_date,
  tw_start: o.open_time ? String(o.open_time).slice(0, 5) : '08:00',
  tw_end: o.close_time ? String(o.close_time).slice(0, 5) : '17:00',
  status: o.status || 'pending',
  created_at: o.created_at || null,
})

// Lấy một trang; backend lọc theo ngày/trạng thái/từ khóa trước khi áp dụng skip/limit.
export const listPage = async ({
  skip = 0,
  limit = 25,
  delivery_date,
  status,
  q,
} = {}) => {
  if (USE_MOCK) {
    let items = [...MOCK_ORDERS]
    if (delivery_date) items = items.filter((o) => String(o.delivery_date || '').slice(0, 10) === delivery_date)
    if (status) items = items.filter((o) => o.status === status)
    if (q) {
      const needle = q.toLowerCase()
      items = items.filter((o) => `${o.code} ${o.name || o.customer} ${o.address}`.toLowerCase().includes(needle))
    }
    return { items: items.slice(skip, skip + limit).map(normalizeOrder), total: items.length, skip, limit, pages: Math.ceil(items.length / limit) }
  }
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) })
  if (delivery_date) params.set('delivery_date', delivery_date)
  if (status) params.set('status', status)
  if (q?.trim()) params.set('q', q.trim())
  const data = await request(`/api/orders/page?${params.toString()}`)
  return { ...data, items: (data.items || []).map(normalizeOrder) }
}

// Lấy đủ đơn cho một ngày phục vụ điều phối; tải từng trang thay vì nâng limit vô hạn.
export const listAll = async ({ delivery_date, pageSize = 100 } = {}) => {
  if (USE_MOCK) {
    const items = [...MOCK_ORDERS].filter((o) => !delivery_date || String(o.delivery_date || '').slice(0, 10) === delivery_date)
    return items.map(normalizeOrder)
  }
  const all = []
  let skip = 0
  let total = Infinity
  while (all.length < total) {
    const page = await listPage({ skip, limit: pageSize, delivery_date })
    all.push(...page.items)
    total = page.total
    if (page.items.length === 0) break
    skip += page.items.length
  }
  return all
}

// Giữ API list tương thích với các nơi đang dùng; mặc định trả về trang đầu.
export const list = async () => (await listPage({ skip: 0, limit: 100 })).items

// orderData: giá trị từ form (đã validate ở utils/orderForm.js). Trả về đơn đã chuẩn hóa, có id thật từ DB.
export const create = async (orderData) => {
  if (USE_MOCK) {
    const newOrder = { id: Date.now(), customer: orderData.name, status: 'pending', ...orderData }
    MOCK_ORDERS.push(newOrder)
    return newOrder
  }
  const payload = {
    code: orderData.code.trim(),
    name: orderData.name.trim(),
    address: orderData.address.trim(),
    latitude: Number(orderData.lat),
    longitude: Number(orderData.lng),
    demand_weight_kg: Number(orderData.demand),
    service_duration_min: Number(orderData.service_min),
    delivery_date: orderData.delivery_date,
    open_time: `${orderData.tw_start}:00`,
    close_time: `${orderData.tw_end}:00`,
    status: 'pending',
  }
  const created = await request('/api/orders/', { method: 'POST', body: payload })
  return normalizeOrder(created)
}

export const update = async (id, orderData) => {
  const payload = {
    name: orderData.name.trim(),
    address: orderData.address.trim(),
    latitude: Number(orderData.lat),
    longitude: Number(orderData.lng),
    demand_weight_kg: Number(orderData.demand),
    service_duration_min: Number(orderData.service_min),
    delivery_date: orderData.delivery_date,
    open_time: orderData.tw_start ? `${orderData.tw_start}:00` : null,
    close_time: orderData.tw_end ? `${orderData.tw_end}:00` : null,
    status: orderData.status || 'pending',
  }
  return normalizeOrder(await request(`/api/orders/${id}`, { method: 'PATCH', body: payload }))
}

export const updateStatus = async (id, status) => {
  return normalizeOrder(await request(`/api/orders/${id}`, { method: 'PATCH', body: { status } }))
}

export const remove = (id) => request(`/api/orders/${id}`, { method: 'DELETE' })
