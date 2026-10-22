from datetime import date, datetime
from pydantic import Field
from app.schemas.common import ORMReadSchema


class RoutePlanCreate(ORMReadSchema):
    depot_id: int = Field(gt=0)
    delivery_date: date
    objective: str = Field(default="minimize_distance", min_length=1, max_length=50)
    algorithm: str = Field(default="OR-Tools", min_length=1, max_length=30)
    total_distance_km: float = Field(default=0, ge=0)
    total_duration_min: float = Field(default=0, ge=0)
    total_customers: int = Field(default=0, ge=0)
    status: str = Field(default="draft", min_length=1, max_length=20)


class RoutePlanUpdate(ORMReadSchema):
    depot_id: int | None = Field(default=None, gt=0)
    delivery_date: date | None = None
    objective: str | None = Field(default=None, min_length=1, max_length=50)
    algorithm: str | None = Field(default=None, min_length=1, max_length=30)
    total_distance_km: float | None = Field(default=None, ge=0)
    total_duration_min: float | None = Field(default=None, ge=0)
    total_customers: int | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, min_length=1, max_length=20)


class RoutePlanRead(ORMReadSchema):
    id: int
    depot_id: int
    delivery_date: date
    objective: str
    algorithm: str
    total_distance_km: float
    total_duration_min: float
    total_customers: int
    status: str
    created_at: datetime
