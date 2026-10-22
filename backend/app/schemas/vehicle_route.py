from pydantic import Field
from app.schemas.common import ORMReadSchema


class VehicleRouteCreate(ORMReadSchema):
    route_plan_id: int = Field(gt=0)
    vehicle_id: int = Field(gt=0)
    total_load_kg: float = Field(default=0, ge=0)
    total_distance_km: float = Field(default=0, ge=0)
    total_duration_min: float = Field(default=0, ge=0)


class VehicleRouteUpdate(ORMReadSchema):
    total_load_kg: float | None = Field(default=None, ge=0)
    total_distance_km: float | None = Field(default=None, ge=0)
    total_duration_min: float | None = Field(default=None, ge=0)


class VehicleRouteRead(ORMReadSchema):
    id: int
    route_plan_id: int
    vehicle_id: int
    total_load_kg: float
    total_distance_km: float
    total_duration_min: float
