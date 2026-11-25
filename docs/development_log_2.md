# NHẬT KÝ PHÁT TRIỂN DỰ ÁN (DEV LOG) — SmartDashcam

---

## Phiên làm việc: 22/11/2026 (Phiên 2 — Hoàn thiện Phân hệ Tài xế & Cập nhật Đặc tả)

### 1. Thông tin công việc hôm nay
- **Ngày thực hiện:** 22/11/2026 (Phiên 2).
- **Các mục tiêu đã đặt ra:**
  1. Khắc phục dứt điểm lỗi chưa hiện badge đỏ `CRITICAL` và kiểm tra giờ địa phương (UTC+7) trên trang Lịch sử cảnh báo (`/driver/history`).
  2. Kiểm tra và sửa lỗi đồng bộ nóng ngưỡng TTC (`ttc_danger_sec`) từ trang Cài đặt (`/driver/settings`) sang AI Service.
  3. Giới hạn phạm vi bắt vật cản theo **Vùng giám sát (ROI)**, vẽ khung ROI lên màn hình HUD và bổ sung cảnh báo `CRITICAL` cho vật thể quá lớn.
  4. Tích hợp giọng đọc TTS tiếng Việt cảnh báo vật cản và tạm tắt nhận diện biển báo giả lập để tập trung kiểm thử vật cản.
  5. Sửa lỗi hiển thị tên đối tượng và tọa độ BBox trong trang chi tiết lịch sử (`history_detail.html`).
  6. Đối chiếu và cập nhật tài liệu Đặc tả chức năng (`Log_Dac_Ta_Chuc_Nang.md`) cho phân hệ Tài xế (UC-03, UC-04, UC-05).
- **Những nội dung đã thực hiện:**
  - Sửa nốt dòng đọc `item.risk_level` ở bảng Desktop trong `history.html`.
  - Đồng bộ tên thuộc tính ngưỡng (`conf_threshold`, `ttc_warning_sec`, `ttc_danger_sec`) trong `ObstacleTracker` khớp với `config_routes.py`.
  - Bổ sung logic lọc điểm chân vật cản theo khung ROI (`x: 15%–85%`, `y: 50%–95%`) và logic nhận diện vật thể quá lớn (`>= 35%` khung hình hoặc `>= 45%` ROI → ép `CRITICAL`) trong `obstacle_tracker.py`.
  - Truyền tọa độ `roi` qua WebSocket (`ws_detect.py`) và vẽ khung nét đứt **"VÙNG GIÁM SÁT"** lên canvas trong `hud.js`.
  - Tích hợp hàm `speakObstacleAlert()` trong `hud.js` để đọc cảnh báo vật cản tiếng Việt qua `window.SmartTTS` (có cooldown 4 giây và ưu tiên ngắt câu khi lên `CRITICAL`).
  - Tạm tắt `sign_detector.detect(frame)` (gán `signs = []`) trong `ws_detect.py` để dừng biển báo giả lập.
  - Cung cấp bản vá cho `history_detail.html` để khớp tên cột ORM (`alert.risk_level`, `obj.object_label`, `obj.bbox_x1..y2`, `obj.confidence`) và dịch nhãn sang tiếng Việt.
  - Viết lại bảng đặc tả chuẩn cho UC-03, UC-04, UC-05 khớp với mã nguồn thực tế.
- **Kết quả đạt được:**
  - Hoàn thiện ổn định phân hệ Tài xế (phần nhận diện vật cản): hiển thị badge đỏ `CRITICAL`, đúng giờ UTC+7, đồng bộ nóng ngưỡng TTC, lọc theo khung ROI hiển thị trực quan trên HUD, cảnh báo vật thể quá lớn và đọc TTS tiếng Việt cho vật cản.
  - Đã cập nhật xong nội dung đặc tả UC-03, UC-04, UC-05.

---

### 2. Những thay đổi trong dự án

#### File tạo mới
- Không tạo file mới trong phiên này.

#### File chỉnh sửa
- **`web_app/views/templates/driver/history.html`**
  - **Mục đích:** Sửa dòng đọc mức độ ở bảng Desktop từ `item.severity or item.alert_level` thành `item.risk_level or item.severity or item.alert_level` (trước đó mới sửa ở Card Mobile).
