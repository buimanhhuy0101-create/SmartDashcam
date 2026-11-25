from contextlib import contextmanager
from typing import Generator, Type, TypeVar
from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from web_app.config import Config
from web_app.database.base import Base

T = TypeVar("T", bound=Base)

# Đảm bảo thư mục chứa file SQLite tồn tại nếu dùng đường dẫn tương đối
if Config.DATABASE_URL.startswith("sqlite:///"):
    db_path = Config.DATABASE_URL.replace("sqlite:///", "", 1)
    from pathlib import Path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    Config.DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False} if Config.DATABASE_URL.startswith("sqlite") else {},
)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    """Bật khóa ngoại và chế độ WAL mỗi khi mở kết nối SQLite."""
    if Config.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Context manager quản lý vòng đời session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def active_select(model: Type[T]):
    """Tạo câu lệnh SELECT mặc định lọc bỏ các bản ghi đã xóa mềm."""
    return select(model).where(model.deleted_at.is_(None))