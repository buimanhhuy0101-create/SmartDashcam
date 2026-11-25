from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from web_app.database.base import Base, TimestampSoftDeleteMixin

if TYPE_CHECKING:
    from web_app.models.sign_catalog import TrafficSignCatalog


class TrafficSignCategory(Base, TimestampSoftDeleteMixin):
    __tablename__ = "traffic_sign_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    signs: Mapped[List["TrafficSignCatalog"]] = relationship(
        "TrafficSignCatalog", back_populates="category"
    )