import { request } from './client'
import { USE_MOCK } from '../constants/config'
import { MOCK_VEHICLES } from '../constants/mockData'

export const normalizeVehicle = (v) => ({
  id: v.id,
  code: v.code,
  name: v.name || `Xe ${v.code || v.id}`,
  capacity: Number(v.capacity_kg ?? v.capacity ?? 1000),
  status: v.status || 'available',
})

export const list = async () => {
  if (USE_MOCK) return MOCK_VEHICLES
  const data = await request('/api/vehicles/')
  return (data || []).map(normalizeVehicle)
}

export const create = async (data) => normalizeVehicle(await request('/api/vehicles/', {
  method: 'POST',
  body: {
    code: data.code.trim(),
    name: data.name.trim(),
    capacity_kg: Number(data.capacity),
    status: data.status || 'available',
  },
}))

export const update = async (id, data) => normalizeVehicle(await request(`/api/vehicles/${id}`, {
  method: 'PATCH',
  body: {
    name: data.name.trim(),
    capacity_kg: Number(data.capacity),
    status: data.status,
  },
}))

export const remove = (id) => request(`/api/vehicles/${id}`, { method: 'DELETE' })
