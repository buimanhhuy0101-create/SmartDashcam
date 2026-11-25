from typing import TYPE_CHECKING
from sqlalchemy import Integer, Float, Boolean, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from web_app.database.base import Base, TimestampSoftDeleteMixin

if TYPE_CHECKING:
    from web_app.models.user import User


class UserSetting(Base, TimestampSoftDeleteMixin):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    vehicle_type: Mapped[str] = mapped_column(String(50), default="car", nullable=False)
    tts_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    alert_sound_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    conf_threshold: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    ttc_warning_sec: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    ttc_danger_sec: Mapped[float] = mapped_column(Float, default=1.2, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="setting")