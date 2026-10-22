from fastapi import APIRouter

from app.api.vehicles_api import router as vehicles_router
from app.api.depots_api import router as depots_router
from app.api.delivery_orders_api import router as delivery_orders_router
from app.api.route_plans_api import router as route_plans_router
from app.api.vehicle_routes_api import router as vehicle_routes_router
from app.api.route_stops_api import router as route_stops_router
from app.controller.core.routes_optimize import router as routes_optimize_router
from app.api.agent_api import router as agent_router
from app.api.rag_api import router as rag_router

api_router = APIRouter()
api_router.include_router(agent_router)
api_router.include_router(rag_router)
api_router.include_router(vehicles_router)
api_router.include_router(depots_router)
api_router.include_router(delivery_orders_router)
api_router.include_router(route_plans_router)
api_router.include_router(vehicle_routes_router)
api_router.include_router(route_stops_router)
api_router.include_router(routes_optimize_router)
