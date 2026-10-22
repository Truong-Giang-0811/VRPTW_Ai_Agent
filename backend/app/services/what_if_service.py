from __future__ import annotations

from copy import deepcopy
from datetime import time
from typing import Any, Callable

from app.services.optimization_input_service import build_optimization_input

_ALLOWED_CHANGE_KEYS = {
    "vehicle_count",
    "vehicle_capacity_kg",
    "vehicle_capacity_changes",
    "add_order_ids",
    "exclude_order_ids",
    "order_overrides",
    "algorithm",
    "clustering_mode",
    "time_weight",
}
_ORDER_OVERRIDE_KEYS = {
    "order_id",
    "demand_weight_kg",
    "latitude",
    "longitude",
    "open_time",
    "close_time",
    "service_duration_min",
}


def _parse_clock(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if not isinstance(value, str):
        raise ValueError(f"{field_name} phải có định dạng HH:MM hoặc null.")
    try:
        parsed = time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} phải có định dạng HH:MM.") from exc
    return parsed.strftime("%H:%M")


def _assign_routes_to_vehicles(routes: list[dict[str, Any]], vehicles: list[dict[str, Any]]) -> list[int] | None:
    """Return a vehicle index for each route, respecting each vehicle's capacity."""
    if len(routes) > len(vehicles):
        return None
    route_order = sorted(
        range(len(routes)),
        key=lambda idx: float(routes[idx].get("load", 0.0)),
        reverse=True,
    )
    assignment = [-1] * len(routes)
    used: set[int] = set()

    def search(position: int) -> bool:
        if position >= len(route_order):
            return True
        route_idx = route_order[position]
        load = float(routes[route_idx].get("load", 0.0))
        candidates = sorted(
            (idx for idx, vehicle in enumerate(vehicles)
             if idx not in used and float(vehicle["capacity_kg"]) + 1e-9 >= load),
            key=lambda idx: float(vehicles[idx]["capacity_kg"]),
        )
        seen_capacities: set[float] = set()
        for vehicle_idx in candidates:
            capacity = float(vehicles[vehicle_idx]["capacity_kg"])
            if capacity in seen_capacities:
                continue
            seen_capacities.add(capacity)
            assignment[route_idx] = vehicle_idx
            used.add(vehicle_idx)
            if search(position + 1):
                return True
            used.remove(vehicle_idx)
            assignment[route_idx] = -1
        return False

    return assignment if search(0) else None


def _apply_order_overrides(orders: list[dict[str, Any]], overrides: Any) -> None:
    if overrides is None:
        return
    if not isinstance(overrides, list):
        raise ValueError("order_overrides phải là một danh sách.")

    by_id = {int(order["id"]): order for order in orders}
    for override in overrides:
        if not isinstance(override, dict):
            raise ValueError("Mỗi phần tử order_overrides phải là object.")
        unknown = set(override) - _ORDER_OVERRIDE_KEYS
        if unknown:
            raise ValueError(f"Trường order_overrides không hỗ trợ: {', '.join(sorted(unknown))}.")
        order_id = override.get("order_id")
        if not isinstance(order_id, int) or order_id not in by_id:
            raise ValueError(f"order_id={order_id!r} không nằm trong tập đơn của kịch bản.")
        target = by_id[order_id]
        for field in ("demand_weight_kg", "service_duration_min", "latitude", "longitude"):
            if field in override:
                value = float(override[field])
                if field in {"demand_weight_kg", "service_duration_min"} and value < 0:
                    raise ValueError(f"{field} không được âm.")
                if field == "latitude" and not -90 <= value <= 90:
                    raise ValueError("latitude phải nằm trong khoảng [-90, 90].")
                if field == "longitude" and not -180 <= value <= 180:
                    raise ValueError("longitude phải nằm trong khoảng [-180, 180].")
                target_key = {
                    "demand_weight_kg": "demand",
                    "service_duration_min": "service_time",
                    "latitude": "lat",
                    "longitude": "lng",
                }[field]
                target[target_key] = value
        for field in ("open_time", "close_time"):
            if field in override:
                target["ready_time" if field == "open_time" else "due_time"] = _parse_clock(
                    override[field], field
                )


