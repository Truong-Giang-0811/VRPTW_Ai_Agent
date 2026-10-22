
from sqlalchemy import ForeignKey, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connect_db import Base



class VehicleRoute(Base):
    __tablename__ = "vehicle_routes"

    __table_args__ = (
        UniqueConstraint(
            "route_plan_id",
            "vehicle_id",
            name="uq_plan_vehicle"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    route_plan_id: Mapped[int] = mapped_column(
        ForeignKey("route_plans.id"), nullable=False
    )
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id"), nullable=False
    )

    total_load_kg: Mapped[float] = mapped_column(
        Float, default=0, nullable=False
    )
    total_distance_km: Mapped[float] = mapped_column(
        Float, default=0, nullable=False
    )
    total_duration_min: Mapped[float] = mapped_column(
        Float, default=0, nullable=False
    )

    route_plan: Mapped["RoutePlan"] = relationship(
        back_populates="vehicle_routes"
    )
    vehicle: Mapped["Vehicle"] = relationship(
        back_populates="vehicle_routes"
    )
    stops: Mapped[list["RouteStop"]] = relationship(
        back_populates="vehicle_route",
        cascade="all, delete-orphan",
        order_by="RouteStop.sequence"
    )