- **`ai_service/services/obstacle_tracker.py`** *(đường dẫn file `obstacle_tracker.py` trong `ai_service`)*
  - **Mục đích:**
    - Đổi `self.conf` thành `self.conf_threshold`, bổ sung `self.ttc_warning_sec` và `self.ttc_danger_sec` trong `__init__`; sửa `process_frame()` lấy ngưỡng động trên RAM thay vì tham số mặc định cứng (`3.0`, `1.5`).
    - Thêm bộ lọc khung nhìn nhỏ (ROI: `x1=15%`, `x2=85%`, `y1=50%`, `y2=95%`) theo điểm chân `(cx, y2)`.
    - Bỏ giới hạn `classes` trong `model.track()` để bắt được cả vật thể lạ nếu quá lớn; giữ quy tắc vật thể chiếm `>= 35%` diện tích khung hình hoặc `>= 45%` diện tích ROI sẽ bỏ qua bộ lọc ROI/lớp và ép thẳng lên `CRITICAL`.
    - Trả thêm trường `"roi": [x1, y1, x2, y2]` trong kết quả `process_frame()`.
- **`ai_service/api/ws_detect.py`**
  - **Mục đích:**
    - Bổ sung `"roi": obstacle_res.get("roi")` vào JSON trả về qua WebSocket `/ws/detect`.
    - Tạm đổi `signs = sign_detector.detect(frame)` thành `signs = []` để tắt biển báo giả lập trong lúc kiểm thử vật cản.
- **`web_app/views/static/js/hud.js`**
  - **Mục đích:**
    - Cập nhật `drawDetections(obstacles, frameSize, roi)` và `ws.onmessage` để vẽ khung nét đứt màu xanh **"VÙNG GIÁM SÁT"** theo tọa độ `data.roi`.
    - Thêm từ điển `OBSTACLE_LABELS_VI` và hàm `speakObstacleAlert(level, obstacles)` (cooldown 4 giây, ưu tiên ngắt câu khi chuyển `WARNING` → `CRITICAL`) gọi `window.SmartTTS.speak(...)`.
- **`web_app/views/templates/driver/history_detail.html`** *(Đã cung cấp bản sửa, chờ xác nhận kiểm thử)*
  - **Mục đích:** Sửa lệch cột ORM từ `alert.severity`, `obj.object_class`, `obj.bbox` sang `alert.risk_level`, `obj.object_label`, `obj.bbox_x1..y2`, `obj.confidence`, kèm dịch tên đối tượng sang tiếng Việt.

#### File đã xóa
- Không có file nào bị xóa.

#### Thay đổi CSDL
- Không thay đổi cấu trúc bảng, cột hay quan hệ CSDL.

---

### 3. Công nghệ và kiến trúc
- **Giữ nguyên kiến trúc 2 service tách biệt từ Phiên 1:**
  - **Flask Web App (`http://127.0.0.1:8000`):** Giao diện Jinja2/Bootstrap 5, SQLAlchemy + SQLite, session, controller theo hậu tố `*_controller.py`.
  - **FastAPI AI Service (`http://127.0.0.1:8001`):** WebSocket `/ws/detect`, YOLOv11n + ByteTrack (`ObstacleTracker`), `AlertReporter`, API đồng bộ cấu hình `POST /api/v1/config`.
- **Luồng dữ liệu bổ sung trong phiên:**
  - `ObstacleTracker` tính toán `roi` → `ws_detect.py` gửi kèm trong payload WebSocket → `hud.js` vẽ khung nét đứt theo tỷ lệ `scaleX`, `scaleY`.
  - `hud.js` nhận `warning_level` + `obstacles` → vừa phát còi (`SmartAlertSound`) vừa đọc giọng nói tiếng Việt (`SmartTTS`).

---

### 4. Lỗi đã gặp và cách khắc phục

