// Bảng màu cho từng tuyến xe (lặp vòng nếu nhiều xe hơn số màu)
export const ROUTE_COLORS = [
  '#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444',
  '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1',
]
export const colorOf = (index) => ROUTE_COLORS[index % ROUTE_COLORS.length]
