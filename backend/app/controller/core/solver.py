"""Bộ giải VRPTW dùng cho API.

Các lớp GA/PSO/ACO cũ trong ``core/algorithm`` được viết cho bộ dữ liệu
Solomon: chúng tính khoảng cách Euclidean trực tiếp từ tọa độ. API này nhận
tọa độ thực, vì vậy mọi kiểm tra thời gian đi qua ma trận từ ``data.loader``.
"""

from __future__ import annotations

import time
from typing import Iterable

import numpy as np

from GeneticAlgorithm import GA
from kmeans import Kmeans


SUPPORTED_ALGORITHMS = {"GA", "PSO", "ACO"}
SUPPORTED_CLUSTERING_MODES = {"distance", "spatiotemporal"}
EPSILON = 1e-9


def _route_schedule(route: Iterable[int], customers: list, duration_matrix: np.ndarray):
    """Trả về (khả thi, tải, thời điểm về kho, tổng thời gian lái)."""
    depot = customers[0]
    load = 0.0
    current_time = float(depot.readyTime)
    driving_time = 0.0
    last = 0

    for customer_id in route:
        customer = customers[int(customer_id)]
        travel = float(duration_matrix[last, customer_id])
        driving_time += travel
        service_start = max(current_time + travel, float(customer.readyTime))
        if service_start > float(customer.dueTime) + EPSILON:
            return False, load, current_time, driving_time
        load += float(customer.demand)
        current_time = service_start + float(customer.serviceTime)
        last = int(customer_id)

    if route:
        return_travel = float(duration_matrix[last, 0])
        driving_time += return_travel
        current_time += return_travel

    return current_time <= float(depot.dueTime) + EPSILON, load, current_time, driving_time


def _route_timeline(route: Iterable[int], customers: list, duration_matrix: np.ndarray):
    """Lịch trình chi tiết theo từng khách trong một tuyến."""
    depot = customers[0]
    current_time = float(depot.readyTime)
    last = 0
    waiting_total = 0.0
    driving_total = 0.0
    service_total = 0.0
    stops = []

    for order, customer_id in enumerate(route, start=1):
        customer = customers[int(customer_id)]
        travel = float(duration_matrix[last, customer_id])
        arrival = current_time + travel
        waiting = max(0.0, float(customer.readyTime) - arrival)
        service_start = arrival + waiting
        departure = service_start + float(customer.serviceTime)

        waiting_total += waiting
        driving_total += travel
        service_total += float(customer.serviceTime)

        stops.append({
            "order": order,
            "customer_index": int(customer_id),
            "customer_id": int(customer.id),
            "travel_time_min": round(travel, 2),
            "arrival_min": round(arrival, 2),
            "waiting_min": round(waiting, 2),
            "service_start_min": round(service_start, 2),
            "departure_min": round(departure, 2),
            "due_min": round(float(customer.dueTime), 2),
            "ready_min": round(float(customer.readyTime), 2),
        })

        current_time = departure
        last = int(customer_id)

    if route:
        back_travel = float(duration_matrix[last, 0])
        driving_total += back_travel
        current_time += back_travel

    return stops, round(waiting_total, 2), round(driving_total, 2), round(service_total, 2), round(current_time, 2)


