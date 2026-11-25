from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ai_service.core.model_manager import ModelReloadError

router = APIRouter(prefix="/api/v1/models", tags=["models"])


class ModelReloadPayload(BaseModel):
    model_id: Optional[int] = None
    name: str = ""
    model_type: str
    version: str = ""
    file_path: str
    checksum_sha256: Optional[str] = None
    imgsz: int = 640


@router.post("/reload")
def reload_model(payload: ModelReloadPayload, request: Request):
    manager = getattr(request.app.state, "model_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="ModelManager chưa sẵn sàng.")

    try:
        info = manager.reload_model(
            model_type=payload.model_type,
            file_path=payload.file_path,
            checksum_sha256=payload.checksum_sha256,
            imgsz=payload.imgsz,
            version=payload.version,
            name=payload.name,
        )
        return {
            "status": "ok",
            "message": "Nạp nóng mô hình thành công.",
            "active_model": info,
        }
    except ModelReloadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc