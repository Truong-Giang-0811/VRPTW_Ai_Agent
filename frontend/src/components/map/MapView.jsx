import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap, useMapEvents, ZoomControl } from "react-leaflet";
import L from "leaflet";
import Icon from "../ui/Icon";

const CLUSTER_COLORS = ["#2563eb", "#16a34a", "#dc2626", "#ca8a04", "#7c3aed", "#0891b2", "#db2777", "#0f766e"];

function getClusterColor(clusterId) {
  if (clusterId == null || Number.isNaN(Number(clusterId))) return "#1d4ed8";
  return CLUSTER_COLORS[Math.abs(Number(clusterId)) % CLUSTER_COLORS.length];
}

const depotIcon = L.divIcon({
  className: "custom-marker-wrap",
  html: '<div class="map-marker depot-marker">D</div>',
  iconSize: [38, 38],
  iconAnchor: [19, 19],
});

const customerIcon = (id, clusterId) => {
  const color = getClusterColor(clusterId);
  return L.divIcon({
    className: "custom-marker-wrap",
    html: `<div class="map-marker customer-marker" style="background:${color};box-shadow:0 10px 22px ${color}2a;border-color:${color};">${id}</div>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
  });
};

const selectedIcon = L.divIcon({
  className: "custom-marker-wrap pending-location-wrap",
  html: `
    <div class="pending-location-marker">
      <span class="pending-location-pulse"></span>
      <span class="pending-location-pin">+</span>
    </div>
  `,
  iconSize: [44, 44],
  iconAnchor: [22, 22],
});

function ClickHandler({ onMapClick, interactionMode }) {
  useMapEvents({
    click(e) {
      if (interactionMode !== "pan") onMapClick(e.latlng);
    },
  });
  return null;
}

function MapRecenter({ target }) {
  const map = useMap();

  useEffect(() => {
    if (target) {
      map.flyTo(
        [target.lat, target.lng],
        Math.max(map.getZoom(), 15),
        { duration: 0.7 }
      );
    }
  }, [map, target]);

  return null;
}

function FitBounds({ points, route }) {
  const map = useMap();

  useEffect(() => {
    const source = route?.geometry?.length
      ? route.geometry
      : points.filter(Boolean).map((p) => [p.lat, p.lng]);

    if (source.length > 1) {
      map.fitBounds(L.latLngBounds(source), {
        padding: [60, 60],
        maxZoom: 15,
        animate: true,
      });
    }
  }, [map, points, route]);

  return null;
}

function MapActions({ onZoomToFit, onReset, route }) {
  const map = useMap();

  return (
    <div className="map-action-stack">
      <button type="button" className="map-control" onClick={() => map.zoomIn()} aria-label="Phóng to">
        <Icon name="plus" />
      </button>
      <button type="button" className="map-control" onClick={() => map.zoomOut()} aria-label="Thu nhỏ">
        <Icon name="minus" />
      </button>
      <button
        type="button"
        className="map-control separated"
        onClick={() => map.flyTo([21.0278, 105.8342], 13)}
        aria-label="Về Hà Nội"
        title="Về Hà Nội"
      >
        <Icon name="crosshair" />
      </button>
      {onZoomToFit && (
        <button
          type="button"
          className="map-control"
          onClick={onZoomToFit}
          aria-label="Xem toàn bộ điểm"
          title="Xem toàn bộ điểm"
        >
          <Icon name="target" />
        </button>
      )}
      {route?.geometry?.length > 1 && (
        <button
          type="button"
          className="map-control route-focus-control"
          onClick={() => map.fitBounds(L.latLngBounds(route.geometry), { padding: [60, 60], maxZoom: 16 })}
          aria-label="Xem tuyến đang chọn"
          title="Xem tuyến đang chọn"
        >
          <Icon name="route" />
        </button>
      )}
      {onReset && (
        <button type="button" className="map-control" onClick={onReset} aria-label="Hủy vị trí đang chọn" title="Hủy vị trí đang chọn">
          <Icon name="refresh" />
        </button>
      )}
    </div>
  );
}

export default function MapView({
  depot,
  customers,
  pendingLatLng,
  onMapClick,
  target,
  children,
  interactionMode = "addCustomer",
  onZoomToFit,
  onReset,
  selectedRoute,
  customerClusterMap = {},
}) {
  const center = depot ? [depot.lat, depot.lng] : [21.0278, 105.8342];
  const points = [depot, ...customers];

  return (
    <MapContainer
      center={center}
      zoom={13}
      zoomControl={false}
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      <ZoomControl position="bottomright" />
      <ClickHandler onMapClick={onMapClick} interactionMode={interactionMode} />
      <MapRecenter target={target} />
      <FitBounds points={points} route={selectedRoute} />
      <MapActions onZoomToFit={onZoomToFit} onReset={onReset} route={selectedRoute} />

      {depot && (
        <Marker position={[depot.lat, depot.lng]} icon={depotIcon}>
          <Popup>
            <strong>Kho xuất phát</strong>
            <br />
            Tọa độ: {depot.lat.toFixed(5)}, {depot.lng.toFixed(5)}
            <br />
            {depot.open_time} – {depot.close_time}
          </Popup>
        </Marker>
      )}

      {customers.map((c) => {
        const clusterId = customerClusterMap?.[c.id] ?? customerClusterMap?.[String(c.id)];
        return (
          <Marker key={c.id} position={[c.lat, c.lng]} icon={customerIcon(c.id, clusterId)}>
            <Popup>
              <strong>Khách hàng #{c.id}</strong>
              <br />
              Tọa độ: {c.lat.toFixed(5)}, {c.lng.toFixed(5)}
              <br />
              Demand: {c.demand} kg
              <br />
              Khung giờ: {c.ready_time} – {c.due_time}
              {clusterId != null && (
                <>
                  <br />
                  Cụm: {Number(clusterId) + 1}
                </>
              )}
            </Popup>
          </Marker>
        );
      })}

      {pendingLatLng && (
        <Marker position={[pendingLatLng.lat, pendingLatLng.lng]} icon={selectedIcon} zIndexOffset={1000}>
          <Popup>
            <strong>Vị trí đang chọn</strong>
            <br />
            {pendingLatLng.lat.toFixed(6)}, {pendingLatLng.lng.toFixed(6)}
            <br />
            {interactionMode === "setDepot" ? "Sẽ đặt làm kho" : "Sẽ thêm khách hàng"}
          </Popup>
        </Marker>
      )}

      {children}
    </MapContainer>
  );
}
