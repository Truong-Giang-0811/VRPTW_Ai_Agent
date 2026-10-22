// Khi chạy Vite development, /api đi qua proxy. Với bản preview/build cục bộ,
// gọi trực tiếp Flask (CORS đã được bật) để không phụ thuộc proxy của Vite.
import { API_BASE_URL, apiUrl, ROUTING_URL } from "./apiConfig";

function normalizeRouteGeometry(route) {
  const points = route?.geometry || [];
  return Array.isArray(points) ? points : [];
}

async function loadRoadRoute(route, depot, customersById) {
  const points = [depot, ...route.customer_ids.map((id) => customersById.get(id)), depot];
  if (points.some((point) => !point)) return route;

  const coordinates = points.map((point) => `${point.lng},${point.lat}`).join(";");
  const response = await fetch(
    `${ROUTING_URL}/route/v1/driving/${coordinates}?overview=full&geometries=geojson`
  );
  if (!response.ok) throw new Error("Không thể lấy đường bộ.");
  const road = (await response.json()).routes?.[0];
  if (!road) throw new Error("Không có đường bộ phù hợp giữa các điểm đã chọn.");

  const serviceDuration = route.customer_ids.reduce(
    (sum, id) => sum + Number(customersById.get(id)?.service_time || 0), 0
  );
  return {
    ...route,
    distance_km: Number((road.distance / 1000).toFixed(3)),
    driving_duration_min: Number((road.duration / 60).toFixed(2)),
    duration_min: Number((road.duration / 60 + serviceDuration).toFixed(2)),
    geometry: road.geometry.coordinates.map(([lng, lat]) => [lat, lng]),
    geometry_source: "osrm_browser",
  };
}

async function enrichWithRoadData(result, depot, customers) {
  if (!result) return result;
  if (result.routing_source === "osrm") return result;

  const customersById = new Map(customers.map((customer) => [customer.id, customer]));
  const enriched = await Promise.allSettled(
    (result.routes || []).map((route) => loadRoadRoute(route, depot, customersById))
  );
  const routes = enriched.map((item, index) => item.status === "fulfilled" ? item.value : result.routes[index]);
  const roadRoutes = routes.filter((route) => route.geometry_source === "osrm_browser");
  if (roadRoutes.length === 0) {
    return { ...result, routing_warning: "Không thể cập nhật đường bộ; đang hiển thị tuyến ước lượng." };
  }
  return {
    ...result,
    routes,
    routing_source: "osrm_browser",
    total_distance_km: Number(routes.reduce((sum, route) => sum + route.distance_km, 0).toFixed(3)),
    total_duration_min: Number(routes.reduce((sum, route) => sum + route.duration_min, 0).toFixed(2)),
    routing_warning: roadRoutes.length === routes.length ? undefined : "Một số tuyến đang hiển thị ước lượng.",
  };
}

async function enrichComparisonResult(result, depot, customers) {
  if (!result) return result;
  const enriched = await enrichWithRoadData(result, depot, customers);
  return enriched;
}

export async function optimizeRoutes({ depot, vehicle, customers, algorithm, clusteringMode = "distance", timeWeight = 0.35 }) {
  let res;
  try {
    res = await fetch(apiUrl("/optimize"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        depot,
        vehicle,
        customers,
        algorithm,
        clustering_mode: clusteringMode,
        time_weight: timeWeight,
      }),
    });
  } catch {
    throw new Error(
      `Không kết nối được backend tại ${API_BASE_URL}. Hãy khởi động backend ở cổng 5001.`
    );
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Tối ưu thất bại");
  }

  return enrichWithRoadData(await res.json(), depot, customers);
}

export async function optimizeComparison({ depot, vehicle, customers, algorithm, timeWeight = 0.35 }) {
  let res;
  try {
    res = await fetch(apiUrl("/optimize/compare"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        depot,
        vehicle,
        customers,
        algorithm,
        time_weight: timeWeight,
      }),
    });
  } catch {
    throw new Error(
      `Không kết nối được backend tại ${API_BASE_URL}. Hãy khởi động backend ở cổng 5001.`
    );
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Tối ưu thất bại");
  }

  const payload = await res.json();
  const [distanceBased, spatiotemporalBased] = await Promise.all([
    enrichComparisonResult(payload.distance_based, depot, customers),
    enrichComparisonResult(payload.spatiotemporal_based, depot, customers),
  ]);

  return {
    distance_based: distanceBased,
    spatiotemporal_based: spatiotemporalBased,
  };
}
