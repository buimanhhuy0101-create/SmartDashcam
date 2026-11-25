import threading
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI
from ultralytics import YOLO

from ai_service.config import BASE_DIR, AIConfig
from ai_service.core.obstacle_tracker import ObstacleTracker
from ai_service.utils.checksum import verify_sha256


class ModelReloadError(Exception):
    """Lỗi xảy ra trong quá trình kiểm tra hoặc nạp nóng mô hình."""


class ModelManager:
    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self._lock = threading.Lock()
        self.active_info: dict[str, dict[str, Any]] = {
            "obstacle": {"file_path": str(AIConfig.MODELS_DIR / AIConfig.OBSTACLE_MODEL_FILE)},
            "sign": {"file_path": None},
        }

    def _resolve_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if not path.is_absolute():
            path = (BASE_DIR / path).resolve()
        return path

    def _run_dummy_inference(self, model: YOLO, imgsz: int) -> None:
        """Chạy thử (Dummy Inference) trên ảnh giả lập để đảm bảo file .pt hoạt động tốt."""
        dummy_frame = np.zeros((imgsz, imgsz, 3), dtype=np.uint8)
        model.predict(source=dummy_frame, imgsz=imgsz, verbose=False)

    def reload_model(
        self,
        model_type: str,
        file_path: str,
        checksum_sha256: str | None = None,
        imgsz: int = 640,
        version: str = "",
        name: str = "",
    ) -> dict[str, Any]:
        m_type = (model_type or "").strip().lower()
        if m_type not in ("sign", "obstacle"):
            raise ModelReloadError(f"Loại mô hình không hợp lệ: {model_type}")

        full_path = self._resolve_path(file_path)
        if not full_path.exists() or not full_path.is_file():
            raise ModelReloadError(f"Không tìm thấy tệp mô hình tại: {file_path}")

        if full_path.suffix.lower() != ".pt":
            raise ModelReloadError("Chỉ hỗ trợ nạp tệp trọng số định dạng .pt.")

        # Bước 1: Kiểm tra tính toàn vẹn SHA-256
        if not verify_sha256(full_path, checksum_sha256):
            raise ModelReloadError("Mã kiểm tra toàn vẹn SHA-256 không khớp. Đã hủy nạp nóng.")

        # Bước 2: Nạp thử vào biến tạm và chạy Dummy Inference (chưa chạm vào model đang chạy)
        try:
            if m_type == "obstacle":
                old_tracker = getattr(self.app.state, "obstacle_tracker", None)
                conf = getattr(old_tracker, "conf_threshold", AIConfig.DEFAULT_CONF)
                candidate_tracker = ObstacleTracker(model_path=full_path, conf=conf)
                # Giữ lại ngưỡng TTC hiện tại trên RAM nếu có
                if old_tracker is not None:
                    if hasattr(old_tracker, "ttc_warning_sec"):
                        candidate_tracker.ttc_warning_sec = old_tracker.ttc_warning_sec
                    if hasattr(old_tracker, "ttc_danger_sec"):
                        candidate_tracker.ttc_danger_sec = old_tracker.ttc_danger_sec
                self._run_dummy_inference(candidate_tracker.model, imgsz)
                candidate_obj: Any = candidate_tracker
                num_classes = len(getattr(candidate_tracker.model, "names", {}) or {})
            else:
                candidate_yolo = YOLO(str(full_path))
                self._run_dummy_inference(candidate_yolo, imgsz)
                candidate_obj = candidate_yolo
                num_classes = len(getattr(candidate_yolo, "names", {}) or {})
        except Exception as exc:
            # Rollback: không thay đổi app.state, giữ nguyên bản cũ ổn định trên RAM
            raise ModelReloadError(f"Chạy thử (Dummy Inference) thất bại: {exc}") from exc

        # Bước 3: Nạp nóng an toàn đa luồng (atomic swap trên RAM)
        with self._lock:
            if m_type == "obstacle":
                self.app.state.obstacle_tracker = candidate_obj
            else:
                # Lưu sẵn model biển báo đã kiểm duyệt trên RAM (chưa bật ws_detect cho đến Giai đoạn 5)
                self.app.state.sign_model = candidate_obj
                self.app.state.sign_model_imgsz = imgsz
                sign_detector = getattr(self.app.state, "sign_detector", None)
                if sign_detector is not None and hasattr(sign_detector, "update_model"):
                    sign_detector.update_model(candidate_obj, imgsz)

            self.active_info[m_type] = {
                "name": name,
                "version": version,
                "file_path": file_path,
                "imgsz": imgsz,
                "num_classes": num_classes,
            }

        print(
            f"[ModelManager] Hot-reload thành công ({m_type}): {full_path.name} "
            f"| imgsz={imgsz} | classes={num_classes}"
        )
        return self.active_info[m_type]