
from datetime import time

from sqlalchemy import String, Float, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connect_db import Base



class Depot(Base):
    __tablename__ = "depots"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    open_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    close_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    route_plans: Mapped[list["RoutePlan"]] = relationship(
        back_populates="depot"
    )
