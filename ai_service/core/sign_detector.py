import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np
from ultralytics import YOLO

from ai_service.config import BASE_DIR


def _normalize_vehicle(v: str | None) -> str | None:
    if not v:
        return None
    val = v.strip().lower()
    if val == "motorcycle":
        return "motorbike"
    return val


class SignDetector:
    def __init__(
        self,
        conf: float = 0.55,
        min_confirm_frames: int = 2,
        cooldown_sec: float = 6.0,
    ) -> None:
        self.conf = conf
        self.min_confirm_frames = min_confirm_frames
        self.cooldown_sec = cooldown_sec

        self._lock = threading.Lock()
        self.model: YOLO | None = None
        self.imgsz: int = 640
        self.catalog_cache: dict[str, dict[str, Any]] = {}
        self._user_settings_cache: dict[int, dict[str, Any]] = {}

        # Lưu các mã biển KHÔNG áp dụng cho loại xe hiện tại đã nhận diện 1 lần -> bỏ qua các lần sau
        self._seen_irrelevant: dict[tuple[int | None, str], set[str]] = {}

        # Bộ đếm lọc ổn định nhiều khung hình và cooldown theo từng mã biển
        self._frame_streaks: dict[str, int] = {}
        self._last_emit: dict[str, float] = {}

        self.db_path = BASE_DIR / "storage" / "database" / "smartdashcam.db"
        self.reload_catalog_cache()
        self.load_active_model_from_db()

    def clear_user_cache(self) -> None:
        """Xóa cache cấu hình tài xế và danh sách biển bỏ qua khi đổi cài đặt."""
        with self._lock:
            self._user_settings_cache.clear()
            self._seen_irrelevant.clear()

    def reset_session(self, user_id: int | None = None) -> None:
        """Reset danh sách biển đã bỏ qua khi bắt đầu phiên HUD mới."""
        with self._lock:
            if user_id is None:
                self._seen_irrelevant.clear()
            else:
                for key in list(self._seen_irrelevant.keys()):
                    if key[0] == user_id:
                        del self._seen_irrelevant[key]
            self._frame_streaks.clear()
            self._last_emit.clear()

    def _is_applicable(
        self, driver_vehicle: str | None, allowed_vehicles: list[str] | None
    ) -> bool:
        if not driver_vehicle:
            return True
        vehicles = allowed_vehicles or ["all"]
        return "all" in vehicles or driver_vehicle in vehicles

    def _get_user_settings(self, user_id: int | None) -> dict[str, Any]:
        if not user_id or not self.db_path.exists():
            return {"vehicle_type": None, "conf_threshold": self.conf}

        with self._lock:
            cached = self._user_settings_cache.get(user_id)
        if cached is not None:
            return cached

        result: dict[str, Any] = {"vehicle_type": None, "conf_threshold": self.conf}
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT vehicle_type, conf_threshold
                FROM user_settings
                WHERE user_id = ? AND deleted_at IS NULL
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            conn.close()

            if row:
                result["vehicle_type"] = _normalize_vehicle(row["vehicle_type"])
                if row["conf_threshold"] is not None:
                    result["conf_threshold"] = float(row["conf_threshold"])
        except sqlite3.Error as exc:
            print(f"[SignDetector] Lỗi đọc user_settings: {exc}")

        with self._lock:
            self._user_settings_cache[user_id] = result
        return result

    def reload_catalog_cache(self) -> int:
        """Nạp từ điển 56 biển báo từ SQLite lên RAM Cache (tra cứu ~0ms)."""
        if not self.db_path.exists():
            print(f"[SignDetector] Không tìm thấy DB tại {self.db_path}")
            return 0

        cache: dict[str, dict[str, Any]] = {}
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            rows = cur.execute(
                """
                SELECT id, sign_code, name, tts_script, icon_url, priority
                FROM traffic_sign_catalog
                WHERE deleted_at IS NULL
                """
            ).fetchall()

            veh_rows = cur.execute(
                """
                SELECT sign_id, vehicle_type
                FROM traffic_sign_vehicles
                WHERE deleted_at IS NULL
                """
            ).fetchall()
            conn.close()

            vehicles_by_sign: dict[int, list[str]] = {}
            for vr in veh_rows:
                norm_v = _normalize_vehicle(vr["vehicle_type"])
                if norm_v:
                    vehicles_by_sign.setdefault(vr["sign_id"], []).append(norm_v)

            for r in rows:
                cache[r["sign_code"]] = {
                    "sign_code": r["sign_code"],
                    "name": r["name"],
                    "tts_script": r["tts_script"] or r["name"],
                    "icon_url": r["icon_url"],
                    "priority": r["priority"],
                    "vehicles": vehicles_by_sign.get(r["id"], ["all"]),
                }

            with self._lock:
                self.catalog_cache = cache
                self._seen_irrelevant.clear()
            print(f"[SignDetector] Đã nạp {len(cache)} biển báo vào RAM Cache.")
            return len(cache)
        except sqlite3.Error as exc:
            print(f"[SignDetector] Lỗi đọc RAM Cache biển báo: {exc}")
            return 0

    def load_active_model_from_db(self) -> None:
        """Tự động nạp model biển báo đang is_active=1 từ bảng ai_models khi khởi động."""
        if not self.db_path.exists():
            return

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT name, version, file_path, imgsz
                FROM ai_models
                WHERE model_type = 'sign'
                  AND is_active = 1
                  AND deleted_at IS NULL
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            conn.close()

            if not row:
                print("[SignDetector] Chưa có model biển báo nào được kích hoạt trong DB.")
                return

            model_path = Path(row["file_path"])
            if not model_path.is_absolute():
                model_path = (BASE_DIR / model_path).resolve()

            if not model_path.exists():
                print(f"[SignDetector] Không tìm thấy file model tại {model_path}")
                return

            loaded = YOLO(str(model_path))
            self.update_model(loaded, int(row["imgsz"] or 640))
            print(
                f"[SignDetector] Đã tự động nạp model biển báo: {row['name']} ({row['version']}) "
                f"| {len(loaded.names)} lớp"
            )
        except Exception as exc:
            print(f"[SignDetector] Lỗi tự nạp model biển báo: {exc}")

    def update_model(self, yolo_model: YOLO, imgsz: int = 640) -> None:
        """Cập nhật nóng model từ ModelManager (UC-07 Local Hot-Reload)."""
        with self._lock:
            self.model = yolo_model
            self.imgsz = imgsz
            self._frame_streaks.clear()

    def detect(
        self, frame: np.ndarray, user_id: int | None = None
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Trả về:
        - events: Danh sách biển báo mới (biển khác loại xe chỉ báo 1 lần duy nhất).
        - boxes: Khung biển báo để vẽ lên Canvas (bỏ qua các biển khác loại xe đã biết).
        """
        with self._lock:
            model = self.model
            imgsz = self.imgsz
            catalog = self.catalog_cache

        if model is None:
            return [], []

        user_cfg = self._get_user_settings(user_id)
        active_conf = user_cfg["conf_threshold"]
        driver_vehicle = user_cfg["vehicle_type"]

        ignore_key = (user_id, driver_vehicle) if driver_vehicle else None
        with self._lock:
            ignored_codes = (
                set(self._seen_irrelevant.get(ignore_key, set()))
                if ignore_key
                else set()
            )

        results = model.predict(
            source=frame,
            imgsz=imgsz,
            conf=active_conf,
            verbose=False,
        )
        if not results:
            self._frame_streaks.clear()
            return [], []

        res = results[0]
        names = res.names or {}
        boxes_out: list[dict[str, Any]] = []
        best_conf_in_frame: dict[str, float] = {}

        if res.boxes is not None:
            for box in res.boxes:
                cls_id = int(box.cls[0].item())
                conf = round(float(box.conf[0].item()), 2)
                sign_code = str(names.get(cls_id, cls_id))
                info = catalog.get(sign_code, {})
                applies = self._is_applicable(driver_vehicle, info.get("vehicles"))

                # Đã nhận diện 1 lần và không áp dụng cho loại xe hiện tại -> bỏ qua hoàn toàn
                if not applies and sign_code in ignored_codes:
                    continue

                x1, y1, x2, y2 = [round(float(v), 1) for v in box.xyxy[0].tolist()]
                boxes_out.append(
                    {
                        "sign_code": sign_code,
                        "name": info.get("name", sign_code),
                        "conf": conf,
                        "bbox": [x1, y1, x2, y2],
                    }
                )

                if conf > best_conf_in_frame.get(sign_code, 0.0):
                    best_conf_in_frame[sign_code] = conf

        seen_codes = set(best_conf_in_frame.keys())
        for code in list(self._frame_streaks.keys()):
            if code not in seen_codes:
                del self._frame_streaks[code]

        now = time.time()
        events_out: list[dict[str, Any]] = []

        for code, conf in best_conf_in_frame.items():
            self._frame_streaks[code] = self._frame_streaks.get(code, 0) + 1
            if self._frame_streaks[code] < self.min_confirm_frames:
                continue

            info = catalog.get(code, {})
            applies_to_vehicle = self._is_applicable(driver_vehicle, info.get("vehicles"))

            # Biển khác loại xe: ghi nhận 1 lần duy nhất rồi đưa vào danh sách bỏ qua
            if not applies_to_vehicle:
                if ignore_key is not None:
                    with self._lock:
                        self._seen_irrelevant.setdefault(ignore_key, set()).add(code)
                self._last_emit[code] = now
                events_out.append(
                    {
                        "sign_code": code,
                        "name": info.get("name", code),
                        "tts_script": info.get("tts_script", f"Phía trước có biển {code}"),
                        "icon_url": info.get("icon_url"),
                        "conf": conf,
                        "applies_to_vehicle": False,
                    }
                )
                continue

            if now - self._last_emit.get(code, 0.0) < self.cooldown_sec:
                continue

            self._last_emit[code] = now
            events_out.append(
                {
                    "sign_code": code,
                    "name": info.get("name", code),
                    "tts_script": info.get("tts_script", f"Phía trước có biển {code}"),
                    "icon_url": info.get("icon_url"),
                    "conf": conf,
                    "applies_to_vehicle": True,
                }
            )

        return events_out, boxes_out