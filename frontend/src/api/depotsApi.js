import { request } from './client'
import { USE_MOCK } from '../constants/config'
import { MOCK_DEPOTS } from '../constants/mockData'

export const normalizeDepot = (d) => ({
  id: d.id,
  name: d.name,
  address: d.address,
  lat: Number(d.latitude ?? d.lat ?? 0),
  lng: Number(d.longitude ?? d.lng ?? 0),
  open: d.open_time ? String(d.open_time).slice(0, 5) : '07:00',
  close: d.close_time ? String(d.close_time).slice(0, 5) : '18:00',
})

export const list = async () => {
  if (USE_MOCK) return MOCK_DEPOTS
  const data = await request('/api/depots/')
  return (data || []).map(normalizeDepot)
}

export const create = async (data) => {
  const payload = {
    name: data.name.trim(),
    address: data.address.trim(),
    latitude: Number(data.lat),
    longitude: Number(data.lng),
    open_time: data.open ? `${data.open}:00` : null,
    close_time: data.close ? `${data.close}:00` : null,
  }
  return normalizeDepot(await request('/api/depots/', { method: 'POST', body: payload }))
}

export const update = async (id, data) => {
  const payload = {
    name: data.name.trim(),
    address: data.address.trim(),
    latitude: Number(data.lat),
    longitude: Number(data.lng),
    ...(data.open ? { open_time: `${data.open}:00` } : {}),
    ...(data.close ? { close_time: `${data.close}:00` } : {}),
  }
  return normalizeDepot(await request(`/api/depots/${id}`, { method: 'PATCH', body: payload }))
}

export const remove = (id) => request(`/api/depots/${id}`, { method: 'DELETE' })
