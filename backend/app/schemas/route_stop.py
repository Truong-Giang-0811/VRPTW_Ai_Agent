from datetime import datetime
from typing import Literal
from pydantic import Field
from app.schemas.common import ORMReadSchema


class RouteStopCreate(ORMReadSchema):
    vehicle_route_id: int = Field(gt=0)
    delivery_order_id: int | None = Field(default=None, gt=0)
    sequence: int = Field(ge=0)
    stop_type: Literal["depot_start", "delivery", "depot_end"]
    arrival_time: datetime | None = None
    service_start_time: datetime | None = None
    departure_time: datetime | None = None
    distance_from_previous_km: float = Field(default=0, ge=0)


class RouteStopUpdate(ORMReadSchema):
    delivery_order_id: int | None = Field(default=None, gt=0)
    sequence: int | None = Field(default=None, ge=0)
    stop_type: Literal["depot_start", "delivery", "depot_end"] | None = None
    arrival_time: datetime | None = None
    service_start_time: datetime | None = None
    departure_time: datetime | None = None
    distance_from_previous_km: float | None = Field(default=None, ge=0)


class RouteStopRead(ORMReadSchema):
    id: int
    vehicle_route_id: int
    delivery_order_id: int | None
    sequence: int
    stop_type: str
    arrival_time: datetime | None
    service_start_time: datetime | None
    departure_time: datetime | None
    distance_from_previous_km: float
