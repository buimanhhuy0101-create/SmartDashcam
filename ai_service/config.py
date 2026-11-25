import os
from pathlib import Path
from dotenv import load_dotenv

# Trỏ về thư mục gốc SmartDashcam/ để đọc file .env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class AIConfig:
    AI_HOST: str = os.getenv("AI_HOST", "127.0.0.1")
    AI_PORT: int = int(os.getenv("AI_PORT", "8001"))
    WEB_APP_URL: str = os.getenv("WEB_APP_URL", "http://127.0.0.1:8000")

    MODELS_DIR: Path = BASE_DIR / os.getenv("MODELS_DIR", "storage/models")
    SNAPSHOTS_DIR: Path = BASE_DIR / os.getenv("SNAPSHOTS_DIR", "storage/snapshots")

    OBSTACLE_MODEL_FILE: str = os.getenv("OBSTACLE_MODEL_FILE", "yolo11n.pt")
    SIGN_MODEL_FILE: str = os.getenv("SIGN_MODEL_FILE", "traffic_sign.pt")

    # Ngưỡng mặc định dùng khi chưa đồng bộ từ user_settings
    DEFAULT_CONF: float = 0.45
    TTC_WARNING_SEC: float = 3.0
    TTC_DANGER_SEC: float = 1.5