from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from web_app.database.base import Base, TimestampSoftDeleteMixin

if TYPE_CHECKING:
    from web_app.models.user_setting import UserSetting
    from web_app.models.collision_alert import CollisionAlert


class User(Base, TimestampSoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 0: Admin, 1: Driver
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    setting: Mapped[Optional["UserSetting"]] = relationship(
        "UserSetting", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    alerts: Mapped[List["CollisionAlert"]] = relationship(
        "CollisionAlert", back_populates="user", cascade="all, delete-orphan"
    )