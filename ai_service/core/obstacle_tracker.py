from pathlib import Path
from typing import Any
import numpy as np
from ultralytics import YOLO

# Các lớp COCO giám sát
TARGET_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    15: "cat",
    16: "dog",
}


class ObstacleTracker:
    def __init__(
        self,
        model_path: Path,
        conf: float = 0.45,
        ttc_warning_sec: float = 3.0,
        ttc_danger_sec: float = 1.5,
    ):
        # Nếu chưa có file trong storage/models/, Ultralytics sẽ tự tải yolo11n.pt
        source = str(model_path) if model_path.exists() else model_path.name
        self.model = YOLO(source)
        self.conf_threshold = conf
        self.ttc_warning_sec = ttc_warning_sec
        self.ttc_danger_sec = ttc_danger_sec

    def process_frame(
        self,
        frame: np.ndarray,
        ttc_warning: float | None = None,
        ttc_danger: float | None = None,
    ) -> dict[str, Any]:
        # Ưu tiên tham số truyền vào; nếu không có thì lấy ngưỡng động trên RAM
        warn_th = self.ttc_warning_sec if ttc_warning is None else ttc_warning
        danger_th = self.ttc_danger_sec if ttc_danger is None else ttc_danger

        frame_h, frame_w = frame.shape[:2]

        # Khung nhìn nhỏ (ROI) ở làn đường phía trước mũi xe
        roi_x1 = frame_w * 0.15  # Cắt 15% lề trái
        roi_x2 = frame_w * 0.85  # Cắt 15% lề phải
        roi_y1 = frame_h * 0.50  # Cắt 50% phần trời / vật ở quá xa
        roi_y2 = frame_h * 0.95  # Cắt 5% phần nắp capo sát đáy

        # Bỏ giới hạn classes để bắt được cả vật thể lạ khi quá lớn áp sát xe
        results = self.model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=self.conf_threshold,
            verbose=False,
        )
        obstacles = []
        min_ttc: float | None = None

        if results and results[0].boxes is not None:
            boxes = results[0].boxes
            xyxy_list = boxes.xyxy.cpu().numpy()
            cls_list = boxes.cls.cpu().numpy().astype(int)
            conf_list = boxes.conf.cpu().numpy()
            id_list = (
                boxes.id.cpu().numpy().astype(int)
                if boxes.id is not None
                else [-1] * len(xyxy_list)
            )

            frame_area = max(frame_w * frame_h, 1)
            roi_area = max((roi_x2 - roi_x1) * (roi_y2 - roi_y1), 1)

            for xyxy, cls_id, score, track_id in zip(
                xyxy_list, cls_list, conf_list, id_list
            ):
                x1, y1, x2, y2 = [float(v) for v in xyxy]
                cls_int = int(cls_id)

                # Tính tỷ lệ diện tích chiếm khung hình & phần giao với ROI
                box_area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
                frame_cover_ratio = box_area / frame_area

                inter_x1 = max(x1, roi_x1)
                inter_y1 = max(y1, roi_y1)
                inter_x2 = min(x2, roi_x2)
                inter_y2 = min(y2, roi_y2)
                inter_area = max(0.0, inter_x2 - inter_x1) * max(0.0, inter_y2 - inter_y1)
                roi_cover_ratio = inter_area / roi_area

                # Vật thể quá lớn chiếm phần lớn khung hình hoặc vùng giám sát
                is_oversized = (frame_cover_ratio >= 0.35) or (roi_cover_ratio >= 0.45)

                # Nếu không phải 8 lớp giao thông thì chỉ giữ lại khi quá lớn
                is_target_class = cls_int in TARGET_CLASSES
                if not is_target_class and not is_oversized:
                    continue

                # Nếu không phải vật quá lớn, áp dụng lọc điểm chân trong ROI
                cx = (x1 + x2) / 2.0
                in_roi = (roi_x1 <= cx <= roi_x2) and (roi_y1 <= y2 <= roi_y2)
                if not in_roi and not is_oversized:
                    continue

                h_ratio = max((y2 - y1) / max(frame_h, 1), 0.01)

                # Heuristic: vật càng chiếm chiều cao khung hình thì TTC càng nhỏ
                estimated_ttc = round(max(0.4, min(6.0, 0.9 / h_ratio)), 2)

                level = "SAFE"
                if is_oversized or estimated_ttc <= danger_th:
                    level = "CRITICAL"
                    if is_oversized:
                        estimated_ttc = min(estimated_ttc, round(danger_th, 2))
                elif estimated_ttc <= warn_th:
                    level = "WARNING"

                if min_ttc is None or estimated_ttc < min_ttc:
                    min_ttc = estimated_ttc

                label = TARGET_CLASSES.get(
                    cls_int, self.model.names.get(cls_int, "object")
                )

                obstacles.append(
                    {
                        "track_id": int(track_id),
                        "label": label,
                        "conf": round(float(score), 2),
                        "bbox": [round(x1), round(y1), round(x2), round(y2)],
                        "estimated_ttc": estimated_ttc,
                        "level": level,
                    }
                )

        warning_level = "SAFE"
        if min_ttc is not None:
            if min_ttc <= danger_th:
                warning_level = "CRITICAL"
            elif min_ttc <= warn_th:
                warning_level = "WARNING"

        return {
            "obstacles": obstacles,
            "min_ttc": min_ttc,
            "warning_level": warning_level,
            "frame_size": [frame_w, frame_h],
            "roi": [round(roi_x1), round(roi_y1), round(roi_x2), round(roi_y2)],
        }