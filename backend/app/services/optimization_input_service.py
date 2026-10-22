from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from sqlalchemy.orm import Session, selectinload

from app.models import DeliveryOrder, Depot, RoutePlan, RouteStop, Vehicle, VehicleRoute


def _time_text(value: time | None, default: str | None = None) -> str | None:
    return value.strftime("%H:%M") if value else default


def _order_payload(order: DeliveryOrder) -> dict[str, Any]:
    return {
        "id": order.id,
        "code": order.code,
        "name": order.name,
        "address": order.address,
        "lat": float(order.latitude),
        "lng": float(order.longitude),
        "demand": float(order.demand_weight_kg),
        "service_time": float(order.service_duration_min or 0),
        "ready_time": _time_text(order.open_time),
        "due_time": _time_text(order.close_time),
        "delivery_date": order.delivery_date.isoformat(),
        "status": order.status,
    }


def _vehicle_payload(vehicle: Vehicle, *, route_number: int | None = None) -> dict[str, Any]:
    result = {
        "id": vehicle.id,
        "code": vehicle.code,
        "name": vehicle.name,
        "capacity_kg": float(vehicle.capacity_kg),
        "status": vehicle.status,
    }
    if route_number is not None:
        result["route_number"] = route_number
    return result


def build_optimization_input(db: Session, plan_id: int) -> dict[str, Any] | None:
    """Read and normalize all data needed to create a What-if from a saved plan.

    This function is read-only. It never changes route plans, orders, or vehicles.
    """
    plan = (
        db.query(RoutePlan)
        .options(
            selectinload(RoutePlan.depot),
            selectinload(RoutePlan.vehicle_routes)
            .selectinload(VehicleRoute.vehicle),
            selectinload(RoutePlan.vehicle_routes)
            .selectinload(VehicleRoute.stops)
            .selectinload(RouteStop.delivery_order),
        )
        .filter(RoutePlan.id == plan_id)
        .first()
    )
    if plan is None:
        return None

    depot = plan.depot
    if depot is None:
        raise ValueError(f"Kế hoạch {plan_id} không có depot hợp lệ.")

    plan_routes = sorted(plan.vehicle_routes, key=lambda item: item.id)
    planned_order_ids: list[int] = []
    route_payloads: list[dict[str, Any]] = []
    plan_vehicles: list[dict[str, Any]] = []
    seen_vehicle_ids: set[int] = set()

    for route_number, vehicle_route in enumerate(plan_routes, start=1):
        vehicle = vehicle_route.vehicle
        if vehicle is not None and vehicle.id not in seen_vehicle_ids:
            plan_vehicles.append(_vehicle_payload(vehicle, route_number=route_number))
            seen_vehicle_ids.add(vehicle.id)

        stops = sorted(vehicle_route.stops, key=lambda item: item.sequence)
        stop_payloads = []
        for stop in stops:
            order = stop.delivery_order
            if stop.stop_type.lower() == "delivery" and order is not None:
                if order.id not in planned_order_ids:
                    planned_order_ids.append(order.id)
                stop_payloads.append({
                    "sequence": stop.sequence,
                    "stop_type": stop.stop_type,
                    "order_id": order.id,
                    "arrival_time": stop.arrival_time.isoformat() if stop.arrival_time else None,
                    "service_start_time": stop.service_start_time.isoformat() if stop.service_start_time else None,
                    "departure_time": stop.departure_time.isoformat() if stop.departure_time else None,
                })
            else:
                stop_payloads.append({
                    "sequence": stop.sequence,
                    "stop_type": stop.stop_type,
                    "order_id": None,
                    "arrival_time": stop.arrival_time.isoformat() if stop.arrival_time else None,
                    "service_start_time": stop.service_start_time.isoformat() if stop.service_start_time else None,
                    "departure_time": stop.departure_time.isoformat() if stop.departure_time else None,
                })

        route_payloads.append({
            "vehicle_route_id": vehicle_route.id,
            "vehicle_id": vehicle_route.vehicle_id,
            "vehicle_number": route_number,
            "total_load_kg": float(vehicle_route.total_load_kg or 0),
            "total_distance_km": float(vehicle_route.total_distance_km or 0),
            "total_duration_min": float(vehicle_route.total_duration_min or 0),
            "stops": stop_payloads,
        })

    planned_orders = []
    if planned_order_ids:
        order_rows = (
            db.query(DeliveryOrder)
            .filter(DeliveryOrder.id.in_(planned_order_ids))
            .all()
        )
        order_by_id = {order.id: order for order in order_rows}
        planned_orders = [
            _order_payload(order_by_id[order_id])
            for order_id in planned_order_ids
            if order_id in order_by_id
        ]

    candidate_query = db.query(DeliveryOrder).filter(
        DeliveryOrder.delivery_date == plan.delivery_date,
        DeliveryOrder.status == "pending",
    )
    if planned_order_ids:
        candidate_query = candidate_query.filter(~DeliveryOrder.id.in_(planned_order_ids))
    candidate_orders = [
        _order_payload(order)
        for order in candidate_query.order_by(DeliveryOrder.id.asc()).all()
    ]

    # The plan's current vehicles are included even if their current status is not
    # "available". Other vehicles can be considered as additional scenario vehicles
    # only when their status is "available".
    fleet = list(plan_vehicles)
    fleet_ids = {vehicle["id"] for vehicle in fleet}
    extra_vehicles = (
        db.query(Vehicle)
        .filter(Vehicle.status == "available")
        .order_by(Vehicle.id.asc())
        .all()
    )
    for vehicle in extra_vehicles:
        if vehicle.id not in fleet_ids:
            fleet.append(_vehicle_payload(vehicle))
            fleet_ids.add(vehicle.id)

    return {
        "plan": {
            "id": plan.id,
            "delivery_date": plan.delivery_date.isoformat(),
            "depot_id": plan.depot_id,
            "objective": plan.objective,
            "algorithm": plan.algorithm,
            "status": plan.status,
            "total_distance_km": float(plan.total_distance_km or 0),
            "total_duration_min": float(plan.total_duration_min or 0),
            "total_customers": int(plan.total_customers or 0),
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
        },
        "depot": {
            "id": depot.id,
            "name": depot.name,
            "address": depot.address,
            "lat": float(depot.latitude),
            "lng": float(depot.longitude),
            "ready_time": _time_text(depot.open_time, "07:00"),
            "due_time": _time_text(depot.close_time, "18:00"),
        },
        "plan_vehicles": plan_vehicles,
        "fleet_vehicles": fleet,
        "planned_orders": planned_orders,
        "candidate_orders": candidate_orders,
        "routes": route_payloads,
        "optimization_config": {
            "algorithm": plan.algorithm if plan.algorithm in {"GA", "ACO", "PSO"} else "GA",
            "clustering_mode": "distance",
            "time_weight": 0.35,
        },
        "travel_matrix": None,
    }
