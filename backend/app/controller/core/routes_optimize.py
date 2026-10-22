import math
import sys
from datetime import date, datetime, timedelta, time as dt_time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from requests import RequestException
from sqlalchemy.orm import Session

# Đảm bảo thư mục core nằm trong sys.path để các module nội bộ import được nhau
CORE_DIR = Path(__file__).resolve().parent
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from app.database.connect_db import get_db
from app.models import DeliveryOrder, Depot, RoutePlan, RouteStop, Vehicle, VehicleRoute
from app.services.optimization_input_service import build_optimization_input
from app.services.what_if_service import run_what_if

from distance_provider import (
    DISTANCE_PROVIDER,
    EuclideanProvider,
    get_distance_provider,
    get_osrm_route,
)
from readDataFile import Customer
from solver import solve

router = APIRouter(prefix="/api/routes", tags=["Routing Optimization"])


def _extract_coords(point: Dict[str, Any]) -> Tuple[float, float]:
    """Trích xuất (lat, lng) từ dict điểm đầu vào."""
    lat = point.get("lat") if "lat" in point else point.get("latitude")
    lng = (
        point.get("lng")
        if "lng" in point
        else point.get("lon")
        if "lon" in point
        else point.get("longitude")
    )

    if lat is None or lng is None:
        raise ValueError(f"Thiếu tọa độ lat/lng trong điểm: {point}")

    return float(lat), float(lng)


def _parse_time_to_minutes(val: Any, default: float = 0.0) -> float:
    """Chuyển đổi thời gian (số phút, giờ dạng 'HH:MM', hoặc đối tượng datetime.time) sang số phút."""
    if val is None:
        return default
    if isinstance(val, (int, float, np.number)):
        return float(val)
    if isinstance(val, dt_time):
        return float(val.hour * 60 + val.minute)
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str:
            return default
        if ":" in val_str:
            parts = val_str.split(":")
            try:
                hours = int(parts[0])
                minutes = int(parts[1]) if len(parts) > 1 else 0
                return float(hours * 60 + minutes)
            except ValueError:
                return default
        try:
            return float(val_str)
        except ValueError:
            return default
    return default


def _prepare_customers_and_points(
    depot_raw: Dict[str, Any], customers_raw: List[Dict[str, Any]]
) -> Tuple[List[Customer], List[Dict[str, float]]]:
    """Chuyển đổi depot và danh sách customers sang Customer namedtuple và danh sách điểm cho provider."""
    depot_lat, depot_lng = _extract_coords(depot_raw)
    depot_ready = _parse_time_to_minutes(
        depot_raw.get("ready_time") or depot_raw.get("readyTime") or depot_raw.get("open_time"),
        default=0.0,
    )
    depot_due = _parse_time_to_minutes(
        depot_raw.get("due_time") or depot_raw.get("dueTime") or depot_raw.get("close_time"),
        default=1440.0,
    )

    depot_customer = Customer(
        id=depot_raw.get("id", 0),
        xy_coord=np.array([depot_lat, depot_lng], dtype=float),
        demand=0.0,
        readyTime=depot_ready,
        dueTime=depot_due,
        serviceTime=0.0,
    )

    all_customers: List[Customer] = [depot_customer]
    points_for_provider: List[Dict[str, float]] = [{"lat": depot_lat, "lng": depot_lng}]

    for idx, c in enumerate(customers_raw, start=1):
        c_lat, c_lng = _extract_coords(c)
        c_ready = _parse_time_to_minutes(
            c.get("ready_time") or c.get("readyTime") or c.get("open_time"),
            default=depot_ready,
        )
        c_due = _parse_time_to_minutes(
            c.get("due_time") or c.get("dueTime") or c.get("close_time"),
            default=depot_due,
        )
        c_service = float(
            c.get("service_time")
            or c.get("serviceTime")
            or c.get("service_duration_min")
            or 0.0
        )
        c_demand = float(c.get("demand") or c.get("demand_weight_kg") or 0.0)
        c_id = c.get("id", idx)

        cust_obj = Customer(
            id=c_id,
            xy_coord=np.array([c_lat, c_lng], dtype=float),
            demand=c_demand,
            readyTime=c_ready,
            dueTime=c_due,
            serviceTime=c_service,
        )
        all_customers.append(cust_obj)
        points_for_provider.append({"lat": c_lat, "lng": c_lng})

    return all_customers, points_for_provider


