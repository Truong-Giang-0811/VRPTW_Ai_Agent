"""MCP server for AI_Agent_VRPTW; wraps the existing async BackendAPIClient."""
from __future__ import annotations

import json
from datetime import date
from typing import Any, Literal

from dotenv import load_dotenv

load_dotenv()  # Load config before api_client is instantiated.

from mcp.server.fastmcp import FastMCP
from app.agent.api_client import APIClientError, api_client
mcp = FastMCP(
    "AI-Agent-VRPTW-Tools",
    instructions=(
        "You are the MCP tool layer for a VRPTW (Vehicle Routing Problem with Time Windows) delivery dispatch system. "
        "Use these tools to read/write data through the backend API; never access the database directly. "
        "Before creating, updating, or deleting any data, make sure the user's request explicitly allows that action. "
        "To optimize from database data, both depot_id and delivery_date are required. Optimizing from the database "
        "only produces a preview result; saving the result requires a separate call to save_optimized_route_plan, "
        "and must be done only when the user asks to save it. "
        "For What-if, use run_what_if with the selected route plan ID; this tool only "
        "creates an in-memory scenario and never saves or mutates business records."
    ),
)

Resource = Literal["orders", "depots", "vehicles", "route-plans", "vehicle-routes", "route-stops"]

RESOURCE_METHODS = {
    "orders": ("list_orders", "get_order", "create_order", "update_order", "delete_order"),
    "depots": ("list_depots", "get_depot", "create_depot", "update_depot", "delete_depot"),
    "vehicles": ("list_vehicles", "get_vehicle", "create_vehicle", "update_vehicle", "delete_vehicle"),
    "route-plans": ("list_route_plans", "get_route_plan", "create_route_plan", "update_route_plan", "delete_route_plan"),
    "vehicle-routes": ("list_vehicle_routes", "get_vehicle_route", "create_vehicle_route", "update_vehicle_route", "delete_vehicle_route"),
    "route-stops": ("list_route_stops", "get_route_stop", "create_route_stop", "update_route_stop", "delete_route_stop"),
}


def _json_result(value: Any) -> str:
    return json.dumps({"ok": True, "data": value}, ensure_ascii=False, default=str)


def _error_result(exc: Exception) -> str:
    if isinstance(exc, APIClientError):
        payload = {"ok": False, "error": str(exc), "status_code": exc.status_code,
                   "detail": exc.detail, "method": exc.method, "url": exc.url}
    else:
        payload = {"ok": False, "error": str(exc), "type": type(exc).__name__}
    return json.dumps(payload, ensure_ascii=False, default=str)


async def _run_api(method_name: str, *args: Any, **kwargs: Any) -> str:
    try:
        method = getattr(api_client, method_name)
        return _json_result(await method(*args, **kwargs))
    except Exception as exc:
        return _error_result(exc)


@mcp.tool()
async def list_database_records(resource: Resource, skip: int = 0, limit: int = 100) -> str:
    """List records of a given resource type. Supports pagination.

    Args:
        resource: One of "orders", "depots", "vehicles", "route-plans", "vehicle-routes", "route-stops".
        skip: Number of records to skip (offset). Must be >= 0.
        limit: Maximum number of records to return. Must be between 1 and 500.
    """
    if skip < 0 or limit < 1 or limit > 500:
        return json.dumps({"ok": False, "error": "skip must be >= 0 and limit must be between 1 and 500."}, ensure_ascii=False)
    return await _run_api(RESOURCE_METHODS[resource][0], skip=skip, limit=limit)


@mcp.tool()
async def get_database_record(resource: Resource, item_id: int) -> str:
    """Get a single record by ID.

    Args:
        resource: One of "orders", "depots", "vehicles", "route-plans", "vehicle-routes", "route-stops".
        item_id: The record's ID. Must be greater than 0.
    """
    if item_id <= 0:
        return json.dumps({"ok": False, "error": "item_id must be greater than 0."}, ensure_ascii=False)
    return await _run_api(RESOURCE_METHODS[resource][1], item_id)


