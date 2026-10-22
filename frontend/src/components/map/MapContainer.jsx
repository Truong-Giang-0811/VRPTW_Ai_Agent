import { Fragment, useEffect, useMemo, useState } from 'react'
import { MapContainer as LeafletMap, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import DepotMarker from './DepotMarker'
import CustomerMarker from './CustomerMarker'
import RoutePolyline from './RoutePolyline'
import MapLegend from './MapLegend'
import { colorOf } from '../../constants/colors'
import { DEFAULT_CENTER, DEFAULT_ZOOM, TILE_LIGHT, TILE_DARK, TILE_ATTR } from '../../constants/config'

// OSRM public demo server. For production, configure your own OSRM/Valhalla service.
const OSRM_ROUTE_URL = 'https://router.project-osrm.org/route/v1/driving'
const EMPTY_ROUTES = []

function getLatLng(point) {
  const lat = Number(point?.lat ?? point?.latitude)
  const lng = Number(point?.lng ?? point?.longitude ?? point?.lon)
  return Number.isFinite(lat) && Number.isFinite(lng) &&
    Math.abs(lat) <= 90 && Math.abs(lng) <= 180
    ? [lat, lng]
    : null
}

function getStopPoints(route) {
  return (route?.stops || [])
    .map((stop) => getLatLng(stop))
    .filter(Boolean)
}

/**
 * Ask OSRM for road-following geometry for each vehicle route.
 * Coordinate order in the URL is longitude,latitude; GeoJSON output is
 * converted back to Leaflet's [latitude, longitude].
 */
function useRoadRoutes(routes, depot) {
  const [roadRoutes, setRoadRoutes] = useState([])
  const depotPoint = getLatLng(depot)

  useEffect(() => {
    let cancelled = false

    async function loadRoadRoutes() {
      if (!Array.isArray(routes) || routes.length === 0) {
        // Avoid triggering a render loop when the route list is already empty.
        setRoadRoutes((current) => current.length === 0 ? current : [])
        return
      }

      const resolved = await Promise.all(routes.map(async (route) => {
        const stops = getStopPoints(route)
        const sequence = [
          ...(depotPoint ? [depotPoint] : []),
          ...stops,
          ...(depotPoint ? [depotPoint] : []),
        ]

        // A route with no stop coordinate cannot be requested from OSRM.
        if (sequence.length < 2) {
          return { ...route, geometry: Array.isArray(route.geometry) ? route.geometry : [] }
        }

        try {
          const coordinates = sequence
            .map(([lat, lng]) => `${lng},${lat}`)
            .join(';')
          const url = `${OSRM_ROUTE_URL}/${coordinates}?overview=full&geometries=geojson&steps=false`
          const response = await fetch(url)

          if (!response.ok) throw new Error(`OSRM HTTP ${response.status}`)
          const data = await response.json()
          const coords = data?.code === 'Ok' ? data?.routes?.[0]?.geometry?.coordinates : null

          if (!Array.isArray(coords) || coords.length < 2) {
            throw new Error(data?.message || 'OSRM không trả về geometry')
          }

          return {
            ...route,
            geometry: coords.map(([lng, lat]) => [lat, lng]),
            geometry_source: 'osrm',
            road_distance_m: data.routes[0].distance,
            road_duration_s: data.routes[0].duration,
          }
        } catch (error) {
          // Preserve an existing backend geometry if OSRM is temporarily unavailable.
          // If it is only a sequence of stops, it will still look like straight lines.
          console.warn(`Không lấy được đường bộ cho xe ${route.vehicle_id}:`, error)
          return {
            ...route,
            geometry: Array.isArray(route.geometry) ? route.geometry : sequence,
            geometry_source: 'fallback',
          }
        }
      }))

      if (!cancelled) setRoadRoutes(resolved)
    }

    loadRoadRoutes()
    return () => { cancelled = true }
  }, [routes, depotPoint?.[0], depotPoint?.[1]])

  return roadRoutes
}

function FitBounds({ points }) {
  const map = useMap()
  useEffect(() => {
    if (points?.length) map.fitBounds(L.latLngBounds(points), { padding: [60, 60], maxZoom: 15 })
  }, [points, map])
  return null
}

export default function MapContainer({
  theme,
  depot,
  orders = [],
  result,
  focusedRouteId,
  hiddenRoutes = new Set(),
  onToggleRoute,
  onFocusRoute,
}) {
  const routes = result?.routes ?? EMPTY_ROUTES
  const routesWithGeometry = useRoadRoutes(routes, depot)

  const focused = routesWithGeometry.find((r) => r.vehicle_id === focusedRouteId)
  const fitPoints = focused?.geometry?.length
    ? focused.geometry
    : routesWithGeometry.length
      ? routesWithGeometry.flatMap((r) => r.geometry || [])
      : [...orders.map((o) => [Number(o.lat ?? o.latitude), Number(o.lng ?? o.longitude)]),
      ...(depot ? [[Number(depot.lat ?? depot.latitude), Number(depot.lng ?? depot.longitude)]] : [])]
        .filter(([lat, lng]) => Number.isFinite(lat) && Number.isFinite(lng))

  return (
    <div className="map-wrap">
      <LeafletMap center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} zoomControl={false} style={{ height: '100%', width: '100%' }}>
        <TileLayer url={theme === 'dark' ? TILE_DARK : TILE_LIGHT} attribution={TILE_ATTR} />
        <FitBounds points={fitPoints} />
        <DepotMarker depot={depot} />
        {routesWithGeometry.length === 0 && orders.map((o) => <CustomerMarker key={o.id} stop={o} />)}
        {routesWithGeometry.map((route, index) => {
          if (hiddenRoutes.has(route.vehicle_id)) return null
          const dimmed = focusedRouteId != null && focusedRouteId !== route.vehicle_id
          return (
            <Fragment key={route.vehicle_id}>
              <RoutePolyline
                geometry={route.geometry}
                color={colorOf(index)}
                focused={focusedRouteId === route.vehicle_id}
                dimmed={dimmed}
                onClick={() => onFocusRoute?.(route.vehicle_id)}
              />
              {(route.stops || []).map((stop, stopIndex) => (
                <CustomerMarker
                  key={stop.order_id ?? stop.id ?? `${route.vehicle_id}-${stopIndex}`}
                  stop={stop}
                  color={colorOf(index)}
                  seq={stopIndex + 1}
                  dimmed={dimmed}
                  onClick={() => onFocusRoute?.(route.vehicle_id)}
                />
              ))}
            </Fragment>
          )
        })}
      </LeafletMap>
      <MapLegend routes={routesWithGeometry} hidden={hiddenRoutes} focusedId={focusedRouteId} onToggle={onToggleRoute} onFocus={onFocusRoute} />
    </div>
  )
}
