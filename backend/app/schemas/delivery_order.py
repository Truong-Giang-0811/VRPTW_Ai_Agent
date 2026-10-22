from datetime import date, datetime, time
from pydantic import Field
from app.schemas.common import ORMReadSchema


class DeliveryOrderCreate(ORMReadSchema):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=150)
    address: str = Field(min_length=1, max_length=255)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    demand_weight_kg: float = Field(ge=0)
    service_duration_min: int = Field(default=10, ge=0)
    delivery_date: date
    open_time: time | None = None
    close_time: time | None = None
    status: str = Field(default="pending", min_length=1, max_length=20)


class DeliveryOrderUpdate(ORMReadSchema):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    address: str | None = Field(default=None, min_length=1, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    demand_weight_kg: float | None = Field(default=None, ge=0)
    service_duration_min: int | None = Field(default=None, ge=0)
    delivery_date: date | None = None
    open_time: time | None = None
    close_time: time | None = None
    status: str | None = Field(default=None, min_length=1, max_length=20)


class DeliveryOrderRead(ORMReadSchema):
    id: int
    code: str
    name: str
    address: str
    latitude: float
    longitude: float
    demand_weight_kg: float
    service_duration_min: int
    delivery_date: date
    open_time: time | None
    close_time: time | None
    status: str
    created_at: datetime
