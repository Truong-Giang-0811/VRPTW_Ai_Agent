"""Async HTTP client để AI Agent gọi các API nghiệp vụ VRPTW.

Dùng await api_client.list_orders() hoặc asyncio.gather(...) để gọi nhiều API
độc lập song song. Đóng client bằng await api_client.aclose() khi ứng dụng dừng.
"""

from __future__ import annotations

import os
from typing import Any, Mapping
from urllib.parse import urljoin

import httpx


class APIClientError(RuntimeError):
    """Lỗi có cấu trúc khi gọi API nghiệp vụ."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        detail: Any = None,
        method: str | None = None,
        url: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail
        self.method = method
        self.url = url


class BackendAPIClient:
    """Client bất đồng bộ dựa trên httpx.AsyncClient."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        raw_url = base_url or os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000")
        self.base_url = raw_url.rstrip("/") + "/"
        self.timeout = (
            timeout
            if timeout is not None
            else float(os.getenv("BACKEND_API_TIMEOUT", "180"))
        )
        headers = {"Accept": "application/json", "User-Agent": "AI-Agent-VRPTW/1.0"}
        token = os.getenv("BACKEND_API_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(
            timeout=self.timeout, headers=headers
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | list[Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        url = urljoin(self.base_url, path.lstrip("/"))
        method = method.upper()
        req_timeout = timeout if timeout is not None else self.timeout
        try:
            response = await self.client.request(
                method, url, params=params, json=json, timeout=req_timeout
            )
        except httpx.TimeoutException as exc:
            raise APIClientError(
                f"Quá thời gian chờ phản hồi từ backend API (timeout sau {req_timeout}s).",
                method=method,
                url=url,
            ) from exc
        except httpx.ConnectError as exc:
            raise APIClientError(
                f"Không thể kết nối tới backend API tại {url}. Kiểm tra xem server đã khởi động chưa.",
                method=method,
                url=url,
            ) from exc
        except httpx.HTTPError as exc:
            msg = str(exc).strip() or type(exc).__name__
            raise APIClientError(
                f"Lỗi HTTP khi gọi backend API: {msg}", method=method, url=url
            ) from exc

        if not response.is_success:
            try:
                body = response.json()
            except ValueError:
                body = response.text
            detail = body.get("detail", body) if isinstance(body, dict) else body
            raise APIClientError(
                f"Backend trả HTTP {response.status_code}: {detail}",
                status_code=response.status_code,
                detail=detail,
                method=method,
                url=str(response.url),
            )

        if response.status_code == 204 or not response.content:
            return None

        try:
            return response.json()
        except ValueError as exc:
            raise APIClientError(
                "Backend trả phản hồi không phải JSON hợp lệ.",
                status_code=response.status_code,
                detail=response.text[:1000],
                method=method,
                url=str(response.url),
            ) from exc

    async def list_resource(
        self, resource: str, *, skip: int = 0, limit: int = 100
    ) -> Any:
        return await self.request(
            "GET", f"/api/{resource}/", params={"skip": skip, "limit": limit}
        )

    async def get_resource(self, resource: str, item_id: int) -> Any:
        return await self.request("GET", f"/api/{resource}/{item_id}")

    async def create_resource(
        self, resource: str, payload: Mapping[str, Any]
    ) -> Any:
        return await self.request("POST", f"/api/{resource}/", json=payload)

    async def update_resource(
        self, resource: str, item_id: int, payload: Mapping[str, Any]
    ) -> Any:
        return await self.request("PATCH", f"/api/{resource}/{item_id}", json=payload)

    async def delete_resource(self, resource: str, item_id: int) -> None:
        await self.request("DELETE", f"/api/{resource}/{item_id}")

    # --- Orders ---
    async def list_orders(self, *, skip: int = 0, limit: int = 100) -> Any:
        return await self.list_resource("orders", skip=skip, limit=limit)

    async def get_order(self, order_id: int) -> Any:
        return await self.get_resource("orders", order_id)

    async def create_order(self, payload: Mapping[str, Any]) -> Any:
        return await self.create_resource("orders", payload)

    async def update_order(self, order_id: int, payload: Mapping[str, Any]) -> Any:
        return await self.update_resource("orders", order_id, payload)

    async def delete_order(self, order_id: int) -> None:
        await self.delete_resource("orders", order_id)

    # --- Depots ---
    async def list_depots(self, *, skip: int = 0, limit: int = 100) -> Any:
        return await self.list_resource("depots", skip=skip, limit=limit)

    async def get_depot(self, depot_id: int) -> Any:
        return await self.get_resource("depots", depot_id)

    async def create_depot(self, payload: Mapping[str, Any]) -> Any:
        return await self.create_resource("depots", payload)

    async def update_depot(self, depot_id: int, payload: Mapping[str, Any]) -> Any:
        return await self.update_resource("depots", depot_id, payload)

    async def delete_depot(self, depot_id: int) -> None:
        await self.delete_resource("depots", depot_id)

    # --- Vehicles ---
    async def list_vehicles(self, *, skip: int = 0, limit: int = 100) -> Any:
        return await self.list_resource("vehicles", skip=skip, limit=limit)

    async def get_vehicle(self, vehicle_id: int) -> Any:
        return await self.get_resource("vehicles", vehicle_id)

    async def create_vehicle(self, payload: Mapping[str, Any]) -> Any:
        return await self.create_resource("vehicles", payload)

    async def update_vehicle(self, vehicle_id: int, payload: Mapping[str, Any]) -> Any:
        return await self.update_resource("vehicles", vehicle_id, payload)

    async def delete_vehicle(self, vehicle_id: int) -> None:
        await self.delete_resource("vehicles", vehicle_id)

    # --- Route plans ---
    async def list_route_plans(self, *, skip: int = 0, limit: int = 100) -> Any:
        return await self.list_resource("route-plans", skip=skip, limit=limit)

    async def get_route_plan(self, plan_id: int) -> Any:
        return await self.get_resource("route-plans", plan_id)

    async def create_route_plan(self, payload: Mapping[str, Any]) -> Any:
        return await self.create_resource("route-plans", payload)

    async def update_route_plan(self, plan_id: int, payload: Mapping[str, Any]) -> Any:
        return await self.update_resource("route-plans", plan_id, payload)

    async def delete_route_plan(self, plan_id: int) -> None:
        await self.delete_resource("route-plans", plan_id)

    # --- Vehicle routes ---
    async def list_vehicle_routes(self, *, skip: int = 0, limit: int = 100) -> Any:
        return await self.list_resource("vehicle-routes", skip=skip, limit=limit)

    async def get_vehicle_route(self, vehicle_route_id: int) -> Any:
        return await self.get_resource("vehicle-routes", vehicle_route_id)

    async def create_vehicle_route(self, payload: Mapping[str, Any]) -> Any:
        return await self.create_resource("vehicle-routes", payload)

    async def update_vehicle_route(
        self, vehicle_route_id: int, payload: Mapping[str, Any]
    ) -> Any:
        return await self.update_resource("vehicle-routes", vehicle_route_id, payload)

    async def delete_vehicle_route(self, vehicle_route_id: int) -> None:
        await self.delete_resource("vehicle-routes", vehicle_route_id)

    # --- Route stops ---
    async def list_route_stops(self, *, skip: int = 0, limit: int = 100) -> Any:
        return await self.list_resource("route-stops", skip=skip, limit=limit)

    async def get_route_stop(self, route_stop_id: int) -> Any:
        return await self.get_resource("route-stops", route_stop_id)

    async def create_route_stop(self, payload: Mapping[str, Any]) -> Any:
        return await self.create_resource("route-stops", payload)

    async def update_route_stop(
        self, route_stop_id: int, payload: Mapping[str, Any]
    ) -> Any:
        return await self.update_resource("route-stops", route_stop_id, payload)

    async def delete_route_stop(self, route_stop_id: int) -> None:
        await self.delete_resource("route-stops", route_stop_id)

    # --- Optimization and legacy copilot endpoints ---
    async def optimize_routes(self, payload: Mapping[str, Any]) -> Any:
        return await self.request("POST", "/api/routes/optimize", json=payload, timeout=180.0)

    async def compare_optimization(self, payload: Mapping[str, Any]) -> Any:
        return await self.request("POST", "/api/routes/optimize/compare", json=payload, timeout=180.0)

    async def optimize_from_db(self, payload: Mapping[str, Any]) -> Any:
        return await self.request("POST", "/api/routes/optimize-from-db", json=payload, timeout=180.0)

    async def save_route_plan(self, payload: Mapping[str, Any]) -> Any:
        return await self.request("POST", "/api/routes/save-plan", json=payload)

    async def list_saved_plans(self) -> Any:
        return await self.request("GET", "/api/routes/plans")

    async def get_saved_plan_details(self, plan_id: int) -> Any:
        return await self.request("GET", f"/api/routes/plans/{plan_id}")

    async def get_plan_optimization_input(self, plan_id: int) -> Any:
        return await self.request(
            "GET", f"/api/routes/plans/{plan_id}/optimization-input"
        )

    async def run_what_if(self, plan_id: int, changes: Mapping[str, Any]) -> Any:
        return await self.request(
            "POST",
            f"/api/routes/plans/{plan_id}/what-if",
            json={"changes": dict(changes)},
            timeout=180.0,
        )

    async def legacy_agent_chat(self, payload: Mapping[str, Any]) -> Any:
        return await self.request("POST", "/api/routes/chat/agent", json=payload)


api_client = BackendAPIClient()


# ==========================================
# Async wrappers cho LangChain/LangGraph tools
# ==========================================

# --- Orders ---
async def list_orders(skip: int = 0, limit: int = 100) -> Any:
    return await api_client.list_orders(skip=skip, limit=limit)


async def get_order(order_id: int) -> Any:
    return await api_client.get_order(order_id)


async def create_order(payload: Mapping[str, Any]) -> Any:
    return await api_client.create_order(payload)


async def update_order(order_id: int, payload: Mapping[str, Any]) -> Any:
    return await api_client.update_order(order_id, payload)


async def delete_order(order_id: int) -> None:
    await api_client.delete_order(order_id)


# --- Depots ---
async def list_depots(skip: int = 0, limit: int = 100) -> Any:
    return await api_client.list_depots(skip=skip, limit=limit)


async def get_depot(depot_id: int) -> Any:
    return await api_client.get_depot(depot_id)


async def create_depot(payload: Mapping[str, Any]) -> Any:
    return await api_client.create_depot(payload)


async def update_depot(depot_id: int, payload: Mapping[str, Any]) -> Any:
    return await api_client.update_depot(depot_id, payload)


async def delete_depot(depot_id: int) -> None:
    await api_client.delete_depot(depot_id)


# --- Vehicles ---
async def list_vehicles(skip: int = 0, limit: int = 100) -> Any:
    return await api_client.list_vehicles(skip=skip, limit=limit)


async def get_vehicle(vehicle_id: int) -> Any:
    return await api_client.get_vehicle(vehicle_id)


async def create_vehicle(payload: Mapping[str, Any]) -> Any:
    return await api_client.create_vehicle(payload)


async def update_vehicle(vehicle_id: int, payload: Mapping[str, Any]) -> Any:
    return await api_client.update_vehicle(vehicle_id, payload)


async def delete_vehicle(vehicle_id: int) -> None:
    await api_client.delete_vehicle(vehicle_id)