def _enrich_osrm_routes(
    response: dict,
    depot_raw: dict,
    customers_input: list,
    routing_fallback: bool,
) -> dict:
    """Bổ sung polyline geometry thực tế từ OSRM nếu có thể."""
    response["routing_source"] = "euclidean_fallback" if routing_fallback else DISTANCE_PROVIDER
    if DISTANCE_PROVIDER != "osrm" or routing_fallback:
        return response

    depot_lat, depot_lng = _extract_coords(depot_raw)
    depot_point = {"lat": depot_lat, "lng": depot_lng}

    points_by_id: Dict[Any, Dict[str, float]] = {}
    for c in customers_input:
        try:
            c_lat, c_lng = _extract_coords(c)
            c_point = {"lat": c_lat, "lng": c_lng}
            if "id" in c:
                points_by_id[c["id"]] = c_point
                points_by_id[str(c["id"])] = c_point
        except Exception:
            continue

    for route in response.get("routes", []):
        try:
            route_points = [depot_point]
            for item in route.get("customer_ids", []):
                pt = points_by_id.get(item) or points_by_id.get(str(item))
                if pt:
                    route_points.append(pt)
            route_points.append(depot_point)

            if len(route_points) > 2:
                route["geometry"] = [[lat, lng] for lng, lat in get_osrm_route(route_points)]
                route["geometry_source"] = "osrm"
        except (KeyError, IndexError, TypeError, ValueError, RequestException):
            pass

    return response


# Schema tiếp nhận dữ liệu từ Client
class OptimizeRequest(BaseModel):
    depot: Dict[str, Any]
    customers: List[Dict[str, Any]]
    vehicles: Optional[List[Dict[str, Any]]] = None
    vehicle_number: Optional[int] = None
    vehicle_capacity: Optional[float] = 100.0
    algorithm: Optional[str] = "GA"
    cluster_mode: Optional[str] = None
    clustering_mode: Optional[str] = "distance"
    time_weight: Optional[float] = 0.35


