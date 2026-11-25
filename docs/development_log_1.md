# NHẬT KÝ PHÁT TRIỂN DỰ ÁN (DEV LOG) — SmartDashcam

---

## Phiên làm việc: 22/11/2026

### 1. Thông tin công việc hôm nay
- **Ngày thực hiện:** 22/11/2026.
- **Trạng thái đầu phiên (đã xác nhận hoạt động):**
  - Màn hình HUD (UC-03) đã hoạt động.
  - Nhận diện vật cản, phát còi cảnh báo và giọng đọc TTS đã ổn định.
  - Kết nối WebSocket và API giữa các dịch vụ đã thông suốt.
  - Phần kết nối camera ngoài (ngoài webcam test) được thống nhất để làm sau.
- **Các mục tiêu đã đặt ra:**
  1. Xây dựng luồng tự động ghi nhận sự kiện cảnh báo va chạm (`WARNING` / `CRITICAL`) từ FastAPI AI Service về Flask Web App và lưu vào SQLite (tạm thời chưa lưu ảnh chụp hiện trường, để `snapshot_path = None`).
  2. Xây dựng các chức năng thuộc module **Lịch sử cảnh báo va chạm (UC-04)**: xem danh sách, xem chi tiết, xóa mềm.
  3. Xây dựng module **Cài đặt người dùng (UC-05)**: lưu ngưỡng cảnh báo vào SQLite và đồng bộ nóng sang FastAPI AI Service.
  4. Kiểm thử thực tế trên webcam và xử lý các lỗi phát sinh.
- **Những nội dung đã thực hiện:**
  - Tạo service `AlertReporter` gửi cảnh báo bất đồng bộ từ FastAPI sang Flask (có cơ chế cooldown 5 giây và ưu tiên nâng mức từ `WARNING` lên `CRITICAL`).
  - Nối `user_id` từ Flask session qua trang HUD (`hud.html` → `hud.js`) sang WebSocket `/ws/detect`.
  - Xây dựng API nội bộ `POST /api/internal/alerts` và các route UC-04 trong `alert_controller.py`.
  - Xây dựng route `GET/POST /driver/settings` trong `setting_controller.py` và đồng bộ cấu hình qua `POST /api/v1/config` bên FastAPI.
  - Khắc phục các lỗi: lệch tên cột ORM, `404 Not Found` ở API đồng bộ cấu hình, lỗi chỉ ghi nhận mức `WARNING`, sai múi giờ UTC, lệch biến hiển thị mức độ trong `history.html` và bổ sung route xóa mềm từ Modal.
- **Kết quả đạt được:**
  - Luồng **HUD → FastAPI WebSocket → `AlertReporter` → Flask `POST /api/internal/alerts` → SQLite** đã hoạt động và lưu thành công (mã `201`), ghi nhận được cả bản ghi `WARNING` và `CRITICAL` trong CSDL (`[(21, 'CRITICAL', 1.01), (20, 'CRITICAL', 0.94), ...]`).
  - Giao diện `/driver/settings` đã lưu được ngưỡng vào SQLite và đồng bộ sang AI Service.
  - Các bản vá cho hiển thị badge đỏ `CRITICAL`, giờ địa phương (UTC+7) và nút xóa mềm đã được cung cấp, đang chờ kiểm thử xác nhận cuối cùng trên giao diện.

---

### 2. Những thay đổi trong dự án

#### File tạo mới
- **`ai_service/services/alert_reporter.py`**
  - **Mục đích:** Định nghĩa class `AlertReporter` kiểm tra điều kiện gửi cảnh báo (`WARNING`/`CRITICAL`), áp dụng cooldown 5 giây theo `user_id`, ưu tiên vượt cooldown khi chuyển từ `WARNING` sang `CRITICAL`, lọc các vật thể nguy hiểm và gửi `POST /api/internal/alerts` trên thread nền để không làm giảm FPS của WebSocket.

#### File chỉnh sửa
- **`ai_service/main.py`**
  - **Mục đích:** Khởi tạo `app.state.alert_reporter = AlertReporter(cooldown_sec=5.0)` trong `lifespan`; kiểm tra/đăng ký `config_router` đúng prefix `/api/v1`.
