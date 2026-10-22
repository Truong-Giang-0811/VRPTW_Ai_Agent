from datetime import time
from pydantic import Field
from app.schemas.common import ORMReadSchema


class DepotCreate(ORMReadSchema):
    name: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=255)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    open_time: time | None = None
    close_time: time | None = None


class DepotUpdate(ORMReadSchema):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    address: str | None = Field(default=None, min_length=1, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    open_time: time | None = None
    close_time: time | None = None


class DepotRead(ORMReadSchema):
    id: int
    name: str
    address: str
    latitude: float
    longitude: float
    open_time: time | None
    close_time: time | None