@mcp.tool()
async def create_database_record(resource: Resource, payload: dict[str, Any]) -> str:
    """Create a new record. Call this only when the user explicitly asks to create data.

    Args:
        resource: One of "orders", "depots", "vehicles", "route-plans", "vehicle-routes", "route-stops".
        payload: Record fields. Must match the backend API schema for the chosen resource. Must not be empty.
    """
    if not payload:
        return json.dumps({"ok": False, "error": "payload must not be empty."}, ensure_ascii=False)
    return await _run_api(RESOURCE_METHODS[resource][2], payload)


@mcp.tool()
async def update_database_record(resource: Resource, item_id: int, payload: dict[str, Any]) -> str:
    """Update an existing record via PATCH. Call this only when the user explicitly asks to update data.

    Args:
        resource: One of "orders", "depots", "vehicles", "route-plans", "vehicle-routes", "route-stops".
        item_id: The record's ID. Must be greater than 0.
        payload: Only the fields to change (partial update). Must not be empty.
    """
    if item_id <= 0 or not payload:
        return json.dumps({"ok": False, "error": "item_id must be > 0 and payload must not be empty."}, ensure_ascii=False)
    return await _run_api(RESOURCE_METHODS[resource][3], item_id, payload)


@mcp.tool()
async def delete_database_record(resource: Resource, item_id: int) -> str:
    """Permanently delete a record by ID. This is a destructive, irreversible operation;
    call it only when the user explicitly asks to delete.

    Args:
        resource: One of "orders", "depots", "vehicles", "route-plans", "vehicle-routes", "route-stops".
        item_id: The record's ID. Must be greater than 0.
    """
    if item_id <= 0:
        return json.dumps({"ok": False, "error": "item_id must be greater than 0."}, ensure_ascii=False)
    result = await _run_api(RESOURCE_METHODS[resource][4], item_id)
    # A successful API DELETE returns None; _run_api wraps it as data=null.
    return result


@mcp.tool()
async def optimize_routes_from_database(
    depot_id: int,
    delivery_date: str,
    algorithm: Literal["GA", "ACO", "PSO"] = "GA",
    clustering_mode: Literal["distance", "spatiotemporal"] = "distance",
    vehicle_capacity: float = 100.0,
    vehicle_number: int | None = None,
    time_weight: float = 0.35,
    order_ids: list[int] | None = None,
) -> str:
    """Run VRPTW optimization using the depot, orders, and vehicles stored in the database.
    Returns a preview result only; it does NOT save the plan (use save_optimized_route_plan for that).

    Args:
        depot_id: ID of the depot to dispatch from. Required, must be > 0.
        delivery_date: Delivery date in YYYY-MM-DD format. Required.
        algorithm: Optimization algorithm: "GA" (Genetic Algorithm), "ACO" (Ant Colony Optimization), or "PSO" (Particle Swarm Optimization).
        clustering_mode: How customers are clustered: "distance" (by distance only) or "spatiotemporal" (by location and time windows).
        vehicle_capacity: Capacity of each vehicle. Must be > 0.
        vehicle_number: Number of vehicles to use. If omitted, the backend decides. Must be > 0 if provided.
        time_weight: Weight of the time-window component in the objective/clustering (default 0.35).
        order_ids: Optional list of order IDs to restrict optimization to. If omitted, all eligible orders for the depot and date are used.
    """
    try:
        date.fromisoformat(delivery_date)
    except ValueError:
        return json.dumps({"ok": False, "error": "delivery_date must be in YYYY-MM-DD format."}, ensure_ascii=False)
    if depot_id <= 0 or vehicle_capacity <= 0 or (vehicle_number is not None and vehicle_number <= 0):
        return json.dumps({"ok": False, "error": "depot_id, vehicle_capacity, and vehicle_number must be valid positive values."}, ensure_ascii=False)
    payload: dict[str, Any] = {
        "depot_id": depot_id, "delivery_date": delivery_date,
        "algorithm": algorithm, "clustering_mode": clustering_mode,
        "vehicle_capacity": vehicle_capacity, "time_weight": time_weight,
    }
    if vehicle_number is not None:
        payload["vehicle_number"] = vehicle_number
    if order_ids:
        payload["order_ids"] = order_ids
    return await _run_api("optimize_from_db", payload)