- **`ai_service/api/ws_detect.py`**
  - **Mục đích:** Đọc `user_id` từ query string (`ws://127.0.0.1:8001/ws/detect?user_id=...`) và gọi `alert_reporter.report_async(..., snapshot_path=None)` ngay sau khi `obstacle_tracker.process_frame(frame)` chạy xong.
- **`ai_service/api/config_routes.py`**
  - **Mục đích:** Triển khai endpoint `POST /api/v1/config` với schema `AIConfigUpdate` (`conf_threshold`, `ttc_warning_sec`, `ttc_danger_sec`) để cập nhật trực tiếp lên `request.app.state.obstacle_tracker` trên RAM.
- **`web_app/views/templates/driver/hud.html`**
  - **Mục đích:** Truyền `window.CURRENT_USER_ID = {{ session.get('user_id') | tojson }};` trước khi nạp `hud.js`.
- **`web_app/views/static/js/hud.js`**
  - **Mục đích:** Gắn tham số `user_id` vào `WS_URL` khi kết nối WebSocket tới FastAPI.
- **`web_app/controllers/alert_controller.py`**
  - **Mục đích:**
    - `POST /api/internal/alerts`: Nhận JSON từ FastAPI, tạo thông điệp cảnh báo và lưu vào `CollisionAlert` + `AlertObject` (khớp đúng tên cột ORM, gán `created_at=datetime.now()`, `updated_at=datetime.now()`).
    - `GET /driver/history`: Truy vấn tối đa 100 bản ghi chưa xóa mềm (`deleted_at IS NULL`), hỗ trợ lọc theo `risk_level`, đếm thống kê tổng quan và render `driver/history.html`.
    - `GET /driver/history/<int:alert_id>`: Truy vấn chi tiết 1 cảnh báo kèm danh sách `AlertObject` liên quan và render `driver/history_detail.html`.
    - `POST /driver/history/<int:alert_id>/delete` & `POST /driver/history/delete`: Thực hiện xóa mềm (`deleted_at = datetime.now()`) cho cả `CollisionAlert` và các `AlertObject` con (hỗ trợ cả form Modal từ `history.html`).
- **`web_app/controllers/setting_controller.py`**
  - **Mục đích:** Triển khai `GET/POST /driver/settings`, tự khởi tạo `UserSetting` mặc định nếu tài xế chưa có cấu hình, kiểm tra ràng buộc `ttc_danger_sec < ttc_warning_sec`, lưu SQLite và gọi `POST /api/v1/config` đồng bộ nóng sang FastAPI.
- **`web_app/main.py`**
  - **Mục đích:** Import và đăng ký `alert_bp` (từ `web_app.controllers.alert_controller`) và `setting_bp` (từ `web_app.controllers.setting_controller`).
- **`web_app/views/templates/driver/history.html`** *(Đã đề xuất chỉnh sửa, chờ xác nhận sau kiểm thử)*
  - **Mục đích:** Sửa 2 dòng Jinja2 (ở bảng Desktop và Card Mobile) từ `item.severity or item.alert_level` sang `item.risk_level or item.severity or item.alert_level` để hiển thị đúng badge đỏ `CRITICAL`.

#### File đã xóa
- Không có file nào bị xóa (chỉ lưu ý xóa các route stub trùng lặp nếu có trong `main.py` hoặc `monitor_controller.py`).

#### Thay đổi CSDL
- Không thay đổi cấu trúc bảng/cột. Đã kiểm tra và xác nhận chính xác schema ORM hiện tại:
  - **`CollisionAlert`:** `['id', 'user_id', 'alert_type', 'risk_level', 'message', 'min_ttc', 'snapshot_path', 'created_at', 'updated_at', 'deleted_at']`
  - **`AlertObject`:** `['id', 'alert_id', 'track_id', 'object_label', 'confidence', 'bbox_x1', 'bbox_y1', 'bbox_x2', 'bbox_y2', 'estimated_ttc', 'created_at', 'updated_at', 'deleted_at']`
  - **`UserSetting`:** `['id', 'user_id', 'vehicle_type', 'tts_enabled', 'alert_sound_enabled', 'conf_threshold', 'ttc_warning_sec', 'ttc_danger_sec', 'created_at', 'updated_at', 'deleted_at']`

---