def run_what_if(
    db,
    plan_id: int,
    changes: dict[str, Any],
    *,
    solve_payload: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Run a read-only What-if scenario against a saved plan.

    All modifications happen to a deep copy in RAM. This service never commits
    changes to MySQL. ``solve_payload`` adapts the normalized payload to the
    project's existing VRPTW solver.
    """
    if not isinstance(changes, dict):
        raise ValueError("changes phải là object JSON.")
    unknown = set(changes) - _ALLOWED_CHANGE_KEYS
    if unknown:
        raise ValueError(f"Loại thay đổi chưa hỗ trợ: {', '.join(sorted(unknown))}.")

    source = build_optimization_input(db, plan_id)
    if source is None:
        return {"status": "not_found", "plan_id": plan_id, "error": f"Không tìm thấy kế hoạch {plan_id}."}

    # Make an isolated working copy. All following mutations are RAM-only.
    scenario = deepcopy(source)
    plan = scenario["plan"]
    planned_orders = scenario["planned_orders"]
    candidate_orders = scenario["candidate_orders"]
    plan_vehicles = scenario["plan_vehicles"]
    fleet_vehicles = scenario["fleet_vehicles"]

    add_ids = changes.get("add_order_ids", []) or []
    exclude_ids = changes.get("exclude_order_ids", []) or []
    if not isinstance(add_ids, list) or not all(isinstance(item, int) for item in add_ids):
        raise ValueError("add_order_ids phải là danh sách ID số nguyên.")
    if not isinstance(exclude_ids, list) or not all(isinstance(item, int) for item in exclude_ids):
        raise ValueError("exclude_order_ids phải là danh sách ID số nguyên.")
    if len(set(add_ids)) != len(add_ids) or len(set(exclude_ids)) != len(exclude_ids):
        raise ValueError("Danh sách đơn hàng không được chứa ID trùng lặp.")

    candidate_by_id = {int(order["id"]): order for order in candidate_orders}
    planned_by_id = {int(order["id"]): order for order in planned_orders}
    unknown_adds = set(add_ids) - set(candidate_by_id)
    unknown_excludes = set(exclude_ids) - set(planned_by_id)
    if unknown_adds:
        raise ValueError(f"Các đơn thêm không phải đơn pending cùng ngày của kế hoạch: {sorted(unknown_adds)}.")
    if unknown_excludes:
        raise ValueError(f"Các đơn loại bỏ không thuộc kế hoạch gốc: {sorted(unknown_excludes)}.")

    orders_by_id = {order_id: deepcopy(order) for order_id, order in planned_by_id.items()}
    for order_id in exclude_ids:
        orders_by_id.pop(order_id, None)
    for order_id in add_ids:
        orders_by_id[order_id] = deepcopy(candidate_by_id[order_id])
    scenario_orders = list(orders_by_id.values())
    if not scenario_orders:
        raise ValueError("Kịch bản phải có ít nhất một đơn hàng để tối ưu.")

    _apply_order_overrides(scenario_orders, changes.get("order_overrides"))

    requested_vehicle_count = changes.get("vehicle_count")
    if requested_vehicle_count is None:
        requested_vehicle_count = max(1, len(plan_vehicles))
    if not isinstance(requested_vehicle_count, int) or requested_vehicle_count < 1:
        raise ValueError("vehicle_count phải là số nguyên dương.")
    if requested_vehicle_count > len(fleet_vehicles):
        raise ValueError(
            f"Yêu cầu {requested_vehicle_count} xe nhưng chỉ có {len(fleet_vehicles)} xe trong đội xe khả dụng/kế hoạch."
        )

    # Preserve the plan's vehicle order first; append additional available vehicles.
    selected_vehicles = deepcopy(fleet_vehicles[:requested_vehicle_count])
    if len(selected_vehicles) < requested_vehicle_count:
        raise ValueError("Không đủ phương tiện để tạo kịch bản.")
    for index, vehicle in enumerate(selected_vehicles, start=1):
        vehicle["scenario_vehicle_number"] = index

    global_capacity = changes.get("vehicle_capacity_kg")
    if global_capacity is not None:
        global_capacity = float(global_capacity)
        if global_capacity <= 0:
            raise ValueError("vehicle_capacity_kg phải lớn hơn 0.")
        for vehicle in selected_vehicles:
            vehicle["capacity_kg"] = global_capacity

    capacity_changes = changes.get("vehicle_capacity_changes", []) or []
    if not isinstance(capacity_changes, list):
        raise ValueError("vehicle_capacity_changes phải là một danh sách.")
    for item in capacity_changes:
        if not isinstance(item, dict):
            raise ValueError("Mỗi vehicle_capacity_changes phải là object.")
        if set(item) - {"vehicle_id", "vehicle_number", "capacity_kg"}:
            raise ValueError("vehicle_capacity_changes chỉ nhận vehicle_id, vehicle_number và capacity_kg.")
        if ("vehicle_id" in item) == ("vehicle_number" in item):
            raise ValueError("Mỗi thay đổi tải trọng phải có đúng một trong vehicle_id hoặc vehicle_number.")
        capacity = float(item.get("capacity_kg", 0))
        if capacity <= 0:
            raise ValueError("capacity_kg phải lớn hơn 0.")
        if "vehicle_id" in item:
            matches = [v for v in selected_vehicles if int(v["id"]) == int(item["vehicle_id"])]
        else:
            vehicle_number = int(item["vehicle_number"])
            matches = [v for v in selected_vehicles if v["scenario_vehicle_number"] == vehicle_number]
        if len(matches) != 1:
            raise ValueError(f"Không xác định được đúng một xe cho thay đổi tải trọng: {item}.")
        matches[0]["capacity_kg"] = capacity

    capacities = [float(vehicle["capacity_kg"]) for vehicle in selected_vehicles]
    if not capacities or min(capacities) <= 0:
        raise ValueError("Tải trọng phương tiện không hợp lệ.")

    algorithm = str(changes.get("algorithm") or scenario["optimization_config"]["algorithm"]).upper()
    if algorithm not in {"GA", "ACO", "PSO"}:
        raise ValueError("algorithm phải là GA, ACO hoặc PSO.")
    clustering_mode = str(changes.get("clustering_mode") or "distance").lower()
    if clustering_mode not in {"distance", "spatiotemporal"}:
        raise ValueError("clustering_mode phải là distance hoặc spatiotemporal.")
    time_weight = float(changes.get("time_weight", 0.35))
    if not 0 <= time_weight <= 1:
        raise ValueError("time_weight phải nằm trong khoảng [0, 1].")

    customers = []
    for order in scenario_orders:
        customers.append({
            "id": int(order["id"]),
            "code": order.get("code"),
            "name": order.get("name"),
            "lat": float(order["lat"]),
            "lng": float(order["lng"]),
            "demand": float(order["demand"]),
            "service_time": float(order.get("service_time") or 0),
            "ready_time": order.get("ready_time"),
            "due_time": order.get("due_time"),
        })

    # The existing solver accepts a single capacity. First solve using the largest
    # selected capacity, then explicitly assign each route to a real vehicle with
    # sufficient capacity. If assignment fails, retry conservatively at min capacity.
    solve_errors: list[str] = []
    assignment_failed = False
    solved: dict[str, Any] | None = None
    assigned: list[int] | None = None
    # Try each distinct capacity as the uniform solver limit. This gives the
    # post-assignment step several route partitions to test for heterogeneous fleets.
    for capacity in sorted(set(capacities), reverse=True):
        solver_payload = {
            "depot": deepcopy(scenario["depot"]),
            "customers": deepcopy(customers),
            "vehicles": [
                {"id": v["id"], "capacity": capacity, "code": v.get("code"), "name": v.get("name")}
                for v in selected_vehicles
            ],
            "vehicle_number": requested_vehicle_count,
            "vehicle_capacity": capacity,
            "algorithm": algorithm,
            "clustering_mode": clustering_mode,
            "time_weight": time_weight,
        }
        try:
            candidate_result = solve_payload(solver_payload)
            candidate_routes = candidate_result.get("routes", [])
            candidate_assignment = _assign_routes_to_vehicles(candidate_routes, selected_vehicles)
            if candidate_assignment is not None:
                solved, assigned = candidate_result, candidate_assignment
                break
            assignment_failed = True
            solve_errors.append(
                f"Không thể gán {len(candidate_routes)} tuyến vào các xe với tải trọng riêng tương ứng."
            )
        except Exception as exc:
            detail = getattr(exc, "detail", None)
            solve_errors.append(str(detail or exc))

    if solved is None or assigned is None:
        error_text = solve_errors[-1] if solve_errors else "Không tìm được phương án khả thi."
        known_infeasible_terms = ("không đủ", "không thể phục vụ", "không khả thi", "không thể gán")
        solver_reported_infeasible = any(
            any(term in message.lower() for term in known_infeasible_terms)
            for message in solve_errors
        )
        final_status = "infeasible" if assignment_failed or solver_reported_infeasible else "error"
        return {
            "status": final_status,
            "plan_id": plan_id,
            "changes": changes,
            "error": error_text,
            "diagnostics": solve_errors,
            "base_kpi": {
                "vehicles_used": len(plan_vehicles),
                "orders_served": len(planned_orders),
                "total_distance_km": float(plan["total_distance_km"]),
                "total_duration_min": float(plan["total_duration_min"]),
            },
            "scenario_kpi": None,
        }

    route_results = []
    served_ids: set[int] = set()
    for route_index, route in enumerate(solved.get("routes", [])):
        vehicle = selected_vehicles[assigned[route_index]]
        served_ids.update(int(order_id) for order_id in route.get("customer_ids", []))
        route_result = dict(route)
        route_result.update({
            "vehicle_id": int(vehicle["id"]),
            "vehicle_code": vehicle.get("code"),
            "vehicle_name": vehicle.get("name"),
            "vehicle_capacity_kg": float(vehicle["capacity_kg"]),
        })
        route_results.append(route_result)

    scenario_distance = float(solved.get("total_distance", 0))
    scenario_duration = float(solved.get("total_duration", 0))
    base_kpi = {
        "vehicles_used": len(plan_vehicles),
        "orders_served": len(planned_orders),
        "total_distance_km": float(plan["total_distance_km"]),
        "total_duration_min": float(plan["total_duration_min"]),
    }
    scenario_kpi = {
        "vehicles_used": len(route_results),
        "available_vehicles": len(selected_vehicles),
        "orders_served": len(served_ids),
        "orders_requested": len(scenario_orders),
        "unassigned_order_ids": sorted(set(orders_by_id) - served_ids),
        "total_distance_km": scenario_distance,
        "total_duration_min": scenario_duration,
        "total_waiting_time_min": float(solved.get("total_waiting_time", 0)),
        "algorithm": solved.get("algorithm", algorithm),
        "clustering_mode": solved.get("clustering_mode", clustering_mode),
        "process_time_ms": solved.get("process_time_ms"),
    }
    return {
        "status": "feasible",
        "plan_id": plan_id,
        "delivery_date": plan["delivery_date"],
        "changes": changes,
        "base_kpi": base_kpi,
        "scenario_kpi": scenario_kpi,
        "delta": {
            "vehicles_used": scenario_kpi["vehicles_used"] - base_kpi["vehicles_used"],
            "orders_served": scenario_kpi["orders_served"] - base_kpi["orders_served"],
            "total_distance_km": round(scenario_distance - base_kpi["total_distance_km"], 3),
            "total_duration_min": round(scenario_duration - base_kpi["total_duration_min"], 2),
        },
        "routes": route_results,
        "saved_to_database": False,
        "notes": [
            "Kịch bản chỉ được tính trong RAM; không thay đổi kế hoạch hoặc dữ liệu MySQL.",
            "Solver hiện tối ưu với một capacity chung mỗi lượt; kết quả tuyến được hậu kiểm và gán vào xe theo tải trọng riêng. Nếu không gán được, service thử lại với tải trọng nhỏ nhất của đội xe.",
            "So sánh KPI dùng số liệu kế hoạch đã lưu làm baseline; kết quả có thể khác do thuật toán và ma trận đường được tính lại.",
        ],
    }