@mcp.tool()
async def compare_route_optimization(payload: dict[str, Any]) -> str:
    """Compare optimization results between the Distance and Spatiotemporal clustering modes.

    Args:
        payload: Follows the OptimizeRequest schema. Must include "depot", "customers", and the algorithm configuration.
    """
    if not payload.get("depot") or not payload.get("customers"):
        return json.dumps({"ok": False, "error": "payload must include depot and customers."}, ensure_ascii=False)
    return await _run_api("compare_optimization", payload)


@mcp.tool()
async def optimize_routes(payload: dict[str, Any]) -> str:
    """Run VRPTW optimization on depot/customer data supplied directly in the payload.
    Does not read from or save results to the database.

    Args:
        payload: Follows the OptimizeRequest schema. Must include "depot" and "customers".
    """
    if not payload.get("depot") or not payload.get("customers"):
        return json.dumps({"ok": False, "error": "payload must include depot and customers."}, ensure_ascii=False)
    return await _run_api("optimize_routes", payload)


@mcp.tool()
async def save_optimized_route_plan(payload: dict[str, Any]) -> str:
    """Save an optimization result to the database: creates the route plan, vehicle routes, and stops,
    and may update order statuses. Call this only when the user explicitly asks to save/apply the result.

    Args:
        payload: Must include "depot_id", "delivery_date" (YYYY-MM-DD), and a non-empty "routes" list.
    """
    if not payload.get("depot_id") or not payload.get("delivery_date") or not payload.get("routes"):
        return json.dumps({"ok": False, "error": "payload must include depot_id, delivery_date, and a non-empty routes list."}, ensure_ascii=False)
    return await _run_api("save_route_plan", payload)


@mcp.tool()
async def list_saved_route_plans() -> str:
    """List all saved route plans."""
    return await _run_api("list_saved_plans")


@mcp.tool()
async def get_route_plan_optimization_input(plan_id: int) -> str:
    """Get normalized What-if input data for a saved route plan without changing it.

    Args:
        plan_id: ID of the selected saved route plan; must be greater than 0.
    """
    if plan_id <= 0:
        return json.dumps({"ok": False, "error": "plan_id must be greater than 0."}, ensure_ascii=False)
    return await _run_api("get_plan_optimization_input", plan_id)


@mcp.tool()
async def run_what_if(plan_id: int, changes: dict[str, Any]) -> str:
    """Run a read-only What-if scenario for a saved route plan. The scenario is held in RAM and never saved.

    Supported changes keys:
    - vehicle_count: number of vehicles to use in the scenario.
    - vehicle_capacity_kg: set the same capacity for every selected vehicle.
    - vehicle_capacity_changes: list of {vehicle_number, capacity_kg} or {vehicle_id, capacity_kg}.
      vehicle_number is 1-based in the selected plan's vehicle order.
    - add_order_ids: pending order IDs on the plan's delivery date to add.
    - exclude_order_ids: order IDs in the original plan to remove from this scenario.
    - order_overrides: list of {order_id, demand_weight_kg?, latitude?, longitude?, open_time?, close_time?, service_duration_min?}.
    - algorithm: GA, ACO, or PSO; clustering_mode: distance or spatiotemporal; time_weight: 0..1.

    Args:
        plan_id: The currently selected saved route plan ID.
        changes: JSON object describing only the hypothetical changes requested by the user.
    """
    if plan_id <= 0:
        return json.dumps({"ok": False, "error": "plan_id must be greater than 0."}, ensure_ascii=False)
    if not isinstance(changes, dict):
        return json.dumps({"ok": False, "error": "changes must be an object."}, ensure_ascii=False)
    return await _run_api("run_what_if", plan_id, changes)


@mcp.tool()
async def get_saved_route_plan_details(plan_id: int) -> str:
    """Get the details of a saved route plan, including its vehicle routes and stops.

    Args:
        plan_id: The route plan's ID. Must be greater than 0.
    """
    if plan_id <= 0:
        return json.dumps({"ok": False, "error": "plan_id must be greater than 0."}, ensure_ascii=False)
    return await _run_api("get_saved_plan_details", plan_id)


if __name__ == "__main__":
    # MCP stdio transport: for hosts that launch this server as a child process.
    mcp.run(transport="stdio")
