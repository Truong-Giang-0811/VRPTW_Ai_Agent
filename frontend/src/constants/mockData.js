// Dữ liệu giả CHỈ để dựng giao diện. Hình dạng này là GIẢ ĐỊNH — chỉnh lại theo response thật của backend.
export const MOCK_DEPOTS = [
  { id: 1, name: 'Kho Cầu Giấy', lat: 21.0333, lng: 105.7906, open: '06:00', close: '22:00' },
  { id: 2, name: 'Kho Long Biên', lat: 21.0453, lng: 105.8890, open: '07:00', close: '21:00' },
]
export const MOCK_VEHICLES = [
  { id: 1, name: 'Xe 01', capacity: 1000 }, { id: 2, name: 'Xe 02', capacity: 1000 }, { id: 3, name: 'Xe 03', capacity: 800 },
]
export const MOCK_ORDERS = [
  { id: 101, customer: 'Cửa hàng A', lat: 21.0245, lng: 105.8412, demand: 120, tw_start: '08:00', tw_end: '11:00', service_min: 10 },
  { id: 102, customer: 'Cửa hàng B', lat: 21.0071, lng: 105.8431, demand: 200, tw_start: '09:00', tw_end: '12:00', service_min: 15 },
  { id: 103, customer: 'Siêu thị C', lat: 21.0366, lng: 105.8344, demand: 350, tw_start: '08:30', tw_end: '14:00', service_min: 20 },
  { id: 104, customer: 'Nhà hàng D', lat: 21.0583, lng: 105.8196, demand: 90, tw_start: '10:00', tw_end: '13:00', service_min: 10 },
  { id: 105, customer: 'Đại lý E', lat: 21.0153, lng: 105.8010, demand: 260, tw_start: '08:00', tw_end: '15:00', service_min: 15 },
  { id: 106, customer: 'Cửa hàng F', lat: 21.0480, lng: 105.8700, demand: 140, tw_start: '09:30', tw_end: '16:00', service_min: 10 },
]
const mk = (vid, name, cap, load, km, end, stops, geometry) => ({ vehicle_id: vid, vehicle_name: name, capacity: cap, load, distance_km: km, end_time: end, stops, geometry })
export const MOCK_RESULT = {
  mode: 'spatiotemporal', total_distance_km: 31.4, total_time_min: 312, violations: 0,
  routes: [
    mk(1, 'Xe 01', 1000, 670, 14.2, '12:10', [
      { order_id: 101, name: 'Cửa hàng A', lat: 21.0245, lng: 105.8412, demand: 120, arrival: '08:20', waiting: 0, service_start: '08:20', departure: '08:30' },
      { order_id: 103, name: 'Siêu thị C', lat: 21.0366, lng: 105.8344, demand: 350, arrival: '08:48', waiting: 0, service_start: '08:48', departure: '09:08' },
      { order_id: 104, name: 'Nhà hàng D', lat: 21.0583, lng: 105.8196, demand: 90, arrival: '09:30', waiting: 30, service_start: '10:00', departure: '10:10' },
    ], [[21.0333,105.7906],[21.0245,105.8412],[21.0366,105.8344],[21.0583,105.8196],[21.0333,105.7906]]),
    mk(2, 'Xe 02', 1000, 460, 17.2, '13:05', [
      { order_id: 102, name: 'Cửa hàng B', lat: 21.0071, lng: 105.8431, demand: 200, arrival: '09:00', waiting: 0, service_start: '09:00', departure: '09:15' },
      { order_id: 105, name: 'Đại lý E', lat: 21.0153, lng: 105.8010, demand: 260, arrival: '09:50', waiting: 0, service_start: '09:50', departure: '10:05' },
    ], [[21.0333,105.7906],[21.0071,105.8431],[21.0153,105.8010],[21.0333,105.7906]]),
  ],
}
export const MOCK_HISTORY = [
  { id: 12, date: '2026-10-11', depot: 'Kho Cầu Giấy', vehicles: 2, orders: 6, distance_km: 31.4, mode: 'spatiotemporal' },
  { id: 11, date: '2026-10-10', depot: 'Kho Long Biên', vehicles: 3, orders: 9, distance_km: 44.8, mode: 'distance' },
]