### 3. Công nghệ và kiến trúc
- **Công nghệ & Thư viện:**
  - **Web App (`web_app`):** Python (venv `web_app\.venv`), Flask (Blueprint, Jinja2, session, flash), SQLAlchemy ORM, SQLite, `requests`, Bootstrap 5 + Bootstrap Icons.
  - **AI Service (`ai_service`):** Python (venv `ai_service\.venv`), FastAPI, WebSocket, OpenCV (`cv2`), NumPy, Pydantic, `requests`.
- **Kiến trúc hệ thống (2 service tách biệt):**
  - **Flask Web App (`http://127.0.0.1:8000`):** Quản lý giao diện người dùng, xác thực session, lưu trữ SQLite (UC-04, UC-05) và điều phối cấu hình.
  - **FastAPI AI Service (`http://127.0.0.1:8001`):** Xử lý luồng video thời gian thực qua WebSocket (`/ws/detect`), chạy `obstacle_tracker` và `sign_detector`.
- **Giao tiếp & xử lý dữ liệu:**
  - Trình duyệt (`hud.js`) gửi frame ảnh dạng bytes qua `ws://127.0.0.1:8001/ws/detect?user_id=<id>` và nhận JSON kết quả nhận diện.
  - FastAPI gửi sự kiện cảnh báo qua `POST http://127.0.0.1:8000/api/internal/alerts` (chạy trên thread nền để không chặn vòng lặp WebSocket).
  - Flask gửi cấu hình ngưỡng mới qua `POST http://127.0.0.1:8001/api/v1/config` để cập nhật trực tiếp biến trên RAM của `obstacle_tracker`.
- **Quy ước lập trình đã thống nhất:**
  - Controller bên Flask đặt tên theo hậu tố `*_controller.py` (ví dụ: `alert_controller.py`, `setting_controller.py`, `sign_controller.py`...).
  - Thực hiện xóa mềm bằng cột `deleted_at` (không xóa cứng khỏi SQLite); mọi truy vấn hiển thị đều lọc `deleted_at.is_(None)`.
  - Render template trong phạm vi `with get_db() as db:` để tránh lỗi `DetachedInstanceError` của SQLAlchemy.

---

### 4. Lỗi đã gặp và cách khắc phục

| # | Nội dung lỗi | Nguyên nhân | Cách khắc phục | Trạng thái |
|---|---|---|---|---|
| 1 | `requests.exceptions.ConnectionError: [WinError 10061]` khi test `POST /api/internal/alerts` | Flask Web App chưa chạy trên cổng `8000` tại thời điểm chạy lệnh test. | Khởi chạy Flask ở một tab Terminal riêng (`web_app\.venv\Scripts\python.exe -m web_app.main`) trước khi gọi API. | **Đã sửa** |
| 2 | `[Internal Alerts] Lỗi lưu CSDL: 'severity' is an invalid keyword argument for CollisionAlert` (HTTP 500) | Code ban đầu dùng tên cột `severity`, `object_class`, `bbox` thay vì tên cột thực tế trong ORM (`risk_level`, `object_label`, `bbox_x1..y2`, `confidence`, `message`). | Kiểm tra danh sách cột thực tế bằng SQLAlchemy và cập nhật lại `receive_internal_alert()` trong `alert_controller.py`. Đã xác nhận trả về HTTP `201`. | **Đã sửa** |
| 3 | Thông báo *"AI Service chưa kết nối để đồng bộ nóng"* và log FastAPI báo `POST /api/v1/config 404 Not Found` | Trùng lặp `prefix="/api/v1"` giữa `ai_service/main.py` và `ai_service/api/config_routes.py` (hoặc chưa đăng ký router). | Thống nhất chỉ khai báo `prefix="/api/v1"` ở 1 nơi duy nhất và đăng ký `config_router` trong `ai_service/main.py`. | **Đã sửa** |
| 4 | Lịch sử chỉ ghi `WARNING`, không ghi nhận `CRITICAL` dù đưa vật cản lại gần | Ngưỡng `CRITICAL` mặc định thấp hơn mức TTC test thực tế (~1.40s) và cooldown 5 giây của `WARNING` chặn mất lần chuyển lên `CRITICAL`. | Cập nhật `AlertReporter.should_report()` cho phép `CRITICAL` vượt qua cooldown của `WARNING`; kéo chỉnh ngưỡng TTC trên `/driver/settings`. Đã xác nhận SQLite lưu bản ghi `CRITICAL` (ID 17–21). | **Đã sửa** |
| 5 | Thời gian trong bảng Lịch sử bị chậm 7 tiếng (hiển thị `08:48` thay vì `15:48`) | SQLite/SQLAlchemy mặc định lưu thời gian theo UTC thay vì giờ địa phương (UTC+7). | Truyền tường minh `created_at=datetime.now()` và `updated_at=datetime.now()` khi tạo `CollisionAlert` và `AlertObject` trong `alert_controller.py`. | **Đang kiểm tra** |
| 6 | Trang `/driver/history` chỉ hiển thị badge vàng `WARNING` dù CSDL đã lưu `CRITICAL` | `history.html` kiểm tra `item.severity or item.alert_level`, không có `item.risk_level`, nên luôn rơi về nhánh mặc định `'warning'`. | Cập nhật 2 chỗ trong `history.html` (Desktop & Mobile) để đọc `item.risk_level` trước. | **Đang kiểm tra** |
| 7 | Form Modal xóa mềm trong `history.html` gửi `POST /driver/history/delete` không khớp với route `/driver/history/<int:alert_id>/delete` | Khác biệt phương thức truyền `alert_id` (form body vs URL param). | Bổ sung thêm route `@alert_bp.route("/driver/history/delete", methods=["POST"])` (`delete_driver_history_form`) trong `alert_controller.py`. | **Đang kiểm tra** |

