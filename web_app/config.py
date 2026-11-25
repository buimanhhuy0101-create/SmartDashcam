import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    # ===== Web MVC =====
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'storage' / 'database' / 'smartdashcam.db').as_posix()}"
    )
    WEB_HOST: str = os.getenv("WEB_HOST", "127.0.0.1")
    WEB_PORT: int = int(os.getenv("WEB_PORT", "5000"))

    # ===== Liên kết giữa 2 dịch vụ =====
    AI_SERVICE_URL: str = os.getenv("AI_SERVICE_URL", "http://127.0.0.1:8001")
    WEB_APP_URL: str = os.getenv("WEB_APP_URL", "http://127.0.0.1:5000")

    # ===== Đường dẫn thư mục dùng chung =====
    MODELS_DIR: Path = BASE_DIR / os.getenv("MODELS_DIR", "storage/models")
    SNAPSHOTS_DIR: Path = BASE_DIR / os.getenv("SNAPSHOTS_DIR", "storage/snapshots")

    # ===== Tài khoản Admin mặc định (seed) =====
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@smartdashcam.local")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")