
from datetime import date, datetime, time

from sqlalchemy import (
    String, Float, Integer, Date, DateTime, Time, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connect_db import Base


class DeliveryOrder(Base):
    __tablename__ = "delivery_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    demand_weight_kg: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    service_duration_min: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False
    )

    delivery_date: Mapped[date] = mapped_column(Date, nullable=False)
    open_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    close_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    route_stops: Mapped[list["RouteStop"]] = relationship(
        back_populates="delivery_order"
    )