---

### 5. Những quyết định kỹ thuật đã thống nhất
- **Tạm hoãn chức năng lưu ảnh chụp hiện trường (`snapshot_saver.py`):**
  - *Phương án đã chọn:* Truyền `snapshot_path = None` trong `AlertReporter` và `alert_controller.py` để hoàn thiện luồng ghi DB trước.
  - *Phương án loại bỏ (tạm thời):* Chưa vẽ khung bao và lưu ảnh vào `storage/snapshots/` ở giai đoạn này.
  - *Lý do:* Giữ luồng lưu cảnh báo gọn, nhẹ, dễ kiểm thử ổn định trước khi bổ sung lưu ảnh sau.
- **Tạm hoãn phần kết nối camera ngoài:** Giữ nguyên luồng webcam trình duyệt để test, chỉ xử lý kết nối camera ngoài sau khi hoàn thiện các module nghiệp vụ.
- **Giữ cơ chế xóa mềm (`deleted_at`):** Không xóa cứng bản ghi trong `collision_alerts` và `alert_objects`.
- **Điều AI phiên sau KHÔNG được tự ý thay đổi nếu chưa trao đổi:**
  - Không đổi tên cột ORM của `CollisionAlert`, `AlertObject`, `UserSetting`.
  - Không đổi kiến trúc tách 2 service (Flask cổng `8000`, FastAPI cổng `8001`) và 2 môi trường ảo `.venv` riêng biệt.
  - Không tự ý thêm lại logic lưu ảnh `snapshot_saver.py` hoặc kết nối camera ngoài khi người dùng chưa yêu cầu.

---

### 6. Trạng thái hiện tại của dự án
- **Hoàn thành:**
  - Luồng lõi HUD (UC-03): Webcam, WebSocket AI, vẽ khung bao, còi cảnh báo, giọng đọc TTS.
  - Luồng gửi & lưu cảnh báo tự động: `AlertReporter` (FastAPI) → `POST /api/internal/alerts` (Flask) → SQLite (`CollisionAlert`, `AlertObject`).
  - Module Cài đặt (UC-05): Lưu `UserSetting` vào SQLite và đồng bộ nóng sang FastAPI (`POST /api/v1/config`).
- **Đang thực hiện / Đang kiểm tra:**
  - Xác nhận hiển thị trên `/driver/history`: badge đỏ `CRITICAL`, bộ lọc 1 chạm (Tất cả / Nguy hiểm / Cảnh báo), thời gian đúng giờ Việt Nam (UTC+7), chức năng xóa mềm từ Modal.
  - Kiểm tra trang chi tiết cảnh báo `/driver/history/<id>` (`web_app/views/templates/driver/history_detail.html`).