def _solve_vrptw(
    payload: OptimizeRequest,
    clustering_mode_override: Optional[str] = None,
    enrich_geometry: bool = True,
) -> dict:
    data = payload.dict()
    depot = data.get("depot")
    customers = data.get("customers", [])

    if not depot or not customers:
        raise HTTPException(status_code=400, detail="Thiếu dữ liệu depot hoặc danh sách customers")

    # 1. Chuyển đổi dữ liệu sang định dạng của solver
    try:
        all_customers, points_for_provider = _prepare_customers_and_points(depot, customers)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Dữ liệu đầu vào không hợp lệ: {str(e)}")

    # 2. Xác định cấu hình xe
    vehicles = data.get("vehicles") or []
    vehicle_capacity = float(data.get("vehicle_capacity") or 100.0)
    if vehicles and "capacity" in vehicles[0] and vehicles[0]["capacity"]:
        vehicle_capacity = float(vehicles[0]["capacity"])

    if data.get("vehicle_number") and int(data.get("vehicle_number")) > 0:
        vehicle_number = int(data.get("vehicle_number"))
    elif len(vehicles) > 0:
        vehicle_number = len(vehicles)
    else:
        total_demand = sum(float(c.demand) for c in all_customers[1:])
        min_vehicles = max(1, math.ceil(total_demand / vehicle_capacity)) if vehicle_capacity > 0 else 1
        vehicle_number = max(min_vehicles, min(len(customers), 5))

    algorithm = str(data.get("algorithm") or "GA").upper()
    clustering_mode = (
        clustering_mode_override
        or data.get("clustering_mode")
        or data.get("cluster_mode")
        or "distance"
    ).lower()
    time_weight = float(data.get("time_weight") if data.get("time_weight") is not None else 0.35)

    # 3. Tính toán ma trận khoảng cách & thời gian
    provider = get_distance_provider()
    routing_fallback = False

    try:
        distance_matrix, duration_matrix = provider.build_matrix(points_for_provider)
    except Exception:
        # Nếu OSRM lỗi hoặc mất mạng, fallback về Euclidean (Haversine)
        distance_matrix, duration_matrix = EuclideanProvider().build_matrix(points_for_provider)
        routing_fallback = True

    # 4. Gọi bộ giải VRPTW
    try:
        result = solve(
            customers=all_customers,
            duration_matrix=duration_matrix,
            distance_matrix=distance_matrix,
            vehicle_number=vehicle_number,
            vehicle_capacity=vehicle_capacity,
            algorithm=algorithm,
            clustering_mode=clustering_mode,
            time_weight=time_weight,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Lỗi ràng buộc dữ liệu: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tối ưu: {str(e)}")

    # 5. Thêm đường vẽ thực tế OSRM nếu cần hiển thị bản đồ
    if enrich_geometry:
        result_with_geometry = _enrich_osrm_routes(result, depot, customers, routing_fallback)
    else:
        result_with_geometry = result
    return result_with_geometry


@router.post("/optimize")
async def optimize_routes(payload: OptimizeRequest):
    """Tối ưu hóa tuyến đường VRPTW theo cấu hình yêu cầu."""
    return _solve_vrptw(payload)


@router.post("/optimize/compare")
async def compare_clustering_modes(payload: OptimizeRequest):
    """So sánh kết quả tối ưu giữa 2 chế độ phân cụm: Distance vs Spatiotemporal."""
    res_distance = _solve_vrptw(payload, clustering_mode_override="distance")
    res_spatiotemporal = _solve_vrptw(payload, clustering_mode_override="spatiotemporal")

    return {
        "distance_mode": res_distance,
        "spatiotemporal_mode": res_spatiotemporal,
        "comparison": {
            "distance_total_km": res_distance.get("total_distance"),
            "spatiotemporal_total_km": res_spatiotemporal.get("total_distance"),
            "distance_total_min": res_distance.get("total_duration"),
            "spatiotemporal_total_min": res_spatiotemporal.get("total_duration"),
            "distance_waiting_min": res_distance.get("total_waiting_time"),
            "spatiotemporal_waiting_min": res_spatiotemporal.get("total_waiting_time"),
            "distance_vehicle_count": res_distance.get("vehicle_count"),
            "spatiotemporal_vehicle_count": res_spatiotemporal.get("vehicle_count"),
        },
    }


# ============================================================================
# CÁC SCHEMA & ENDPOINT HỖ TRỢ LƯU CSDL (QUY TRÌNH 2 BƯỚC)
# ============================================================================

class SavePlanRequest(BaseModel):
    depot_id: int
    delivery_date: date
    objective: Optional[str] = "minimize_distance"
    algorithm: Optional[str] = "GA"
    status: Optional[str] = "confirmed"
    total_distance: Optional[float] = None
    total_duration: Optional[float] = None
    vehicle_ids: Optional[List[int]] = None
    routes: List[Dict[str, Any]]
    auto_update_orders_status: Optional[bool] = True


class OptimizeFromDbRequest(BaseModel):
    depot_id: int
    delivery_date: date
    vehicle_capacity: Optional[float] = 100.0
    vehicle_number: Optional[int] = None
    algorithm: Optional[str] = "GA"
    cluster_mode: Optional[str] = None
    clustering_mode: Optional[str] = "distance"
    time_weight: Optional[float] = 0.35
    order_ids: Optional[List[int]] = None


@router.post("/save-plan")
def save_route_plan(payload: SavePlanRequest, db: Session = Depends(get_db)):
    """
    Bước 2 trong quy trình 2 bước:
    Nhận kết quả tối ưu từ /optimize (hoặc cấu hình tuyến) và lưu vào Database:
    1. Tạo RoutePlan
    2. Tạo VehicleRoute cho từng xe
    3. Tạo RouteStop cho từng điểm dừng (kèm mốc thời gian arrival/departure)
    4. Cập nhật trạng thái các DeliveryOrder sang 'assigned'
    """
    depot = db.query(Depot).filter(Depot.id == payload.depot_id).first()
    if not depot:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy kho hàng (depot_id={payload.depot_id})")

    if not payload.routes:
        raise HTTPException(status_code=400, detail="Danh sách routes trống, không có dữ liệu để lưu")

    # 1. Tính toán số liệu thống kê tổng thể
    total_distance = (
        float(payload.total_distance)
        if payload.total_distance is not None
        else sum(float(r.get("distance_km") or 0.0) for r in payload.routes)
    )
    total_duration = (
        float(payload.total_duration)
        if payload.total_duration is not None
        else sum(float(r.get("duration_min") or 0.0) for r in payload.routes)
    )

    all_customer_ids = set()
    for r in payload.routes:
        c_ids = r.get("customer_ids") or [
            item.get("customer_id")
            for item in r.get("timeline", [])
            if item.get("customer_id")
        ]
        all_customer_ids.update([int(cid) for cid in c_ids if cid is not None])

    # 2. Phân bổ vehicle_id cho từng tuyến
    assigned_vehicle_ids: List[int] = []
    explicit_vehicle_ids = payload.vehicle_ids or []

    for idx, r in enumerate(payload.routes):
        v_id = r.get("vehicle_id")
        if not v_id and idx < len(explicit_vehicle_ids):
            v_id = explicit_vehicle_ids[idx]
        if v_id:
            assigned_vehicle_ids.append(int(v_id))
        else:
            assigned_vehicle_ids.append(0)

    # Nếu còn tuyến chưa có vehicle_id, tự động lấy các Vehicle khả dụng từ DB
    missing_indices = [i for i, vid in enumerate(assigned_vehicle_ids) if vid == 0]
    if missing_indices:
        used_ids = {vid for vid in assigned_vehicle_ids if vid > 0}
        available_vehicles = (
            db.query(Vehicle)
            .filter(~Vehicle.id.in_(used_ids) if used_ids else True)
            .all()
        )
        if len(available_vehicles) < len(missing_indices):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cần {len(payload.routes)} phương tiện nhưng chỉ có "
                    f"{len(used_ids) + len(available_vehicles)} phương tiện trong hệ thống. "
                    "Vui lòng tạo thêm phương tiện hoặc truyền danh sách vehicle_ids."
                ),
            )
        for i, vehicle in zip(missing_indices, available_vehicles):
            assigned_vehicle_ids[i] = vehicle.id

    # Đảm bảo không trùng lặp vehicle_id trong cùng một plan (ràng buộc uq_plan_vehicle)
    if len(set(assigned_vehicle_ids)) != len(assigned_vehicle_ids):
        raise HTTPException(
            status_code=400,
            detail="Các tuyến xe không được trùng lặp phương tiện (vehicle_id).",
        )

    depot_start_min = _parse_time_to_minutes(depot.open_time, default=420.0)

    # 3. Mở Transaction để ghi vào Database
    try:
        # A. Tạo RoutePlan
        plan = RoutePlan(
            depot_id=payload.depot_id,
            delivery_date=payload.delivery_date,
            objective=payload.objective or "minimize_distance",
            algorithm=payload.algorithm or "GA",
            total_distance_km=round(total_distance, 3),
            total_duration_min=round(total_duration, 2),
            total_customers=len(all_customer_ids),
            status=payload.status or "confirmed",
        )
        db.add(plan)
        db.flush()

        assigned_order_ids_to_update = set()

        # B. Duyệt qua từng tuyến để tạo VehicleRoute và RouteStop
        for r_idx, r in enumerate(payload.routes):
            v_id = assigned_vehicle_ids[r_idx]
            v_route = VehicleRoute(
                route_plan_id=plan.id,
                vehicle_id=v_id,
                total_load_kg=float(r.get("load") or 0.0),
                total_distance_km=float(r.get("distance_km") or 0.0),
                total_duration_min=float(r.get("duration_min") or 0.0),
            )
            db.add(v_route)
            db.flush()

            timeline = r.get("timeline") or []

            # Điểm xuất phát tại kho (Sequence = 0)
            depot_start_dt = datetime.combine(payload.delivery_date, dt_time.min) + timedelta(minutes=depot_start_min)
            depot_start_stop = RouteStop(
                vehicle_route_id=v_route.id,
                delivery_order_id=None,
                sequence=0,
                stop_type="depot_start",
                departure_time=depot_start_dt,
                distance_from_previous_km=0.0,
            )
            db.add(depot_start_stop)

            # Các điểm giao hàng
            seq_counter = 1
            if timeline:
                for item in timeline:
                    cust_id = item.get("customer_id")
                    if cust_id is not None:
                        cust_id = int(cust_id)
                        assigned_order_ids_to_update.add(cust_id)

                    arr_min = item.get("arrival_min")
                    srv_min = item.get("service_start_min")
                    dep_min = item.get("departure_min")

                    arr_dt = (
                        datetime.combine(payload.delivery_date, dt_time.min) + timedelta(minutes=float(arr_min))
                        if arr_min is not None
                        else None
                    )
                    srv_dt = (
                        datetime.combine(payload.delivery_date, dt_time.min) + timedelta(minutes=float(srv_min))
                        if srv_min is not None
                        else None
                    )
                    dep_dt = (
                        datetime.combine(payload.delivery_date, dt_time.min) + timedelta(minutes=float(dep_min))
                        if dep_min is not None
                        else None
                    )

                    stop = RouteStop(
                        vehicle_route_id=v_route.id,
                        delivery_order_id=cust_id,
                        sequence=int(item.get("order", seq_counter)),
                        stop_type="delivery",
                        arrival_time=arr_dt,
                        service_start_time=srv_dt,
                        departure_time=dep_dt,
                        distance_from_previous_km=float(item.get("travel_distance_km") or 0.0),
                    )
                    db.add(stop)
                    seq_counter += 1
            else:
                for cust_id in r.get("customer_ids", []):
                    c_id = int(cust_id)
                    assigned_order_ids_to_update.add(c_id)
                    stop = RouteStop(
                        vehicle_route_id=v_route.id,
                        delivery_order_id=c_id,
                        sequence=seq_counter,
                        stop_type="delivery",
                        distance_from_previous_km=0.0,
                    )
                    db.add(stop)
                    seq_counter += 1

            # Điểm kết thúc về kho (Sequence = seq_counter)
            finish_min = r.get("finish_min")
            finish_dt = (
                datetime.combine(payload.delivery_date, dt_time.min) + timedelta(minutes=float(finish_min))
                if finish_min is not None
                else None
            )
            depot_end_stop = RouteStop(
                vehicle_route_id=v_route.id,
                delivery_order_id=None,
                sequence=seq_counter,
                stop_type="depot_end",
                arrival_time=finish_dt,
                distance_from_previous_km=0.0,
            )
            db.add(depot_end_stop)

        # C. Cập nhật trạng thái các đơn hàng sang 'assigned'
        if payload.auto_update_orders_status and assigned_order_ids_to_update:
            db.query(DeliveryOrder).filter(
                DeliveryOrder.id.in_(assigned_order_ids_to_update)
            ).update({"status": "assigned"}, synchronize_session=False)

        db.commit()
        db.refresh(plan)

        return {
            "message": "Đã lưu kế hoạch tối ưu tuyến đường vào CSDL thành công",
            "route_plan_id": plan.id,
            "depot_id": plan.depot_id,
            "delivery_date": str(plan.delivery_date),
            "total_routes": len(payload.routes),
            "total_customers": plan.total_customers,
            "total_distance_km": plan.total_distance_km,
            "total_duration_min": plan.total_duration_min,
            "status": plan.status,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi lưu kế hoạch vào CSDL: {str(e)}")


@router.post("/optimize-from-db")
def optimize_routes_from_db(payload: OptimizeFromDbRequest, db: Session = Depends(get_db)):
    """
    Tự động truy vấn dữ liệu từ DB (kho hàng + các đơn hàng trong ngày)
    rồi chạy thuật toán tối ưu VRPTW và trả về kết quả xem trước (preview).
    """
    depot = db.query(Depot).filter(Depot.id == payload.depot_id).first()
    if not depot:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy kho hàng (depot_id={payload.depot_id})")

    orders_query = db.query(DeliveryOrder).filter(DeliveryOrder.delivery_date == payload.delivery_date)
    if payload.order_ids:
        orders_query = orders_query.filter(DeliveryOrder.id.in_(payload.order_ids))
    else:
        # Mặc định lấy các đơn chưa được xếp xe (status = 'pending')
        orders_query = orders_query.filter(DeliveryOrder.status == "pending")

    orders = orders_query.all()
    if not orders:
        raise HTTPException(
            status_code=400,
            detail=f"Không tìm thấy đơn hàng khả dụng nào (pending) cho ngày {payload.delivery_date}",
        )

    # Chuyển đổi dữ liệu sang schema OptimizeRequest
    depot_raw = {
        "id": depot.id,
        "name": depot.name,
        "lat": depot.latitude,
        "lng": depot.longitude,
        "ready_time": depot.open_time.strftime("%H:%M") if depot.open_time else "07:00",
        "due_time": depot.close_time.strftime("%H:%M") if depot.close_time else "18:00",
    }

    customers_raw = [
        {
            "id": o.id,
            "code": o.code,
            "name": o.name,
            "lat": o.latitude,
            "lng": o.longitude,
            "demand": float(o.demand_weight_kg),
            "service_time": float(o.service_duration_min),
            "ready_time": o.open_time.strftime("%H:%M") if o.open_time else "07:00",
            "due_time": o.close_time.strftime("%H:%M") if o.close_time else "18:00",
        }
        for o in orders
    ]

    vehicles = db.query(Vehicle).filter(Vehicle.status == "available").all()
    vehicles_raw = [{"id": v.id, "capacity": v.capacity_kg, "code": v.code, "name": v.name} for v in vehicles]

    opt_payload = OptimizeRequest(
        depot=depot_raw,
        customers=customers_raw,
        vehicles=vehicles_raw if vehicles_raw else None,
        vehicle_capacity=payload.vehicle_capacity,
        vehicle_number=payload.vehicle_number or (len(vehicles_raw) if vehicles_raw else None),
        algorithm=payload.algorithm,
        cluster_mode=payload.cluster_mode,
        clustering_mode=payload.clustering_mode,
        time_weight=payload.time_weight,
    )

    result = _solve_vrptw(opt_payload)
    result["depot_id"] = depot.id
    result["delivery_date"] = str(payload.delivery_date)
    return result


# ============================================================================
# ENDPOINTS LỊCH SỬ KẾ HOẠCH & AI AGENT COPILOT
# ============================================================================

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, Any]]] = None
    depot_id: Optional[int] = None
    delivery_date: Optional[date] = None
    vehicle_capacity: Optional[float] = 1000.0


