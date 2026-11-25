from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "SmartDashcam FastAPI AI Service",
        "obstacle_model": "yolo11n.pt (ByteTrack)",
        "sign_model": "stub_mode",
    }