- **Chưa thực hiện:**
  - Chức năng lưu ảnh chụp hiện trường (`ai_service/services/snapshot_saver.py` và hiển thị ảnh thumbnail/modal).
  - Kết nối nguồn camera ngoài (để làm sau).
  - Cụm chức năng Admin (bắt đầu từ Quản lý biển báo `sign_controller.py` - UC-06, Quản lý người dùng `user_controller.py`, Quản lý model `model_controller.py`...).
- **Đang gặp vấn đề:**
  - Chưa ghi nhận lỗi chặn mới; cần người dùng xác nhận lại 3 điểm đang kiểm tra ở mục 4 (số 5, 6, 7).

---

### 7. Công việc tiếp theo (theo thứ tự ưu tiên)

1. **Xác nhận hoàn tất UC-04 (Lịch sử cảnh báo):**
   - Tải lại trang `/driver/history`, kiểm tra badge đỏ `CRITICAL` đã hiện đúng, nút lọc **Nguy hiểm / Cảnh báo** hoạt động, bản ghi mới lưu đúng giờ UTC+7, và nút **Xóa mềm** hoạt động không lỗi.
   - Bấm nút **Chi tiết** (`/driver/history/<id>`) để kiểm tra `web_app/views/templates/driver/history_detail.html` có bị lệch tên cột ORM (`risk_level`, `object_label`, `bbox_x1..y2`, `estimated_ttc`) hay không; sửa nếu có.
   - **File liên quan:** `web_app/views/templates/driver/history.html`, `web_app/views/templates/driver/history_detail.html`, `web_app/controllers/alert_controller.py`.

2. **Chuyển sang cụm chức năng Admin — Quản lý biển báo (UC-06) *(hoặc bổ sung lưu ảnh chụp nếu người dùng ưu tiên)*:**
   - Kiểm tra model bảng biển báo trong `web_app/models/` trước khi code.
   - Xây dựng CRUD biển báo trong `web_app/controllers/sign_controller.py`.
   - Nối dữ liệu biển báo từ DB thay cho dữ liệu cứng trong `ai_service` (`sign_detector.py`).
   - **File liên quan:** `web_app/controllers/sign_controller.py`, `web_app/models/...`, các template admin tương ứng.

3. **Bổ sung sau (theo yêu cầu người dùng):**
   - Lưu ảnh chụp hiện trường (`ai_service/services/snapshot_saver.py`) và nối lại vào `ws_detect.py` + `alert_reporter.py`.
   - Kết nối camera ngoài cho màn hình HUD.

---

### 8. Hướng dẫn dành cho AI ở phiên tiếp theo (HANDOFF)

> **Chỉ thị bàn giao cho AI phiên kế tiếp:**
> 1. **Đọc kỹ trạng thái trước khi hành động:** Hệ thống gồm 2 service chạy song song: **Flask (`web_app`, cổng `8000`)** và **FastAPI (`ai_service`, cổng `8001`)**. Luồng ghi DB từ HUD và đồng bộ cấu hình UC-05 đã hoạt động; không viết lại các phần đã ổn định.
> 2. **Không giả định các mục "Đang kiểm tra" là đã xong:** Trước khi sang module mới, hãy hỏi hoặc xác nhận với người dùng rằng 3 bản vá cuối phiên (badge đỏ `CRITICAL` trong `history.html`, giờ UTC+7, và nút xóa mềm + trang `history_detail.html`) đã chạy ổn chưa.
> 3. **Luôn kiểm tra tên cột ORM và HTML trước khi viết code mới:** Tránh lỗi lệch tên trường như `severity` vs `risk_level` bằng cách yêu cầu người dùng gửi model hoặc chạy lệnh in `Model.__table__.columns` trước khi viết controller/template mới.
> 4. **Tôn trọng các quyết định đã thống nhất:** Giữ `snapshot_path = None` và chưa đụng vào phần kết nối camera ngoài cho đến khi người dùng chủ động yêu cầu. Mọi thao tác xóa lịch sử phải là xóa mềm (`deleted_at`).
> 5. **Phong cách làm việc:** Chia nhỏ từng bước, cung cấp code rõ ràng theo đúng tên file thực tế (`*_controller.py`), kèm lệnh kiểm tra ngắn gọn sau mỗi bước.