def _normalize_matrix(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    min_v = values.min(axis=0)
    max_v = values.max(axis=0)
    span = np.where(np.abs(max_v - min_v) < EPSILON, 1.0, max_v - min_v)
    return (values - min_v) / span


def _simple_kmeans(X: np.ndarray, k: int, seed: int = 42, max_iter: int = 100):
    """K-Means nhỏ gọn, không phụ thuộc sklearn."""
    X = np.asarray(X, dtype=float)
    if X.ndim != 2:
        raise ValueError("Dữ liệu clustering phải là ma trận 2 chiều.")
    if len(X) == 0:
        return np.array([], dtype=int), np.empty((0, X.shape[1]), dtype=float)

    k = max(1, min(int(k), len(X)))
    rng = np.random.default_rng(seed)
    if k == len(X):
        centroids = X.copy()
        labels = np.arange(len(X), dtype=int)
        return labels, centroids

    initial_indices = rng.choice(len(X), size=k, replace=False)
    centroids = X[initial_indices].copy()

    for _ in range(max_iter):
        distances = np.linalg.norm(X[:, None, :] - centroids[None, :, :], axis=2)
        labels = np.argmin(distances, axis=1)

        new_centroids = centroids.copy()
        for idx in range(k):
            mask = labels == idx
            if np.any(mask):
                new_centroids[idx] = X[mask].mean(axis=0)
            else:
                farthest = np.argmax(np.min(distances, axis=1))
                new_centroids[idx] = X[farthest]

        if np.allclose(new_centroids, centroids, atol=1e-8, rtol=0):
            centroids = new_centroids
            break
        centroids = new_centroids

    distances = np.linalg.norm(X[:, None, :] - centroids[None, :, :], axis=2)
    labels = np.argmin(distances, axis=1)
    return labels.astype(int), centroids.astype(float)


def _build_cluster_labels(customers: list, clustering_mode: str, vehicle_number: int, time_weight: float):
    """Trả về nhãn cluster cho từng customer index 1..n."""
    customer_count = max(len(customers) - 1, 0)
    if customer_count <= 0:
        return {}, [], {}

    clustering_mode = str(clustering_mode).lower()
    if clustering_mode not in SUPPORTED_CLUSTERING_MODES:
        clustering_mode = "distance"

    coords = np.array([customer.xy_coord for customer in customers[1:]], dtype=float)
    coords = _normalize_matrix(coords)

    if clustering_mode == "spatiotemporal":
        time_feature = np.array(
            [float(customer.readyTime) + float(customer.serviceTime) * 0.5 for customer in customers[1:]],
            dtype=float,
        ).reshape(-1, 1)
        time_feature = _normalize_matrix(time_feature)
        X = np.column_stack([coords, time_feature[:, 0] * float(time_weight)])
    else:
        X = coords

    n_clusters = max(1, min(int(vehicle_number), customer_count))
    labels, _ = _simple_kmeans(X, k=n_clusters, seed=42)

    depot_xy = np.array(customers[0].xy_coord, dtype=float)
    raw_cluster_centroids = []
    for label in range(n_clusters):
        member_indices = [idx for idx, member_label in enumerate(labels, start=1) if int(member_label) == int(label)]
        if member_indices:
            centroid_xy = np.mean([customers[idx].xy_coord for idx in member_indices], axis=0)
        else:
            centroid_xy = depot_xy
        raw_cluster_centroids.append(centroid_xy)

    centroid_order = sorted(
        range(n_clusters),
        key=lambda idx: float(np.linalg.norm(raw_cluster_centroids[idx] - depot_xy)),
    )
    label_to_rank = {label: rank for rank, label in enumerate(centroid_order)}

    cluster_rank_by_customer_index = {
        customer_index: int(label_to_rank[int(label)])
        for customer_index, label in enumerate(labels, start=1)
    }

    clusters_payload = []
    for rank, label in enumerate(centroid_order):
        member_indices = [idx for idx, member_label in enumerate(labels, start=1) if int(member_label) == int(label)]
        if member_indices:
            mean_xy = np.mean([customers[idx].xy_coord for idx in member_indices], axis=0)
        else:
            mean_xy = depot_xy
        clusters_payload.append({
            "cluster_id": int(rank),
            "cluster_label": int(label),
            "customer_indices": [int(i) for i in member_indices],
            "customer_ids": [int(customers[i].id) for i in member_indices],
            "centroid": [float(mean_xy[0]), float(mean_xy[1])],
        })

    customer_cluster_map = {
        int(customers[idx].id): int(cluster_rank_by_customer_index[idx])
        for idx in range(1, len(customers))
    }

    return cluster_rank_by_customer_index, clusters_payload, customer_cluster_map


def _candidate_key(
    algorithm,
    last,
    customer_id,
    current_time,
    customers,
    duration_matrix,
    distance_matrix,
    cluster_rank_by_customer_index,
    route_cluster_rank,
    clustering_mode,
    time_weight,
):
    customer = customers[customer_id]
    travel = float(duration_matrix[last, customer_id])
    waiting = max(0.0, float(customer.readyTime) - current_time - travel)
    distance = float(distance_matrix[last, customer_id])
    cluster_rank = int(cluster_rank_by_customer_index.get(customer_id, 0))

    if route_cluster_rank is None:
        cluster_priority = cluster_rank
        cluster_gap = cluster_rank
    else:
        cluster_priority = 0 if cluster_rank == route_cluster_rank else 1
        cluster_gap = abs(cluster_rank - route_cluster_rank)

    if algorithm == "PSO":
        primary = (float(customer.dueTime), travel, distance, customer_id)
    elif algorithm == "ACO":
        weight = 0.35 + float(time_weight) * 0.20 if clustering_mode == "spatiotemporal" else 0.35
        primary = (travel + waiting * weight, distance, float(customer.dueTime), customer_id)
    else:
        weight = 0.18 + float(time_weight) * 0.18 if clustering_mode == "spatiotemporal" else 0.10
        primary = (distance + waiting * weight, travel, float(customer.dueTime), customer_id)

    return (cluster_priority, cluster_gap, *primary)


def _two_opt(route, customers, duration_matrix, distance_matrix):
    """Cải thiện thứ tự trong một xe mà không làm mất tính khả thi."""
    if len(route) < 3:
        return route

    def cost(candidate):
        return sum(float(distance_matrix[a, b]) for a, b in zip([0, *candidate], [*candidate, 0]))

    best, best_cost = list(route), cost(route)
    improved = True
    while improved:
        improved = False
        for start in range(len(best) - 1):
            for end in range(start + 2, len(best) + 1):
                candidate = best[:start] + best[start:end][::-1] + best[end:]
                feasible, _, _, _ = _route_schedule(candidate, customers, duration_matrix)
                candidate_cost = cost(candidate)
                if feasible and candidate_cost < best_cost - EPSILON:
                    best, best_cost, improved = candidate, candidate_cost, True
                    break
            if improved:
                break
    return best


def _run_ga(
    customers,
    duration_matrix: np.ndarray,
    distance_matrix: np.ndarray,
    vehicle_number: int,
    vehicle_capacity: float,
    clustering_mode: str,
    time_weight: float,
):
    """Chạy GA thật (GeneticAlgorithm.py) với ma trận OSRM/Haversine."""
    customer_count = len(customers) - 1  # trừ depot

    # --- Phân cụm bằng Kmeans thật ---
    km = Kmeans(maxiter=300, n_cluster=max(1, min(vehicle_number, customer_count)))
    coords = np.array([c.xy_coord for c in customers[1:]], dtype=float)
    depot_xy = np.array(customers[0].xy_coord, dtype=float)

    if clustering_mode == "spatiotemporal":
        time_feature = np.array(
            [float(c.readyTime) + float(c.serviceTime) * 0.5 for c in customers[1:]],
            dtype=float,
        ).reshape(-1, 1)
        X = np.column_stack([coords, time_feature])
        labels, _, _ = km.k_means_spatiotemporal(X, time_weight=float(time_weight))
    else:
        labels, _, _ = km.k_means_sorted(coords, FirstPoint=depot_xy)

    # Chuyển labels → danh sách cluster (data_to_cluster đã trả về 1-based indices khớp với customers[1:])
    clusters = [c for c in km.data_to_cluster(labels) if len(c) > 0]

    # --- Chạy GA ---
    ga = GA(
        individual=50,
        generation=100,
        crossover_rate=0.8,
        mutation_rate=0.1,
        vehicle_capacity=vehicle_capacity,
        vehicle_number=vehicle_number,
        conserve_rate=0.1,
        M=0,
        customers=customers,
        duration_matrix=duration_matrix,
        distance_matrix=distance_matrix,
    )
    _, best_routes, _, _, _ = ga.fit_allClusters(clusters, use_recluster=True)
    return best_routes, ga


def solve(
    customers,
    duration_matrix,
    vehicle_number,
    vehicle_capacity,
    algorithm="GA",
    distance_matrix=None,
    clustering_mode="distance",
    time_weight: float = 0.35,
):
    """Tối ưu VRPTW bằng ma trận phút/km và trả dữ liệu tuần tự hóa JSON."""
    started_at = time.perf_counter()
    algorithm = str(algorithm).upper()
    clustering_mode = str(clustering_mode).lower()

    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError("Thuật toán phải là một trong: GA, PSO, ACO.")
    if clustering_mode not in SUPPORTED_CLUSTERING_MODES:
        raise ValueError("clustering_mode phải là 'distance' hoặc 'spatiotemporal'.")
    if not 0 <= float(time_weight) <= 1:
        raise ValueError("time_weight phải nằm trong khoảng [0, 1].")
    if len(customers) < 2:
        raise ValueError("Cần ít nhất một khách hàng để tối ưu.")
    if not isinstance(vehicle_number, (int, np.integer)) or vehicle_number < 1:
        raise ValueError("Số lượng xe phải là số nguyên dương.")
    if float(vehicle_capacity) <= 0:
        raise ValueError("Tải trọng xe phải lớn hơn 0.")

    duration_matrix = np.asarray(duration_matrix, dtype=float)
    distance_matrix = np.asarray(
        duration_matrix if distance_matrix is None else distance_matrix, dtype=float
    )
    expected_shape = (len(customers), len(customers))
    if duration_matrix.shape != expected_shape or distance_matrix.shape != expected_shape:
        raise ValueError("Ma trận thời gian/khoảng cách không khớp số điểm giao hàng.")
    if not np.isfinite(duration_matrix).all() or not np.isfinite(distance_matrix).all():
        raise ValueError("Ma trận thời gian/khoảng cách có dữ liệu không hợp lệ.")

    # ================================================================
    # Nánh GA: chạy GeneticAlgorithm.py thật + Kmeans.py thật
    # ================================================================
    if algorithm == "GA":
        try:
            routes, ga_obj = _run_ga(
                customers=customers,
                duration_matrix=duration_matrix,
                distance_matrix=distance_matrix,
                vehicle_number=vehicle_number,
                vehicle_capacity=vehicle_capacity,
                clustering_mode=clustering_mode,
                time_weight=time_weight,
            )
        except Exception as e:
            raise RuntimeError(f"GA thật gặp lỗi: {e}") from e

        # --- Xây dựng cluster info để giữ đnhạt API response ---
        cluster_rank_by_customer_index, clusters_payload, customer_cluster_map = \
            _build_cluster_labels(
                customers=customers,
                clustering_mode=clustering_mode,
                vehicle_number=vehicle_number,
                time_weight=time_weight,
            )

        result_routes, total_distance, total_duration, total_waiting_time = [], 0.0, 0.0, 0.0
        for route in routes:
            feasible, load, finish_time, _ = _route_schedule(route, customers, duration_matrix)
            if not feasible:
                raise RuntimeError("GA tạo ra một tuyến không khả thi sau khi kiểm tra lại.")

            distance = sum(float(distance_matrix[a, b]) for a, b in zip([0, *route], [*route, 0]))
            timeline, waiting_time, route_driving_time, service_time, finish_min = \
                _route_timeline(route, customers, duration_matrix)

            route_cluster_rank = None
            if route:
                cluster_candidates = [cluster_rank_by_customer_index.get(idx, 0) for idx in route]
                route_cluster_rank = int(max(set(cluster_candidates), key=cluster_candidates.count))

            total_distance += distance
            total_duration += finish_time - float(customers[0].readyTime)
            total_waiting_time += waiting_time

            result_routes.append({
                "customer_ids": [int(customers[item].id) for item in route],
                "customer_indices": [int(item) for item in route],
                "cluster_id": route_cluster_rank,
                "distance_km": round(distance, 3),
                "duration_min": round(finish_time - float(customers[0].readyTime), 2),
                "driving_duration_min": round(route_driving_time, 2),
                "waiting_time_min": round(waiting_time, 2),
                "service_time_min": round(service_time, 2),
                "load": round(load, 3),
                "timeline": timeline,
                "stop_coordinates": [[float(customers[item].xy_coord[0]), float(customers[item].xy_coord[1])] for item in route],
                "geometry": [[float(customers[item].xy_coord[0]), float(customers[item].xy_coord[1])] for item in [0, *route, 0]],
                "finish_min": round(finish_min, 2),
            })

        return {
            "algorithm": algorithm,
            "clustering_mode": clustering_mode,
            "time_weight": float(time_weight),
            "clusters": clusters_payload,
            "customer_cluster_map": customer_cluster_map,
            "routes": result_routes,
            "total_distance": round(total_distance, 3),
            "total_duration": round(total_duration, 2),
            "total_waiting_time": round(total_waiting_time, 2),
            "vehicle_count": len(routes),
            "process_time_ms": round((time.perf_counter() - started_at) * 1000, 2),
        }

    # ================================================================
    # Nánh PSO / ACO: Greedy heuristic (giữ nguyên như cũ)
    # ================================================================
    cluster_rank_by_customer_index, clusters_payload, customer_cluster_map = _build_cluster_labels(
        customers=customers,
        clustering_mode=clustering_mode,
        vehicle_number=vehicle_number,
        time_weight=time_weight,
    )

    pending, routes, depot = set(range(1, len(customers))), [], customers[0]
    while pending and len(routes) < vehicle_number:
        route, load, current_time, last = [], 0.0, float(depot.readyTime), 0
        route_cluster_rank = None

        while pending:
            feasible = []
            for customer_id in pending:
                customer = customers[customer_id]
                if load + float(customer.demand) > float(vehicle_capacity) + EPSILON:
                    continue
                travel = float(duration_matrix[last, customer_id])
                service_start = max(current_time + travel, float(customer.readyTime))
                finish = service_start + float(customer.serviceTime)
                if service_start <= float(customer.dueTime) + EPSILON and finish + float(duration_matrix[customer_id, 0]) <= float(depot.dueTime) + EPSILON:
                    feasible.append(customer_id)

            if not feasible:
                break

            customer_id = min(
                feasible,
                key=lambda item: _candidate_key(
                    algorithm,
                    last,
                    item,
                    current_time,
                    customers,
                    duration_matrix,
                    distance_matrix,
                    cluster_rank_by_customer_index,
                    route_cluster_rank,
                    clustering_mode,
                    time_weight,
                ),
            )
            customer = customers[customer_id]
            if route_cluster_rank is None:
                route_cluster_rank = int(cluster_rank_by_customer_index.get(customer_id, 0))

            current_time = max(current_time + float(duration_matrix[last, customer_id]), float(customer.readyTime)) + float(customer.serviceTime)
            load += float(customer.demand)
            route.append(customer_id)
            pending.remove(customer_id)
            last = customer_id

        if not route:
            customer = customers[min(pending)]
            raise ValueError(f"Khách hàng {customer.id} không thể phục vụ với tải trọng, khung giờ hoặc thời gian quay về kho hiện tại.")

        routes.append(_two_opt(route, customers, duration_matrix, distance_matrix))

    if pending:
        raise ValueError(f"Không đủ {vehicle_number} xe để phục vụ toàn bộ khách hàng theo các ràng buộc hiện tại.")

    result_routes, total_distance, total_duration, total_waiting_time = [], 0.0, 0.0, 0.0
    for route in routes:
        feasible, load, finish_time, _ = _route_schedule(route, customers, duration_matrix)
        if not feasible:
            raise RuntimeError("Bộ giải tạo ra một tuyến không khả thi.")

        distance = sum(float(distance_matrix[a, b]) for a, b in zip([0, *route], [*route, 0]))
        timeline, waiting_time, route_driving_time, service_time, finish_min = _route_timeline(route, customers, duration_matrix)
        route_cluster_rank = None
        if route:
            cluster_candidates = [cluster_rank_by_customer_index.get(idx, 0) for idx in route]
            route_cluster_rank = int(max(set(cluster_candidates), key=cluster_candidates.count))

        total_distance += distance
        total_duration += finish_time - float(depot.readyTime)
        total_waiting_time += waiting_time

        result_routes.append({
            "customer_ids": [int(customers[item].id) for item in route],
            "customer_indices": [int(item) for item in route],
            "cluster_id": route_cluster_rank,
            "distance_km": round(distance, 3),
            "duration_min": round(finish_time - float(depot.readyTime), 2),
            "driving_duration_min": round(route_driving_time, 2),
            "waiting_time_min": round(waiting_time, 2),
            "service_time_min": round(service_time, 2),
            "load": round(load, 3),
            "timeline": timeline,
            "stop_coordinates": [[float(customers[item].xy_coord[0]), float(customers[item].xy_coord[1])] for item in route],
            "geometry": [[float(customers[item].xy_coord[0]), float(customers[item].xy_coord[1])] for item in [0, *route, 0]],
            "finish_min": round(finish_min, 2),
        })

    return {
        "algorithm": algorithm,
        "clustering_mode": clustering_mode,
        "time_weight": float(time_weight),
        "clusters": clusters_payload,
        "customer_cluster_map": customer_cluster_map,
        "routes": result_routes,
        "total_distance": round(total_distance, 3),
        "total_duration": round(total_duration, 2),
        "total_waiting_time": round(total_waiting_time, 2),
        "vehicle_count": len(routes),
        "process_time_ms": round((time.perf_counter() - started_at) * 1000, 2),
    }