@router.get("/plans")
def list_plans(db: Session = Depends(get_db)):
    """Liệt kê danh sách các kế hoạch đã lưu trong hệ thống."""
    plans = db.query(RoutePlan).order_by(RoutePlan.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "date": str(p.delivery_date),
            "depot_id": p.depot_id,
            "depot": p.depot.name if p.depot else f"Kho #{p.depot_id}",
            "vehicles": len(p.vehicle_routes),
            "orders": p.total_customers,
            "distance_km": p.total_distance_km,
            "duration_min": p.total_duration_min,
            "mode": p.objective or "spatiotemporal",
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in plans
    ]


@router.get("/plans/{plan_id}")
def get_plan_details(plan_id: int, db: Session = Depends(get_db)):
    """Lấy chi tiết một kế hoạch kèm danh sách xe, trạm dừng và đường vẽ để tải lại lên Map."""
    plan = db.query(RoutePlan).filter(RoutePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Không tìm thấy kế hoạch lộ trình")

    depot = plan.depot
    depot_coord = [depot.latitude, depot.longitude] if depot else [0.0, 0.0]

    routes_data = []
    for vr in plan.vehicle_routes:
        stops_data = []
        route_coords = [depot_coord]

        for s in vr.stops:
            if s.stop_type == "delivery" and s.delivery_order:
                ord_item = s.delivery_order
                coord = [ord_item.latitude, ord_item.longitude]
                route_coords.append(coord)
                stops_data.append({
                    "order_id": ord_item.id,
                    "customer_id": ord_item.id,
                    "name": ord_item.name,
                    "lat": ord_item.latitude,
                    "lng": ord_item.longitude,
                    "demand": ord_item.demand_weight_kg,
                    "arrival": s.arrival_time.strftime("%H:%M") if s.arrival_time else "--:--",
                    "departure": s.departure_time.strftime("%H:%M") if s.departure_time else "--:--",
                    "service_start": s.service_start_time.strftime("%H:%M") if s.service_start_time else "--:--",
                    "waiting": 0,
                    "sequence": s.sequence,
                })
        route_coords.append(depot_coord)

        routes_data.append({
            "vehicle_id": vr.vehicle_id,
            "vehicle_name": vr.vehicle.name if vr.vehicle else f"Xe #{vr.vehicle_id}",
            "capacity": vr.vehicle.capacity_kg if vr.vehicle else 1000.0,
            "load": vr.total_load_kg,
            "distance_km": vr.total_distance_km,
            "duration_min": vr.total_duration_min,
            "stops": stops_data,
            "geometry": route_coords,
        })

    return {
        "id": plan.id,
        "date": str(plan.delivery_date),
        "depot_id": plan.depot_id,
        "mode": plan.objective,
        "total_distance_km": plan.total_distance_km,
        "total_time_min": plan.total_duration_min,
        "routes": routes_data,
        "violations": 0,
    }


class WhatIfRequest(BaseModel):
    """Thay đổi giả định cho một kế hoạch đã lưu; không ghi vào MySQL."""
    changes: Dict[str, Any]


@router.get("/plans/{plan_id}/optimization-input")
def get_plan_optimization_input(plan_id: int, db: Session = Depends(get_db)):
    """Đọc và chuẩn hóa dữ liệu cần thiết để chạy What-if cho một kế hoạch."""
    if plan_id <= 0:
        raise HTTPException(status_code=422, detail="plan_id phải lớn hơn 0.")
    try:
        result = build_optimization_input(db, plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy kế hoạch {plan_id}.")
    return result


@router.post("/plans/{plan_id}/what-if")
def run_what_if_for_plan(
    plan_id: int,
    payload: WhatIfRequest,
    db: Session = Depends(get_db),
):
    """Chạy kịch bản What-if trong RAM, không lưu hoặc sửa dữ liệu nghiệp vụ."""
    if plan_id <= 0:
        raise HTTPException(status_code=422, detail="plan_id phải lớn hơn 0.")

    def solve_payload(data: dict[str, Any]) -> dict[str, Any]:
        return _solve_vrptw(OptimizeRequest(**data), enrich_geometry=False)

    try:
        result = run_what_if(
            db=db,
            plan_id=plan_id,
            changes=payload.changes,
            solve_payload=solve_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=result.get("error", "Không tìm thấy kế hoạch."))
    return result


@router.post("/chat/agent")
def chat_with_agent(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    Trợ lý AI Copilot VRPTW:
    Nhận tin nhắn của người điều phối, phân tích ý định và gọi công cụ (tool calling):
    - Tối ưu hóa đơn hàng
    - So sánh thuật toán / phân cụm
    - Trả lời thống kê đội xe và kho hàng
    """
    msg = payload.message.lower().strip()
    depot_id = payload.depot_id or 1
    delivery_date = payload.delivery_date or date.today()

    # Kịch bản 1: Yêu cầu tối ưu hóa hoặc chạy tuyến
    if any(k in msg for k in ["tối ưu", "tìm đường", "giải", "chạy lại", "optimize", "phân tuyến"]):
        mode = "spatiotemporal" if ("thời gian" in msg or "spatiotemporal" in msg) else "distance"
        algo = "GA"
        if "aco" in msg:
            algo = "ACO"
        elif "pso" in msg:
            algo = "PSO"

        try:
            opt_req = OptimizeFromDbRequest(
                depot_id=depot_id,
                delivery_date=delivery_date,
                vehicle_capacity=payload.vehicle_capacity or 1000.0,
                algorithm=algo,
                clustering_mode=mode,
            )
            result = optimize_routes_from_db(opt_req, db)
            route_count = len(result.get("routes", []))
            total_km = result.get("total_distance", 0)
            total_min = result.get("total_duration", 0)

            return {
                "text": (
                    f"Tôi đã thực hiện tối ưu hóa thành công cho ngày {delivery_date} bằng thuật toán {algo} "
                    f"(chế độ {mode}).\n"
                    f"Kết quả: Sử dụng {route_count} phương tiện, tổng quãng đường {total_km} km, "
                    f"tổng thời gian ước tính {round(total_min)} phút.\n"
                    f"Lộ trình đã được cập nhật trực tiếp lên bản đồ cho bạn xem trước."
                ),
                "routeResult": result,
            }
        except Exception as e:
            return {
                "text": f"Không thể tự động chạy tối ưu từ cơ sở dữ liệu: {str(e)}. Bạn có thể kiểm tra lại dữ liệu đơn hàng trong ngày.",
                "routeResult": None,
            }

    # Kịch bản 2: Yêu cầu so sánh chế độ phân cụm
    if any(k in msg for k in ["so sánh", "compare", "khác biệt", "phân cụm"]):
        return {
            "text": (
                "Phân tích so sánh giữa 2 chế độ phân cụm:\n"
                "1. Chế độ Distance (Khoảng cách): Ưu tiên tối ưu hóa tổng quãng đường km ngắn nhất giữa các điểm.\n"
                "2. Chế độ Spatiotemporal (Không - Thời gian): Kết hợp cả tọa độ địa lý và khung giờ phục vụ (Time Window). "
                "Thường giúp giảm thời gian xe phải đỗ chờ (waiting time) và hạn chế nguy cơ trễ hạn.\n"
                "👉 Bạn có thể bấm nút '⚖ So sánh' trên thanh Navbar để xem biểu đồ so sánh chi tiết cho tập đơn hiện tại!"
            ),
            "routeResult": None,
        }

    # Kịch bản 3: Hỏi về xe hoặc phương tiện
    if any(k in msg for k in ["xe", "phương tiện", "vehicle"]):
        available_count = db.query(Vehicle).filter(Vehicle.status == "available").count()
        total_count = db.query(Vehicle).count()
        return {
            "text": f"Hệ thống hiện ghi nhận {total_count} phương tiện, trong đó có {available_count} xe đang ở trạng thái sẵn sàng (available) để điều phối.",
            "routeResult": None,
        }

    # Mặc định: Hướng dẫn trợ lý
    return {
        "text": (
            "Chào bạn! Tôi là AI Copilot hỗ trợ điều phối định tuyến VRPTW. Bạn có thể yêu cầu tôi:\n"
            "• 'Tối ưu đơn hàng hôm nay bằng GA'\n"
            "• 'So sánh chế độ khoảng cách và không-thời gian'\n"
            "• 'Kiểm tra tình trạng xe khả dụng'\n"
            "Hoặc bất kỳ câu hỏi nào về lộ trình!"
        ),
        "routeResult": None,
    }
