from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from web_app.database.base import Base, TimestampSoftDeleteMixin

if TYPE_CHECKING:
    from web_app.models.sign_category import TrafficSignCategory
    from web_app.models.sign_vehicle import TrafficSignVehicle


class TrafficSignCatalog(Base, TimestampSoftDeleteMixin):
    __tablename__ = "traffic_sign_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("traffic_sign_categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sign_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tts_script: Mapped[str] = mapped_column(String(255), nullable=False)
    icon_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1: Thấp, 2: Trung bình, 3: Cao

    # Relationships
    category: Mapped["TrafficSignCategory"] = relationship("TrafficSignCategory", back_populates="signs")
    vehicles: Mapped[List["TrafficSignVehicle"]] = relationship(
        "TrafficSignVehicle", back_populates="sign", cascade="all, delete-orphan"
    )