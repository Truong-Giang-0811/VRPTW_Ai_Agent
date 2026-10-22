import { Fragment, useMemo, useState } from 'react'
import { Marker, Polyline, useMap, useMapEvents } from 'react-leaflet'
import L from 'leaflet'

const ARROW_SPACING_PX = 65
const ARROW_TANGENT_PX = 10
const MIN_BEND_ANGLE = 24
const MIN_BEND_SPACING_PX = 28
const iconCache = new Map()

function directionIcon(angle, color, size = 18) {
  const normalizedAngle = Math.round(angle)
  const key = `${color}-${normalizedAngle}-${size}`
  if (iconCache.has(key)) return iconCache.get(key)

  const svg = `
    <svg width="${size}" height="${size}" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"
      style="transform:rotate(${normalizedAngle}deg);filter:drop-shadow(0 1px 1.5px rgba(0,0,0,.65))">
      <path d="M10 1.5 L17 17 L10 13.1 L3 17 Z" fill="${color}" stroke="#fff"
        stroke-width="1.6" stroke-linejoin="round"/>
    </svg>`
  const icon = L.divIcon({
    className: 'route-direction-arrow',
    html: svg,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })
  iconCache.set(key, icon)
  return icon
}

function angleBetween(a, b) {
  const aLen = Math.hypot(a.x, a.y) || 1
  const bLen = Math.hypot(b.x, b.y) || 1
  const dot = (a.x * b.x + a.y * b.y) / (aLen * bLen)
  return Math.acos(Math.max(-1, Math.min(1, dot))) * 180 / Math.PI
}

function getArrowPoints(map, geometry, zoom) {
  if (!Array.isArray(geometry) || geometry.length < 2) return []

  // Work in screen pixels, so spacing and arrow density stay readable at each zoom.
  const points = geometry
    .filter((p) => Array.isArray(p) && p.length >= 2)
    .map((p) => map.project([Number(p[0]), Number(p[1])], zoom))
  if (points.length < 2) return []

  const cumulative = [0]
  for (let i = 1; i < points.length; i++) {
    cumulative.push(cumulative[i - 1] + points[i].distanceTo(points[i - 1]))
  }
  const total = cumulative[cumulative.length - 1]
  if (total < 24) return []

  const sampleAt = (distance) => {
    const d = Math.max(0, Math.min(distance, total))
    let lo = 0
    let hi = cumulative.length - 1
    while (lo < hi - 1) {
      const mid = (lo + hi) >> 1
      if (cumulative[mid] <= d) lo = mid
      else hi = mid
    }
    const segmentLength = cumulative[hi] - cumulative[lo] || 1
    const t = (d - cumulative[lo]) / segmentLength
    return L.point(
      points[lo].x + (points[hi].x - points[lo].x) * t,
      points[lo].y + (points[hi].y - points[lo].y) * t
    )
  }

  const candidates = []
  // Regular arrows along the road geometry.
  for (let d = Math.min(ARROW_SPACING_PX / 2, total / 2); d < total - 10; d += ARROW_SPACING_PX) {
    candidates.push(d)
  }

  // Also put arrows at pronounced bends, using the actual routed geometry vertices.
  for (let i = 1; i < points.length - 1; i++) {
    const incoming = points[i].subtract(points[i - 1])
    const outgoing = points[i + 1].subtract(points[i])
    const bend = angleBetween(incoming, outgoing)
    const d = cumulative[i]
    if (bend >= MIN_BEND_ANGLE && d >= 12 && d <= total - 12) {
      candidates.push(d)
    }
  }

  candidates.sort((a, b) => a - b)
  const filtered = []
  for (const d of candidates) {
    if (filtered.length && d - filtered[filtered.length - 1] < MIN_BEND_SPACING_PX) {
      // Keep a bend arrow over a regular one when they are close together.
      const isBend = points.some((_, i) =>
        i > 0 && i < points.length - 1 &&
        Math.abs(cumulative[i] - d) < 0.5 &&
        angleBetween(points[i].subtract(points[i - 1]), points[i + 1].subtract(points[i])) >= MIN_BEND_ANGLE
      )
      if (isBend) filtered[filtered.length - 1] = d
      continue
    }
    filtered.push(d)
  }

  return filtered.map((d) => {
    const before = sampleAt(Math.max(0, d - ARROW_TANGENT_PX))
    const after = sampleAt(Math.min(total, d + ARROW_TANGENT_PX))
    const at = sampleAt(d)
    // Leaflet's screen Y axis points down. This angle matches the SVG arrow pointing upward.
    const angle = Math.atan2(after.x - before.x, -(after.y - before.y)) * 180 / Math.PI
    return { position: map.unproject(at, zoom), angle }
  })
}

function useZoomLevel() {
  const map = useMap()
  const [zoom, setZoom] = useState(map.getZoom())
  useMapEvents({
    zoomend: () => setZoom(map.getZoom()),
    moveend: () => setZoom(map.getZoom()),
  })
  return zoom
}

export default function RoutePolyline({
  geometry,
  color = '#2563eb',
  focused = false,
  dimmed = false,
  onClick,
}) {
  const map = useMap()
  const zoom = useZoomLevel()
  const safeGeometry = useMemo(
    () => Array.isArray(geometry)
      ? geometry.filter((p) => Array.isArray(p) && p.length >= 2 &&
          Number.isFinite(Number(p[0])) && Number.isFinite(Number(p[1])))
      : [],
    [geometry]
  )
  const arrows = useMemo(
    () => getArrowPoints(map, safeGeometry, zoom),
    [map, safeGeometry, zoom]
  )

  if (safeGeometry.length < 2) return null

  const weight = focused ? 6 : 4
  const opacity = dimmed ? 0.16 : 0.96
  const eventHandlers = onClick ? { click: onClick } : undefined

  return (
    <Fragment>
      {/* White casing keeps overlapping routes distinguishable on the map. */}
      <Polyline
        positions={safeGeometry}
        pathOptions={{
          color: '#fff',
          weight: weight + 3,
          opacity: dimmed ? 0.12 : 0.95,
          lineCap: 'round',
          lineJoin: 'round',
        }}
        interactive={false}
      />
      <Polyline
        positions={safeGeometry}
        pathOptions={{
          color,
          weight,
          opacity,
          lineCap: 'round',
          lineJoin: 'round',
        }}
        eventHandlers={eventHandlers}
      />
      {!dimmed && arrows.map((arrow, index) => (
        <Marker
          key={`${index}-${arrow.position.lat}-${arrow.position.lng}`}
          position={arrow.position}
          icon={directionIcon(arrow.angle, color, focused ? 20 : 17)}
          interactive={false}
          zIndexOffset={focused ? 700 : 400}
        />
      ))}
    </Fragment>
  )
}
