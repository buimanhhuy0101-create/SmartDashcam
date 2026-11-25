# KIẾN TRÚC & CẤU TRÚC HỆ THỐNG — SMARTDASHCAM

* **Phiên bản tài liệu:** 1.2
* **Ngày cập nhật:** 24/11/2026

---

## 1. Kiến Trúc Tổng Thể (2 Service Tách Biệt)

Hệ thống chạy cục bộ gồm 2 dịch vụ độc lập với 2 môi trường ảo Python (`.venv`) riêng biệt:

```text
[Trình duyệt (View/HUD)] ──(HTTP CRUD/Auth & GET /snapshots/...)──> [Flask Web App :8000 (web_app)] ──> [SQLite: smartdashcam.db]
         │                                                                      ▲                              ▲
 (WS /ws/detect?user_id=...)                                            (REST API nội bộ)            (Read-only RAM Cache)
         ▼                                                                      ▼                              │
[FastAPI AI Service :8001 (ai_service)] ◄───────► [Thư mục dùng chung: storage/models/ & storage/snapshots/] ──┘
```

### Phân chia trách nhiệm
* **Flask Web App (`web_app`, cổng `8000`, venv `web_app\.venv`):** Chịu trách nhiệm toàn bộ thao tác ghi/CRUD với SQLite qua SQLAlchemy ORM; quản lý giao diện, xác thực session (Flask Signed Cookie), phân quyền (`0`: Admin, `1`: Driver), lịch sử cảnh báo, phục vụ ảnh hiện trường (`GET /snapshots/<path:filename>`), cài đặt cá nhân & đổi mật khẩu (UC-05, UC-09) và cụm Admin (UC-06, UC-07, UC-08, Dashboard, kèm xem lại & khôi phục dữ liệu đã xóa mềm).
* **FastAPI AI Service (`ai_service`, cổng `8001`, venv `ai_service\.venv`):** Chạy nền giữ song song 2 mô hình trên RAM (`ObstacleTracker`: YOLOv11n COCO + ByteTrack; `SignDetector`: `best.pt` 56 lớp + RAM Cache); quản lý nạp nóng model (`ModelManager`); vẽ khung & lưu ảnh snapshot nền (`AlertReporter`).
  * *Lưu ý thực tế:* `SignDetector` có thực hiện đọc (read-only) từ SQLite để nạp RAM Cache 56 biển báo, tự nạp model `is_active = 1` khi khởi động và đọc/cache `user_settings` (`vehicle_type`, `conf_threshold`) theo `user_id`; mọi thao tác ghi dữ liệu vẫn tập trung duy nhất tại Flask Web App.

### Lệnh vận hành hệ thống
```powershell
# Cửa sổ 1 — Flask Web App ([http://127.0.0.1:8000](http://127.0.0.1:8000))
python -m web_app.main

# Cửa sổ 2 — FastAPI AI Service ([http://127.0.0.1:8001](http://127.0.0.1:8001))
uvicorn ai_service.main:app --host 127.0.0.1 --port 8001
```

---

## 2. Hợp Đồng Giao Tiếp (API Contract)

| Giao thức & Endpoint | Chiều gọi | Trạng thái | Chức năng chính |
| :--- | :--- | :--- | :--- |
| `WS /ws/detect?user_id=<id>` | Browser ↔ FastAPI | **Đã hoạt động** *(lọc biển khác loại xe 1 lần: Đang kiểm tra)* | Gọi `sign_detector.reset_session(user_id)` khi kết nối; chạy song song `ObstacleTracker` và `SignDetector` (`user_id=user_id`); truyền `frame=frame` vào `alert_reporter.report_async(...)`; trả JSON gồm `obstacles`, `warning_level`, `roi`, `signs` (có cờ `applies_to_vehicle`). |
| `POST /api/internal/alerts` | FastAPI → Flask | **Đã hoạt động** | `AlertReporter` kiểm tra cooldown 5s (vượt cooldown khi nâng mức `WARNING -> CRITICAL`), vẽ khung + nhãn vật thể nguy hiểm lên bản sao khung hình, lưu ảnh `.jpg` vào `AIConfig.SNAPSHOTS_DIR` (`storage/snapshots/`) trên luồng nền `_save_and_send`, gửi sự kiện kèm tên file về Flask để chuẩn hóa và lưu SQLite. |
| `GET /snapshots/<path:filename>` | Browser → Flask | **Đang kiểm tra** | Phục vụ ảnh chụp hiện trường từ `Config.SNAPSHOTS_DIR` (`storage/snapshots/`) qua `send_from_directory` (có kiểm tra đăng nhập qua session). |
| `POST /api/v1/config` | Flask → FastAPI | **Đã hoạt động** *(đồng bộ `SignDetector`: Đang kiểm tra)* | Cập nhật nóng `conf_threshold`, `ttc_warning_sec`, `ttc_danger_sec` cho `ObstacleTracker`, đồng thời cập nhật `conf_threshold` và gọi `sign_detector.clear_user_cache()` (xóa cache `user_settings` và `_seen_irrelevant`). |
| `POST /api/v1/signs/reload-cache` | Flask → FastAPI | **Đang kiểm tra** | Được gọi từ `sign_controller.py` (`_sync_sign_cache_to_ai`) sau khi Admin thêm, sửa, xóa mềm hoặc **khôi phục** biển báo ở UC-06 để gọi `sign_detector.reload_catalog_cache()` nạp lại danh sách biển báo đang hoạt động lên RAM Cache. |
| `POST /api/v1/models/reload` | Flask → FastAPI | **Đã hoạt động** | Được gọi từ `model_controller.py` (UC-07); `ModelManager` kiểm tra SHA-256 (`checksum.py`), chạy thử (Dummy Inference), nạp nóng (Hot-Reload) sang `SignDetector` / `ObstacleTracker` và tự động Rollback nếu lỗi. |
| `GET /api/v1/health` | Flask → FastAPI | **Đã hoạt động** | Kiểm tra trạng thái hoạt động của AI Service (đã nối với Admin Dashboard `/admin/dashboard`). |