| # | Nội dung lỗi | Nguyên nhân | Cách khắc phục | Trạng thái |
|---|---|---|---|---|
| 1 | Trang `/driver/history` trên máy tính vẫn không hiện badge đỏ `CRITICAL` | Phiên trước chỉ sửa `item.risk_level` ở phần Card Mobile, sót 1 dòng ở phần Bảng Desktop trong `history.html`. | Cập nhật thêm `item.risk_level` ở phần Bảng Desktop trong `history.html`. | **Đã sửa** |
| 2 | Đã chỉnh ngưỡng `CRITICAL` xuống `0.5s` nhưng vật cản `1.45s` vẫn bị lưu là `CRITICAL` | `config_routes.py` gán vào `tracker.ttc_danger_sec`, nhưng `ObstacleTracker.process_frame()` dùng cứng tham số mặc định `ttc_danger=1.5` và `self.conf`. | Sửa `ObstacleTracker` dùng `self.conf_threshold`, `self.ttc_warning_sec`, `self.ttc_danger_sec` làm ngưỡng mặc định trên RAM. | **Đã sửa** |
| 3 | HUD liên tục báo biển báo giả lập mỗi 6 giây (95%) dù không có biển báo | `sign_detector.py` đang chạy code mock/stub từ giai đoạn dựng khung. | Tạm gán `signs = []` trong `ai_service/api/ws_detect.py` để tập trung test vật cản. | **Đã sửa** |
| 4 | Dán nhầm đoạn gọi `speakObstacleAlert` lồng vào trong khối `if` cũ trong `hud.js` | Lỗi sao chép mã nguồn gây khai báo trùng `const level` và gọi còi 2 lần. | Viết lại khối xử lý sạch 6 dòng trong `ws.onmessage`. | **Đã sửa** |
| 5 | Trang chi tiết `/driver/history/<id>` hiển thị `"Vật cản"` và tọa độ `"--"` | `history_detail.html` dùng sai tên cột ORM (`alert.severity`, `obj.object_class`, `obj.bbox`) thay vì `alert.risk_level`, `obj.object_label`, `bbox_x1..y2`. | Cung cấp bản sửa khớp tên cột ORM + dịch tiếng Việt trong `history_detail.html`. | **Đang kiểm tra** |
| 6 | Xác nhận nút Xóa mềm (Modal) trên `/driver/history` | Chưa có xác nhận kết quả test thực tế từ người dùng trong phiên này. | Đã có route `POST /driver/history/delete` từ phiên trước, cần test xác nhận. | **Đang kiểm tra** |

---

### 5. Những quyết định kỹ thuật đã thống nhất
- **Âm thanh cảnh báo vật cản:** Chọn **Cách 1 (Giọng đọc TTS tiếng Việt qua `window.SmartTTS`)** thay vì nạp file `.mp3`/`.wav` thu sẵn để gọn nhẹ, dễ mở rộng theo nhãn YOLO.
- **Lọc vật cản theo ROI + Ngoại lệ vật thể quá lớn:** Chỉ cảnh báo vật cản có điểm chân nằm trong khung ROI (`x: 15%–85%`, `y: 50%–95%`), **ngoại trừ** bất kỳ vật thể nào chiếm `>= 35%` khung hình hoặc `>= 45%` ROI sẽ luôn bị bắt và ép `CRITICAL`.
- **Tạm tắt biển báo giả lập:** Gán `signs = []` trong `ws_detect.py` cho đến khi hoàn thiện module Quản lý biển báo (UC-06) và tích hợp model nhận diện biển báo thật.
- **Đồng bộ tài liệu Đặc tả (`Log_Dac_Ta_Chuc_Nang.md`):** Chốt API đồng bộ cấu hình UC-05 là `POST /api/v1/config` (thay cho `/api/v1/config/sync`).
- **Điều AI phiên sau KHÔNG được tự ý thay đổi nếu chưa trao đổi:**
  - Không đổi tên cột ORM (`CollisionAlert`, `AlertObject`, `UserSetting`) và cơ chế xóa mềm (`deleted_at`).
  - Không tự ý bật lại `sign_detector.detect(frame)` mock, không tự ý thêm lại `snapshot_saver.py` hoặc camera ngoài khi chưa được yêu cầu.
  - Giữ nguyên kiến trúc 2 service (Flask cổng `8000`, FastAPI cổng `8001`).

---

### 6. Trạng thái hiện tại của dự án
- **Hoàn thành:**
  - Phân hệ Tài xế (phần vật cản): Đăng nhập/Đăng ký (UC-01, UC-02), HUD giám sát trực tiếp với ROI + vật thể quá lớn + còi + TTS vật cản (UC-03), tự động lưu cảnh báo & hiển thị danh sách lịch sử chuẩn giờ UTC+7 + badge đỏ (UC-04), Cài đặt & đồng bộ nóng ngưỡng TTC (UC-05).
  - Cập nhật đặc tả UC-03, UC-04, UC-05.
