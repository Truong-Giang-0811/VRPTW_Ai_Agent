import { useEffect } from 'react'
import { MapContainer as LeafletMap, TileLayer, Marker, useMap, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import { TILE_LIGHT, TILE_ATTR } from '../../constants/config'

const pickIcon = L.divIcon({
  className: '',
  html: '<div class="pin pin-customer" style="background:#ef4444">📍</div>',
  iconSize: [28, 28], iconAnchor: [14, 14],
})

function ClickHandler({ onPick }) {
  useMapEvents({ click: (e) => onPick(e.latlng.lat, e.latlng.lng) })
  return null
}

// Bay tới vị trí khi cha đặt focus mới (vd chọn kết quả tìm kiếm); click bản đồ không làm bản đồ nhảy
function FlyTo({ focus }) {
  const map = useMap()
  useEffect(() => {
    if (focus) map.flyTo([focus.lat, focus.lng], focus.zoom ?? 17, { duration: 0.8 })
  }, [focus, map])
  return null
}

// Chọn toạ độ bằng click hoặc kéo marker. value = { lat, lng } | null; focus = { lat, lng, zoom? } | null
export default function LocationPicker({ value, center, zoom, focus, onPick }) {
  return (
    <div className="location-picker">
      <LeafletMap center={value || center} zoom={zoom} style={{ height: '100%', width: '100%' }}>
        <TileLayer url={TILE_LIGHT} attribution={TILE_ATTR} />
        <ClickHandler onPick={onPick} />
        <FlyTo focus={focus} />
        {value && (
          <Marker
            position={[value.lat, value.lng]}
            icon={pickIcon}
            draggable
            eventHandlers={{ dragend: (e) => { const p = e.target.getLatLng(); onPick(p.lat, p.lng) } }}
          />
        )}
      </LeafletMap>
    </div>
  )
}
