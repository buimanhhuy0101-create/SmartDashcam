from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Integer, Float, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from web_app.database.base import Base, TimestampSoftDeleteMixin

if TYPE_CHECKING:
    from web_app.models.user import User
    from web_app.models.alert_object import AlertObject


class CollisionAlert(Base, TimestampSoftDeleteMixin):
    __tablename__ = "collision_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)  # collision | traffic_sign
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)  # info | warning | danger
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    min_ttc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    snapshot_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="alerts")
    objects: Mapped[List["AlertObject"]] = relationship(
        "AlertObject", back_populates="alert", cascade="all, delete-orphan"
    )