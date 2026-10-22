
from datetime import datetime

from sqlalchemy import (
    ForeignKey, Integer, String, Float, DateTime,
    UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connect_db import Base


class RouteStop(Base):
    __tablename__ = "route_stops"

    __table_args__ = (
        UniqueConstraint(
            "vehicle_route_id",
            "sequence",
            name="uq_route_sequence"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    vehicle_route_id: Mapped[int] = mapped_column(
        ForeignKey("vehicle_routes.id"), nullable=False
    )
    delivery_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("delivery_orders.id"), nullable=True
    )

    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    stop_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )

    arrival_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    service_start_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    departure_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    distance_from_previous_km: Mapped[float] = mapped_column(
        Float, default=0, nullable=False
    )

    vehicle_route: Mapped["VehicleRoute"] = relationship(
        back_populates="stops"
    )
    delivery_order: Mapped["DeliveryOrder | None"] = relationship(
        back_populates="route_stops"
    )
