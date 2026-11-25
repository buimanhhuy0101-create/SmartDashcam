from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1", tags=["Config"])


class AIConfigUpdate(BaseModel):
    conf_threshold: float = Field(..., ge=0.1, le=0.95)
    ttc_warning_sec: float = Field(..., gt=0.2, le=10.0)
    ttc_danger_sec: float = Field(..., gt=0.1, le=10.0)


@router.post("/config")
def update_ai_config(payload: AIConfigUpdate, request: Request):
    tracker = request.app.state.obstacle_tracker
    tracker.conf_threshold = payload.conf_threshold
    tracker.ttc_warning_sec = payload.ttc_warning_sec
    tracker.ttc_danger_sec = payload.ttc_danger_sec

    sign_detector = getattr(request.app.state, "sign_detector", None)
    if sign_detector is not None:
        sign_detector.conf = payload.conf_threshold
        if hasattr(sign_detector, "clear_user_cache"):
            sign_detector.clear_user_cache()

    return {
        "status": "updated",
        "conf_threshold": tracker.conf_threshold,
        "ttc_warning_sec": tracker.ttc_warning_sec,
        "ttc_danger_sec": tracker.ttc_danger_sec,
    }


@router.post("/signs/reload-cache")
def reload_sign_catalog_cache(request: Request):
    sign_detector = getattr(request.app.state, "sign_detector", None)
    if sign_detector is None or not hasattr(sign_detector, "reload_catalog_cache"):
        return {"status": "skipped", "total_signs": 0}

    total = sign_detector.reload_catalog_cache()
    return {"status": "reloaded", "total_signs": total}