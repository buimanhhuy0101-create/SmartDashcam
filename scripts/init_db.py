import sys
from pathlib import Path

# Thêm thư mục gốc dự án vào sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from web_app.database.base import Base
from web_app.database.connection import engine, get_db
from web_app.database.seed import seed_all
import web_app.models  # noqa: F401 - Đăng ký toàn bộ 8 bảng vào Base.metadata


def init_database() -> None:
    print("[1/2] Đang tạo các bảng trong CSDL...")
    Base.metadata.create_all(bind=engine)

    print("[2/2] Đang nạp dữ liệu mặc định (Admin + Biển báo)...")
    with get_db() as db:
        seed_all(db)

    print("Hoàn tất khởi tạo CSDL!")


if __name__ == "__main__":
    init_database()