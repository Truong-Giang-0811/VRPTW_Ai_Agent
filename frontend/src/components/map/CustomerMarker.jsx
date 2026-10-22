import { Marker, Popup } from 'react-leaflet'
import L from 'leaflet'

// color = màu xe (null nếu chưa gán tuyến); seq = số thứ tự giao
export default function CustomerMarker({ stop, color, seq, dimmed, onClick }) {
  const bg = color || '#94a3b8'
  const icon = L.divIcon({
    className: '',
    html: `<div class="pin pin-customer ${dimmed ? 'dimmed' : ''}" style="background:${bg}">${seq ?? '•'}</div>`,
    iconSize: [28, 28], iconAnchor: [14, 14],
  })
  return (
    <Marker position={[stop.lat, stop.lng]} icon={icon} eventHandlers={{ click: onClick }}>
      <Popup>
        <b>{stop.name || stop.customer}</b><br />
        Nhu cầu: {stop.demand} kg
        {stop.arrival && (<><br />Đến: {stop.arrival} · Chờ: {stop.waiting} ph · Đi: {stop.departure}</>)}
        {stop.tw_start && (<><br />Khung giờ: {stop.tw_start} – {stop.tw_end}</>)}
      </Popup>
    </Marker>
  )
}
