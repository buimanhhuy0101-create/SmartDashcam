import time
import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/detect")
async def websocket_detect(websocket: WebSocket):
    await websocket.accept()
    obstacle_tracker = websocket.app.state.obstacle_tracker
    sign_detector = websocket.app.state.sign_detector
    alert_reporter = websocket.app.state.alert_reporter

    # Lấy user_id từ URL: ws://127.0.0.1:8001/ws/detect?user_id=1
    raw_user_id = websocket.query_params.get("user_id")
    user_id = int(raw_user_id) if raw_user_id and raw_user_id.isdigit() else None
    if hasattr(sign_detector, "reset_session"):
        sign_detector.reset_session(user_id)
    try:
        while True:
            t_start = time.perf_counter()

            raw_bytes = await websocket.receive_bytes()
            np_arr = np.frombuffer(raw_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is None:
                await websocket.send_json({"error": "Invalid frame"})
                continue

            obstacle_res = obstacle_tracker.process_frame(frame)
            signs, sign_boxes = sign_detector.detect(frame, user_id=user_id)

            # Tự động chụp snapshot + gửi về Flask lưu DB khi gặp WARNING / CRITICAL
            alert_reporter.report_async(
                user_id=user_id,
                warning_level=obstacle_res["warning_level"],
                min_ttc=obstacle_res["min_ttc"],
                obstacles=obstacle_res["obstacles"],
                snapshot_path=None,
                frame=frame,
            )

            elapsed = max(time.perf_counter() - t_start, 1e-4)
            fps = round(1.0 / elapsed, 1)

            await websocket.send_json(
                {
                    "warning_level": obstacle_res["warning_level"],
                    "min_ttc": obstacle_res["min_ttc"],
                    "obstacles": obstacle_res["obstacles"],
                    "signs": signs,
                    "sign_boxes": sign_boxes,
                    "fps": fps,
                    "frame_size": obstacle_res["frame_size"],
                    "roi": obstacle_res.get("roi"),
                }
            )

    except WebSocketDisconnect:
        print("[WS /ws/detect] Client disconnected.")
    except Exception as exc:
        print(f"[WS /ws/detect] Error: {exc}")
        await websocket.close()