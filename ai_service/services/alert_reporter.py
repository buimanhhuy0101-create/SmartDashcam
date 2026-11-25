from datetime import datetime
import threading
import time
from typing import Any

import cv2
import numpy as np
import requests

from ai_service.config import AIConfig


class AlertReporter:
    """Gửi sự kiện cảnh báo va chạm (WARNING / CRITICAL) + lưu ảnh snapshot sang Flask."""

    def __init__(self, cooldown_sec: float = 5.0):
        self.cooldown_sec = cooldown_sec
        self.endpoint = f"{AIConfig.WEB_APP_URL.rstrip('/')}/api/internal/alerts"
        self._last_sent: dict[int, float] = {}
        self._last_level: dict[int, str] = {}
        self._lock = threading.Lock()

    def should_report(self, user_id: int | None, warning_level: str) -> bool:
        if not user_id or warning_level not in ("WARNING", "CRITICAL"):
            return False

        now = time.time()
        with self._lock:
            last_time = self._last_sent.get(user_id, 0.0)
            last_level = self._last_level.get(user_id)
            is_escalated = warning_level == "CRITICAL" and last_level == "WARNING"

            # Ưu tiên vượt cooldown 5s nếu mức cảnh báo nâng từ WARNING lên CRITICAL
            if not is_escalated and (now - last_time < self.cooldown_sec):
                return False

            self._last_sent[user_id] = now
            self._last_level[user_id] = warning_level
            return True

    def report_async(
        self,
        user_id: int | None,
        warning_level: str,
        min_ttc: float | None,
        obstacles: list[dict[str, Any]],
        snapshot_path: str | None = None,
        frame: np.ndarray | None = None,
    ) -> bool:
        """Kiểm tra cooldown, sao chép khung hình rồi lưu ảnh + POST ở luồng nền."""
        if not self.should_report(user_id, warning_level):
            return False

        risky_objects = [
            obj for obj in obstacles if obj.get("level") in ("WARNING", "CRITICAL")
        ]
        frame_copy = frame.copy() if frame is not None else None

        thread = threading.Thread(
            target=self._save_and_send,
            args=(user_id, warning_level, min_ttc, risky_objects, snapshot_path, frame_copy),
            daemon=True,
        )
        thread.start()
        return True

    def _save_snapshot(
        self,
        user_id: int,
        frame: np.ndarray,
        risky_objects: list[dict[str, Any]],
    ) -> str | None:
        try:
            AIConfig.SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
            annotated = frame.copy()

            for obj in risky_objects:
                bbox = obj.get("bbox")
                if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                    continue
                x1, y1, x2, y2 = [int(v) for v in bbox]
                color = (0, 0, 255) if obj.get("level") == "CRITICAL" else (0, 165, 255)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                label = f"{obj.get('label', 'obj')} #{obj.get('track_id', '')} | {obj.get('estimated_ttc', '')}s"
                cv2.putText(
                    annotated,
                    label,
                    (x1, max(18, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    color,
                    2,
                )

            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"alert_u{user_id}_{ts}.jpg"
            dest = AIConfig.SNAPSHOTS_DIR / filename
            if cv2.imwrite(str(dest), annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 85]):
                return filename
        except Exception as exc:
            print(f"[AlertReporter] Lỗi lưu ảnh snapshot: {exc}")
        return None

    def _save_and_send(
        self,
        user_id: int,
        warning_level: str,
        min_ttc: float | None,
        risky_objects: list[dict[str, Any]],
        snapshot_path: str | None,
        frame: np.ndarray | None,
    ) -> None:
        if snapshot_path is None and frame is not None:
            snapshot_path = self._save_snapshot(user_id, frame, risky_objects)

        payload = {
            "user_id": user_id,
            "alert_type": "FCW",
            "severity": warning_level,
            "min_ttc": min_ttc,
            "snapshot_path": snapshot_path,
            "objects": risky_objects,
        }

        try:
            resp = requests.post(self.endpoint, json=payload, timeout=3.0)
            if resp.status_code >= 400:
                print(
                    f"[AlertReporter] Flask trả về lỗi {resp.status_code}: {resp.text}"
                )
        except Exception as exc:
            print(f"[AlertReporter] Không gửi được cảnh báo về Flask: {exc}")