---

## 3. Cấu Trúc Thư Mục Thực Tế

```text
SmartDashcam/
├── .env, .env.example, .gitignore, README.md
├── requirements_web.txt, requirements_ai.txt
├── run_web.bat, run_ai.bat, yolo11n.pt
├── scripts/
│   ├── init_db.py
│   └── test_video_source/
├── storage/
│   ├── database/smartdashcam.db (+ -shm, -wal)
│   ├── models/                       # Chứa file .pt (bao gồm best.pt 56 lớp)
│   └── snapshots/                    # Chứa ảnh .jpg chụp hiện trường cảnh báo
├── tests/ (test_auth.py, test_collision_logic.py, test_model_manager.py)
├── ai_service/
│   ├── config.py, main.py
│   ├── api/      (config_routes.py, health_routes.py, model_routes.py, ws_detect.py)
│   ├── core/     (collision_logic.py, model_manager.py, obstacle_tracker.py, runtime_state.py, sign_detector.py)
│   ├── services/ (alert_reporter.py, snapshot_saver.py)
│   └── utils/    (checksum.py, image_utils.py)
└── web_app/
    ├── config.py, main.py            # Đã tích hợp /admin/dashboard nối CSDL thật & ping AI
    ├── database/    (base.py, connection.py, seed.py)
    ├── models/      (ai_model.py, alert_object.py, collision_alert.py, sign_catalog.py, sign_category.py, sign_vehicle.py, user.py, user_setting.py)
    ├── controllers/ (alert_controller.py, auth_controller.py, model_controller.py, monitor_controller.py, setting_controller.py, sign_controller.py, user_controller.py)
    ├── services/    (ai_client.py, file_service.py, security.py, sign_cache.py)
    ├── utils/       (decorators.py, validators.py)
    └── views/
        ├── static/    (css/: auth.css, style.css; js/: alert_sound.js, hud.js, tts.js; img/; sign_icons/)
        └── templates/ (base.html; auth/; driver/; admin/)
```

---

## 4. Công Nghệ, Thư Viện & Cấu Hình

* **Web App (`requirements_web.txt`):** `Flask>=3.0`, `SQLAlchemy>=2.0`, `python-dotenv>=1.0`, `requests>=2.31`, `email-validator>=2.1`, Bootstrap 5 + Bootstrap Icons.
* **AI Service (`requirements_ai.txt`):** `fastapi>=0.110`, `uvicorn[standard]>=0.29`, `websockets>=12.0`, `python-multipart>=0.0.9`, `python-dotenv>=1.0`, `requests>=2.31`, `numpy>=1.26`, `opencv-python>=4.9`, `ultralytics>=8.3`, `lap>=0.5`.
* **Biến môi trường chính (`.env`):**
  * `WEB_HOST=127.0.0.1`, `WEB_PORT=8000`, `WEB_APP_URL=http://127.0.0.1:8000`
  * `AI_HOST=127.0.0.1`, `AI_PORT=8001`, `AI_SERVICE_URL=http://127.0.0.1:8001`
  * `DATABASE_URL=sqlite:///storage/database/smartdashcam.db`
  * `MODELS_DIR=storage/models`, `SNAPSHOTS_DIR=storage/snapshots`

---

## 5. Quy Ước Lập Trình & Kiến Trúc Đã Thống Nhất
* Controller bên Flask đặt tên theo hậu tố `*_controller.py` (ánh xạ theo Use Case: `auth`, `monitor`, `alert`, `setting`, `sign`, `model`, `user`).
* Mọi truy vấn hiển thị dữ liệu mặc định phải lọc xóa mềm (`deleted_at IS NULL` qua `active_select(model)`). Ngoại lệ duy nhất là chế độ xem tab `Đã xóa mềm` (`?status=deleted`, lọc `deleted_at IS NOT NULL`) và thao tác khôi phục (`POST .../restore`) tại 3 phân hệ Admin (`users`, `signs`, `models`).
* Render template Jinja2 bên trong khối `with get_db() as db:` để tránh lỗi `DetachedInstanceError` của SQLAlchemy.
* Không khai báo trùng `prefix="/api/v1"` giữa `ai_service/main.py` và file router con.
* Ảnh chụp hiện trường lưu tại `storage/snapshots/` (`Config.SNAPSHOTS_DIR` / `AIConfig.SNAPSHOTS_DIR`) và phục vụ qua route riêng `GET /snapshots/<path:filename>`, không di chuyển vào `web_app/views/static/`.
* Phân trang tại `history.html` và `signs.html` thực hiện phía client (`PAGE_SIZE = 6`) để giữ tìm kiếm/lọc nhanh tức thì và không cần sửa controller Python.