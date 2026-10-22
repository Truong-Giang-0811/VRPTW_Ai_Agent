from pydantic import Field
from app.schemas.common import ORMReadSchema


class VehicleCreate(ORMReadSchema):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=100)
    capacity_kg: float = Field(gt=0)
    status: str = Field(default="available", min_length=1, max_length=20)


class VehicleUpdate(ORMReadSchema):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    capacity_kg: float | None = Field(default=None, gt=0)
    status: str | None = Field(default=None, min_length=1, max_length=20)


class VehicleRead(ORMReadSchema):
    id: int
    code: str
    name: str
    capacity_kg: float
    status: str
