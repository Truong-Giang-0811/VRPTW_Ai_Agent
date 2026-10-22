"""Distance providers: sync adapter cho solver legacy e async OSRM cho luồng mới."""
from __future__ import annotations

import os
from math import radians, sin, cos, asin, sqrt
from typing import Any

import httpx
import numpy as np
import requests

OSRM_URL = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org").rstrip("/")
DISTANCE_PROVIDER = os.getenv("DISTANCE_PROVIDER", "osrm").lower()
DEFAULT_SPEED_KMH = 30.0
OSRM_TIMEOUT = float(os.getenv("OSRM_TIMEOUT", "30"))


def _coordinates(points: list[dict[str, Any]]) -> str:
    if not points:
        raise ValueError("Danh sách điểm không được rỗng.")
    try:
        return ";".join(f"{float(p['lng'])},{float(p['lat'])}" for p in points)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Mỗi điểm phải có tọa độ số 'lat' và 'lng'.") from exc


def get_osrm_table(points):
    """Hàm đồng bộ tương thích với routes_optimize.py hiện tại."""
    coords = _coordinates(points)
    url = f"{OSRM_URL}/table/v1/driving/{coords}"
    response = requests.get(url, params={"annotations": "distance,duration"}, timeout=OSRM_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if data.get("code") != "Ok" or data.get("distances") is None or data.get("durations") is None:
        raise RuntimeError(f"OSRM Table API không trả dữ liệu hợp lệ: {data.get('message', data.get('code'))}")
    return np.asarray(data["distances"], dtype=float), np.asarray(data["durations"], dtype=float)


def get_osrm_route(points):
    """Hàm đồng bộ giữ tương thích với các endpoint tối ưu legacy."""
    coords = _coordinates(points)
    url = f"{OSRM_URL}/route/v1/driving/{coords}"
    response = requests.get(url, params={"overview": "full", "geometries": "geojson"}, timeout=OSRM_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise RuntimeError(f"OSRM Route API không trả tuyến hợp lệ: {data.get('message', data.get('code'))}")
    return data["routes"][0]["geometry"]["coordinates"]


async def get_osrm_table_async(points, *, client: httpx.AsyncClient | None = None):
    """Lấy distance/duration matrix mà không block event loop."""
    coords = _coordinates(points)
    url = f"{OSRM_URL}/table/v1/driving/{coords}"
    if client is not None:
        response = await client.get(url, params={"annotations": "distance,duration"}, timeout=OSRM_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    else:
        async with httpx.AsyncClient(timeout=OSRM_TIMEOUT) as async_client:
            response = await async_client.get(url, params={"annotations": "distance,duration"})
            response.raise_for_status()
            data = response.json()
    if data.get("code") != "Ok" or data.get("distances") is None or data.get("durations") is None:
        raise RuntimeError(f"OSRM Table API không trả dữ liệu hợp lệ: {data.get('message', data.get('code'))}")
    return np.asarray(data["distances"], dtype=float), np.asarray(data["durations"], dtype=float)


async def get_osrm_route_async(points, *, client: httpx.AsyncClient | None = None):
    """Lấy geometry GeoJSON qua HTTP bất đồng bộ."""
    coords = _coordinates(points)
    url = f"{OSRM_URL}/route/v1/driving/{coords}"
    params = {"overview": "full", "geometries": "geojson"}
    if client is not None:
        response = await client.get(url, params=params, timeout=OSRM_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    else:
        async with httpx.AsyncClient(timeout=OSRM_TIMEOUT) as async_client:
            response = await async_client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise RuntimeError(f"OSRM Route API không trả tuyến hợp lệ: {data.get('message', data.get('code'))}")
    return data["routes"][0]["geometry"]["coordinates"]


def _haversine_km(p1, p2):
    radius_km = 6371.0
    lat1, lng1, lat2, lng2 = map(radians, [p1["lat"], p1["lng"], p2["lat"], p2["lng"]])
    dlat, dlng = lat2 - lat1, lng2 - lng1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    return 2 * radius_km * asin(sqrt(a))


class EuclideanProvider:
    """Haversine approximation; local computation, so sync is appropriate."""
    def build_matrix(self, points):
        n = len(points)
        distance_matrix = np.zeros((n, n), dtype=float)
        for i in range(n):
            for j in range(n):
                if i != j:
                    distance_matrix[i, j] = _haversine_km(points[i], points[j])
        duration_matrix = distance_matrix / DEFAULT_SPEED_KMH * 60.0  # minutes
        return distance_matrix, duration_matrix


class OSRMProvider:
    """Synchronous adapter retained for the existing VRPTW solver."""
    def build_matrix(self, points):
        distance_m, duration_sec = get_osrm_table(points)
        return distance_m / 1000.0, duration_sec / 60.0


class AsyncOSRMProvider:
    """Async provider for new async services and Agent tools."""
    async def build_matrix(self, points, *, client: httpx.AsyncClient | None = None):
        distance_m, duration_sec = await get_osrm_table_async(points, client=client)
        return distance_m / 1000.0, duration_sec / 60.0


class AsyncEuclideanProvider:
    """Async-compatible interface for the local provider (no blocking I/O)."""
    async def build_matrix(self, points, *, client=None):
        return EuclideanProvider().build_matrix(points)


def get_distance_provider():
    """Factory đồng bộ hiện có; giữ tương thích với routes_optimize.py."""
    return OSRMProvider() if DISTANCE_PROVIDER == "osrm" else EuclideanProvider()


def get_async_distance_provider():
    """Factory cho code async mới."""
    return AsyncOSRMProvider() if DISTANCE_PROVIDER == "osrm" else AsyncEuclideanProvider()
