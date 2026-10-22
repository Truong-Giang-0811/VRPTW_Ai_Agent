import { Marker, Popup } from 'react-leaflet'
import L from 'leaflet'

const icon = L.divIcon({ className: '', html: '<div class="pin pin-depot">🏭</div>', iconSize: [36, 36], iconAnchor: [18, 18] })

export default function DepotMarker({ depot }) {
  if (!depot) return null
  return (
    <Marker position={[depot.lat, depot.lng]} icon={icon} zIndexOffset={1000}>
      <Popup>
        <b>{depot.name}</b><br />Giờ mở cửa: {depot.open} – {depot.close}
      </Popup>
    </Marker>
  )
}
