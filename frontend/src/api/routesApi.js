import { request } from './client'
import { USE_MOCK } from '../constants/config'
import { MOCK_RESULT, MOCK_HISTORY } from '../constants/mockData'

const wait = (ms) => new Promise((r) => setTimeout(r, ms))

// Chuyển đổi số phút từ 00:00 sang chuỗi "HH:MM"
export const minToHHMM = (min) => {
  if (min == null || isNaN(min)) return '--:--'
  const totalM = Math.round(Number(min))
  const h = Math.floor(totalM / 60) % 24
  const m = totalM % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

/**
 * Chuẩn hóa kết quả trả về từ Backend (/optimize, /optimize-from-db, /plans/{id})
 * sang cấu trúc đồng nhất cho UI (RoutesDetailTab, RouteTimelineItem, MapContainer, Navbar).
 */
export function normalizeOptimizeResult(res, ordersList = [], vehiclesList = []) {
  if (!res) return null
  const ordersMap = new Map((ordersList || []).map((o) => [o.id, o]))
  const vehiclesMap = new Map((vehiclesList || []).map((v) => [v.id, v]))

  let totalViolations = 0

  const routes = (res.routes || []).map((r, idx) => {
    const vId = r.vehicle_id || idx + 1
    const vehicleInfo = vehiclesMap.get(vId)
    const vName = r.vehicle_name || vehicleInfo?.name || `Xe ${String(idx + 1).padStart(2, '0')}`
    const vCap = Number(r.capacity || vehicleInfo?.capacity || res.vehicle_capacity || 1000)

    // Backend solver trả về 'timeline', mock hoặc plan lưu trả về 'stops'
    const rawStops = r.timeline || r.stops || []
    const stops = rawStops.map((item) => {
      const orderId = item.customer_id ?? item.order_id ?? item.id
      const ord = ordersMap.get(orderId)

      const arrMin = item.arrival_min ?? (typeof item.arrival === 'number' ? item.arrival : null)
      const depMin = item.departure_min ?? (typeof item.departure === 'number' ? item.departure : null)
      const srvMin = item.service_start_min ?? (typeof item.service_start === 'number' ? item.service_start : null)
      const dueMin = item.due_min
      const waitMin = item.waiting_min ?? item.waiting ?? 0

      const isViolated = (srvMin != null && dueMin != null && srvMin > dueMin) || !!item.isViolated
      if (isViolated) totalViolations++

      return {
        order_id: orderId,
        name: ord?.name || item.name || `Đơn hàng #${orderId}`,
        lat: ord?.lat ?? item.lat,
        lng: ord?.lng ?? item.lng,
        demand: ord?.demand ?? item.demand ?? 0,
        arrival: arrMin != null ? minToHHMM(arrMin) : (item.arrival || '--:--'),
        waiting: Math.round(waitMin),
        service_start: srvMin != null ? minToHHMM(srvMin) : (item.service_start || '--:--'),
        departure: depMin != null ? minToHHMM(depMin) : (item.departure || '--:--'),
        tw_start: ord?.tw_start || (item.ready_min != null ? minToHHMM(item.ready_min) : undefined),
        tw_end: ord?.tw_end || (dueMin != null ? minToHHMM(dueMin) : undefined),
        isViolated,
      }
    })

    const end_time = r.finish_min != null ? minToHHMM(r.finish_min) : (r.end_time || '--:--')

    return {
      vehicle_id: vId,
      vehicle_name: vName,
      capacity: vCap,
      load: Number(r.load || 0),
      distance_km: Number(r.distance_km || 0),
      duration_min: Number(r.duration_min || 0),
      end_time,
      stops,
      geometry: r.geometry || [], // Backend đã đảo sẵn thành [[lat, lng], ...]
    }
  })

  return {
    raw: res,
    mode: res.clustering_mode || res.mode || 'spatiotemporal',
    total_distance_km: Number(res.total_distance ?? res.total_distance_km ?? 0),
    total_time_min: Math.round(Number(res.total_duration ?? res.total_time_min ?? 0)),
    violations: totalViolations,
    vehicle_count: res.vehicle_count || routes.length,
    routes,
  }
}

// 1. Tối ưu qua dữ liệu đầu vào trực tiếp (Stateless)
export async function optimizeRoutes(payload, ordersList = [], vehiclesList = []) {
  if (USE_MOCK) {
    await wait(900)
    return normalizeOptimizeResult(MOCK_RESULT, ordersList, vehiclesList)
  }
  const raw = await request('/api/routes/optimize', { method: 'POST', body: payload })
  return normalizeOptimizeResult(raw, ordersList, vehiclesList)
}

// 2. Tối ưu tự động bằng cách đọc từ Database
export async function optimizeFromDb(payload, ordersList = [], vehiclesList = []) {
  if (USE_MOCK) {
    await wait(900)
    return normalizeOptimizeResult(MOCK_RESULT, ordersList, vehiclesList)
  }
  const body = {
    depot_id: payload.depot_id,
    delivery_date: payload.date || payload.delivery_date,
    vehicle_capacity: payload.capacity || payload.vehicle_capacity || 1000,
    vehicle_number: payload.vehicle_number,
    algorithm: payload.algorithm || 'GA',
    clustering_mode: payload.mode || payload.clustering_mode || 'distance',
    time_weight: payload.time_weight ?? 0.35,
    order_ids: payload.order_ids,
  }
  const raw = await request('/api/routes/optimize-from-db', { method: 'POST', body })
  return normalizeOptimizeResult(raw, ordersList, vehiclesList)
}

// 3. Lưu kế hoạch vào Database
export async function saveRoutePlan(payload) {
  if (USE_MOCK) {
    await wait(500)
    return { id: Date.now(), message: 'Đã lưu kế hoạch (Mock)' }
  }
  const rawData = payload.result?.raw || payload.result || {}
  const body = {
    depot_id: payload.depot_id,
    delivery_date: payload.date,
    algorithm: rawData.algorithm || payload.algo?.algorithm || 'GA',
    status: 'confirmed',
    total_distance: payload.result?.total_distance_km ?? rawData.total_distance,
    total_duration: payload.result?.total_time_min ?? rawData.total_duration,
    routes: rawData.routes || payload.result?.routes || [],
    auto_update_orders_status: true,
  }
  return request('/api/routes/save-plan', { method: 'POST', body })
}

// 4. So sánh 2 chế độ phân cụm
export async function compareModes(payload, ordersList = [], vehiclesList = []) {
  if (USE_MOCK) {
    await wait(1200)
    return {
      distance: { ...MOCK_RESULT, mode: 'distance', total_distance_km: 28.9, total_time_min: 340, violations: 2 },
      spatiotemporal: MOCK_RESULT,
    }
  }
  const raw = await request('/api/routes/optimize/compare', { method: 'POST', body: payload })
  return {
    distance: normalizeOptimizeResult(raw.distance_mode, ordersList, vehiclesList),
    spatiotemporal: normalizeOptimizeResult(raw.spatiotemporal_mode, ordersList, vehiclesList),
    comparison: raw.comparison,
  }
}

// 5. Danh sách lịch sử các kế hoạch
export async function listRoutePlans() {
  if (USE_MOCK) return MOCK_HISTORY
  return request('/api/routes/plans')
}

// 6. Chi tiết một kế hoạch cũ kèm routes để vẽ lại lên map
export async function getRoutePlan(planId, ordersList = [], vehiclesList = []) {
  if (USE_MOCK) {
    return normalizeOptimizeResult(MOCK_RESULT, ordersList, vehiclesList)
  }
  const raw = await request(`/api/routes/plans/${planId}`)
  return normalizeOptimizeResult(raw, ordersList, vehiclesList)
}
