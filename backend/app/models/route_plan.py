
from datetime import date, datetime

from sqlalchemy import (
    ForeignKey, String, Float, Integer, Date, DateTime, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connect_db import Base



class RoutePlan(Base):
    __tablename__ = "route_plans"

    id: Mapped[int] = mapped_column(primary_key=True)

    depot_id: Mapped[int] = mapped_column(
        ForeignKey("depots.id"), nullable=False
    )
    delivery_date: Mapped[date] = mapped_column(Date, nullable=False)

    objective: Mapped[str] = mapped_column(
        String(50), default="minimize_distance", nullable=False
    )
    algorithm: Mapped[str] = mapped_column(
        String(30), default="OR-Tools", nullable=False
    )

    total_distance_km: Mapped[float] = mapped_column(
        Float, default=0, nullable=False
    )
    total_duration_min: Mapped[float] = mapped_column(
        Float, default=0, nullable=False
    )
    total_customers: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    depot: Mapped["Depot"] = relationship(back_populates="route_plans")
    vehicle_routes: Mapped[list["VehicleRoute"]] = relationship(
        back_populates="route_plan",
        cascade="all, delete-orphan"
    )