- **Đang thực hiện / Đang kiểm tra:**
  - Xác nhận hiển thị thực tế của `history_detail.html` (tên đối tượng tiếng Việt + tọa độ BBox) và thao tác **Xóa mềm** trên `/driver/history`.
- **Chưa thực hiện:**
  - **Cụm chức năng Admin:**
    - UC-06: Quản lý danh mục biển báo (`sign_controller.py`, CRUD 3 bảng `traffic_sign_catalog`, `traffic_sign_categories`, `traffic_sign_vehicles`).
    - UC-07: Quản lý & cập nhật Model AI (`model_controller.py`, Local Hot-Reload).
    - UC-08: Quản lý tài khoản người dùng (`user_controller.py`).
  - Tích hợp model nhận diện biển báo thật vào `sign_detector.py` và bật lại trong `ws_detect.py`.
  - Lưu ảnh chụp hiện trường (`snapshot_saver.py`) và kết nối camera ngoài.
- **Đang gặp vấn đề:**
  - Không có lỗi chặn.

---

### 7. Công việc tiếp theo (theo thứ tự ưu tiên)

1. **Xác nhận nhanh 2 điểm cuối của UC-04 (5 phút):**
   - Kiểm tra lại trang `/driver/history/<id>` đã hiện đúng tên đối tượng (kèm %) và tọa độ BBox chưa.
   - Bấm thử nút **Xóa mềm** trong Modal trên `/driver/history`.
   - *File liên quan:* `web_app/views/templates/driver/history_detail.html`, `web_app/controllers/alert_controller.py`.

2. **Triển khai cụm chức năng Admin — Bắt đầu từ UC-06 (Quản lý danh mục biển báo):**
   - **Bước 1:** Kiểm tra schema ORM thực tế của 3 bảng `traffic_sign_categories`, `traffic_sign_catalog`, `traffic_sign_vehicles` trong `web_app/models/` và kiểm tra các template giao diện Admin hiện có.
   - **Bước 2:** Xây dựng CRUD (xem danh sách, thêm, sửa, xóa mềm) trong `web_app/controllers/sign_controller.py` và đăng ký Blueprint vào `web_app/main.py`.
   - **Bước 3:** Kiểm thử CRUD trên giao diện Admin.

3. **Triển khai tiếp UC-08 (Quản lý người dùng) và UC-07 (Quản lý Model AI):**
   - Làm tương tự: kiểm tra model + template trước khi viết `user_controller.py` và `model_controller.py`.

4. **Hoàn thiện các phần nâng cao (sau khi xong Admin):**
   - Tích hợp model nhận diện biển báo thật vào `ai_service` và bật lại `signs = sign_detector.detect(frame)` trong `ws_detect.py`.
   - Bổ sung `snapshot_saver.py` lưu ảnh chụp hiện trường vào `storage/snapshots/`.

---

### 8. Hướng dẫn dành cho AI ở phiên tiếp theo (HANDOFF)

> **Chỉ thị bàn giao cho AI phiên kế tiếp:**
> 1. **Nắm rõ trạng thái:** Phân hệ Tài xế (UC-03 phần vật cản, UC-04, UC-05) đã chạy ổn định. Không viết lại các phần đã xong (`obstacle_tracker.py`, `hud.js`, `setting_controller.py`, `config_routes.py`).
> 2. **Không giả định mục "Đang kiểm tra" đã xong:** Xác nhận nhanh với người dùng xem `history_detail.html` và nút xóa mềm đã chạy ổn chưa trước khi đóng hẳn UC-04.
> 3. **Luôn kiểm tra Model & Template trước khi code Admin:** Trước khi viết bất kỳ controller Admin nào (`sign_controller.py`, `user_controller.py`, `model_controller.py`), bắt buộc phải yêu cầu người dùng gửi file model trong `web_app/models/` và file HTML tương ứng để tránh lỗi lệch tên cột ORM.
> 4. **Tôn trọng các quyết định đã chốt:** Giữ `signs = []` trong `ws_detect.py` và `snapshot_path = None` cho đến khi người dùng yêu cầu làm phần biển báo thật hoặc lưu ảnh chụp. Mọi thao tác xóa đều là **xóa mềm (`deleted_at`)**.
> 5. **Phong cách làm việc:** Chia nhỏ từng bước, cung cấp code rõ ràng theo đúng cấu trúc `*_controller.py`, kèm bước kiểm thử ngắn gọn sau mỗi thay đổi.