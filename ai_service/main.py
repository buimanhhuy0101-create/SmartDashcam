from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_service.config import AIConfig
from ai_service.core.obstacle_tracker import ObstacleTracker
from ai_service.core.sign_detector import SignDetector
from ai_service.api.health_routes import router as health_router
from ai_service.api.ws_detect import router as ws_router
from ai_service.services.alert_reporter import AlertReporter
from ai_service.api.config_routes import router as config_router
from ai_service.core.model_manager import ModelManager
from ai_service.api.model_routes import router as model_router


app = FastAPI(
    title="SmartDashcam AI Service",
    description="API xử lý nhận diện và phân tích hình ảnh giao thông",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Nạp sẵn model lên RAM khi khởi động server
    obstacle_path = AIConfig.MODELS_DIR / AIConfig.OBSTACLE_MODEL_FILE
    app.state.obstacle_tracker = ObstacleTracker(
        model_path=obstacle_path,
        conf=AIConfig.DEFAULT_CONF,
    )
    app.state.sign_detector = SignDetector(conf=0.55, min_confirm_frames=2, cooldown_sec=6.0)
    app.state.alert_reporter = AlertReporter(cooldown_sec=5.0)
    app.state.model_manager = ModelManager(app)
    app.include_router(config_router)
    app.include_router(model_router)
    print(f"[AI Service] Ready on http://{AIConfig.AI_HOST}:{AIConfig.AI_PORT}")
    yield


app = FastAPI(title="SmartDashcam AI Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[AIConfig.WEB_APP_URL, "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(ws_router)