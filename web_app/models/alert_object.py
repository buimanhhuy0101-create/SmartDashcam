from typing import Optional, TYPE_CHECKING
from sqlalchemy import Integer, Float, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from web_app.database.base import Base, TimestampSoftDeleteMixin

if TYPE_CHECKING:
    from web_app.models.collision_alert import CollisionAlert


class AlertObject(Base, TimestampSoftDeleteMixin):
    __tablename__ = "alert_objects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("collision_alerts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    track_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    object_label: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_x1: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y1: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_x2: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y2: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_ttc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    alert: Mapped["CollisionAlert"] = relationship("CollisionAlert", back_populates="objects")