from typing import TYPE_CHECKING
from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from web_app.database.base import Base, TimestampSoftDeleteMixin

if TYPE_CHECKING:
    from web_app.models.sign_catalog import TrafficSignCatalog


class TrafficSignVehicle(Base, TimestampSoftDeleteMixin):
    __tablename__ = "traffic_sign_vehicles"
    __table_args__ = (
        UniqueConstraint("sign_id", "vehicle_type", name="uq_sign_vehicle_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("traffic_sign_catalog.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vehicle_type: Mapped[str] = mapped_column(String(50), nullable=False)  # car | motorbike | truck | bus | all

    # Relationships
    sign: Mapped["TrafficSignCatalog"] = relationship("TrafficSignCatalog", back_populates="vehicles")