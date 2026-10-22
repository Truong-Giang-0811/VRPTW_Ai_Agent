// Logic thuần cho form thêm đơn: giá trị mặc định, sinh mã, validate.
// Không phụ thuộc React/API nên dễ test và tái sử dụng.

export const generateOrderCode = () => {
  const stamp = Date.now().toString().slice(-6)
  const rand = Math.floor(Math.random() * 90 + 10)
  return `ORD-${stamp}${rand}`
}

export const emptyOrderForm = (deliveryDate) => ({
  code: generateOrderCode(),
  name: '',
  address: '',
  lat: '',
  lng: '',
  demand: '',
  service_min: '10',
  delivery_date: deliveryDate,
  tw_start: '08:00',
  tw_end: '17:00',
})

// Trả về object lỗi theo từng field; rỗng nghĩa là hợp lệ
export function validateOrderForm(f) {
  const errors = {}
  if (!f.code.trim()) errors.code = 'Bắt buộc'
  else if (f.code.length > 30) errors.code = 'Tối đa 30 ký tự'
  if (!f.name.trim()) errors.name = 'Bắt buộc'
  if (!f.address.trim()) errors.address = 'Bắt buộc'

  const lat = Number(f.lat)
  const lng = Number(f.lng)
  if (f.lat === '' || f.lng === '') errors.location = 'Hãy tìm địa chỉ hoặc click lên bản đồ để chọn vị trí giao hàng'
  else if (!Number.isFinite(lat) || lat < -90 || lat > 90) errors.location = 'Vĩ độ phải trong khoảng -90 đến 90'
  else if (!Number.isFinite(lng) || lng < -180 || lng > 180) errors.location = 'Kinh độ phải trong khoảng -180 đến 180'

  if (f.demand === '' || !(Number(f.demand) > 0)) errors.demand = 'Phải lớn hơn 0'
  if (f.service_min === '' || !Number.isInteger(Number(f.service_min)) || Number(f.service_min) < 0) {
    errors.service_min = 'Số nguyên ≥ 0'
  }
  if (!f.delivery_date) errors.delivery_date = 'Bắt buộc'
  if (!f.tw_start || !f.tw_end) errors.time = 'Nhập đủ khung giờ'
  else if (f.tw_start >= f.tw_end) errors.time = 'Giờ mở phải trước giờ đóng'
  return errors
}
