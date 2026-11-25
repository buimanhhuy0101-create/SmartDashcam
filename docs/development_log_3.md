# DEVELOPMENT LOG – DỰ ÁN SMARTDASHCAM

---

## Phiên làm việc: 24/11/2026 (Đợt 2 – Hoàn thiện luồng HUD, Snapshot, Lọc loại xe & Phân trang)

### 1. Thông tin công việc hôm nay
- **Ngày thực hiện:** 24/11/2026 (buổi sáng).
- **Các mục tiêu đã đặt ra:**
  1. Triển khai trọn gói 3 hạng mục cuối theo đặc tả `Nhom_05.docx`:
     - Chụp và lưu ảnh hiện trường (`snapshot`) khi phát hiện cảnh báo va chạm (`WARNING` / `CRITICAL`), kèm vượt cooldown 5 giây khi nâng mức `WARNING -> CRITICAL`.
     - Lọc cảnh báo biển báo theo loại phương tiện của tài xế (`user_settings.vehicle_type`) và đồng bộ `conf_threshold` sang `SignDetector`.
     - Tự động làm mới RAM Cache biển báo trên FastAPI khi Admin thêm/sửa/xóa mềm biển báo ở UC-06.
  2. Khắc phục các lỗi hiển thị thực tế phát sinh khi kiểm thử: ảnh chụp bị vỡ trên trang Lịch sử cảnh báo, vỡ bố cục cột phải trên HUD và lỗi linter ở dòng gán `window.CURRENT_USER_ID`.
  3. Bổ sung hành vi nhận diện biển báo khác loại xe đúng 1 lần duy nhất rồi bỏ qua các khung hình sau.
  4. Bổ sung phân trang phía trình duyệt (6 dòng/trang) cho trang Lịch sử cảnh báo (`/driver/history`) và Danh mục biển báo Admin (`/admin/signs`).
- **Những nội dung đã thực hiện:**
  - Cập nhật `AlertReporter` vẽ khung vật thể nguy hiểm lên bản sao khung hình và lưu ảnh `.jpg` vào `storage/snapshots/` trên luồng nền; truyền `frame=frame` từ `ws_detect.py`.
  - Thêm route phục vụ ảnh tĩnh `GET /snapshots/<path:filename>` và hàm chuẩn hóa URL `/snapshots/<filename>` trong `alert_controller.py` (đồng thời xóa decorator route bị lặp).
  - Nâng cấp `SignDetector` đọc và cache `user_settings` (`vehicle_type`, `conf_threshold`), chuẩn hóa `motorcycle -> motorbike`, gắn cờ `applies_to_vehicle`, và bổ sung cơ chế `_seen_irrelevant` + `reset_session(user_id)` để biển khác loại xe chỉ hiển thị 1 lần duy nhất rồi bỏ qua.
  - Cập nhật `config_routes.py` đồng bộ `conf_threshold` + xóa cache `user_settings` của `SignDetector` trong `POST /api/v1/config`, bổ sung endpoint `POST /api/v1/signs/reload-cache`, và nối lệnh gọi từ `sign_controller.py`.
  - Cập nhật `hud.js` để hiển thị nhãn `Khác loại xe` và không đọc TTS nếu `applies_to_vehicle === false`.
  - Cập nhật toàn bộ `hud.html` sửa tràn chữ `#alert-message` (bổ sung `.min-w-0`, bỏ `text-truncate`) và mở rộng ô `.hud-sign-icon` (`3.75rem`, `white-space: nowrap`), hướng dẫn bọc chuỗi cho `window.CURRENT_USER_ID`.
  - Cập nhật toàn bộ `history.html` và `signs.html` bổ sung phân trang 6 dòng/trang đồng bộ giữa bảng Desktop, Card Mobile và bộ lọc/tìm kiếm hiện có.
- **Kết quả đạt được:**
  - **Đã có bằng chứng xác nhận (qua ảnh chụp màn hình):**
    - `AlertReporter` đã chụp ảnh và lưu `snapshot_path` thành công vào SQLite (ảnh `image_7a38ff.jpg`: sự kiện `24/11/2026 09:09:53` có dữ liệu ảnh thay vì *"Không có ảnh"*).
    - HUD chạy song song thành công cả cảnh báo va chạm (`TTC: 1.5s`, mức `Nguy hiểm`) và nhận diện biển báo thật (`P-103a – Cấm xe ô tô`, `87%`) (ảnh `image_7a47c3.png`).
  - **Đã cung cấp mã nguồn, đang chờ người dùng xác nhận kết quả kiểm thử:**
    - Hiển thị ảnh snapshot qua `/snapshots/<filename>` (`alert_controller.py`).
    - Bản sửa vỡ bố cục cột phải HUD (`hud.html`) và bọc chuỗi `window.CURRENT_USER_ID`.
    - Cơ chế chỉ nhận diện 1 lần rồi bỏ qua biển khác loại xe (`sign_detector.py`, `ws_detect.py`).
    - Làm mới RAM Cache tự động từ UC-06 (`sign_controller.py`, `config_routes.py`).
    - Phân trang 6 dòng/trang (`history.html`, `signs.html`) và hàng đợi ưu tiên TTS từ phiên trước (`tts.js`, `hud.js`).

---

### 2. Những thay đổi trong dự án

#### File đã tạo mới
- Không có file nào tạo mới trong đợt này.

#### File đã chỉnh sửa
| Đường dẫn | Mục đích thay đổi |
|---|---|
| `ai_service/services/alert_reporter.py` | Bổ sung vượt cooldown 5 giây khi chuyển `WARNING -> CRITICAL`, vẽ khung bao + nhãn vật thể nguy hiểm lên bản sao khung hình và lưu ảnh `.jpg` vào `AIConfig.SNAPSHOTS_DIR` (`storage/snapshots/`) trong luồng nền `_save_and_send`. |
| `ai_service/core/sign_detector.py` | Đọc và cache `vehicle_type`, `conf_threshold` từ `user_settings` theo `user_id`; chuẩn hóa `motorcycle -> motorbike`; thêm `clear_user_cache()` và `reset_session(user_id)`; trả thêm cờ `applies_to_vehicle`; bổ sung `_seen_irrelevant` để biển khác loại xe chỉ báo 1 lần duy nhất rồi bỏ qua hoàn toàn (không vẽ bbox, không lặp sự kiện) cho tới khi đổi cài đặt, reload cache hoặc mở phiên HUD mới. |
| `ai_service/api/config_routes.py` | Cập nhật `POST /api/v1/config` đồng bộ `conf_threshold` và gọi `sign_detector.clear_user_cache()`; bổ sung endpoint `POST /api/v1/signs/reload-cache` gọi `sign_detector.reload_catalog_cache()`. |
| `ai_service/api/ws_detect.py` | Gọi `sign_detector.reset_session(user_id)` khi kết nối WebSocket; truyền `user_id=user_id` vào `sign_detector.detect(...)`; truyền `frame=frame` vào `alert_reporter.report_async(...)`. |
| `web_app/controllers/sign_controller.py` | Bổ sung hàm `_sync_sign_cache_to_ai()` gọi `POST /api/v1/signs/reload-cache` sang FastAPI (bắt lỗi an toàn nếu AI Service tắt); thêm `db.commit()` và `_sync_sign_cache_to_ai()` trong `admin_sign_create`, `admin_sign_edit`, `admin_sign_delete`. |
| `web_app/controllers/alert_controller.py` | Bổ sung route `GET /snapshots/<path:filename>` dùng `send_from_directory(str(Config.SNAPSHOTS_DIR), filename)` (kiểm tra đăng nhập qua session); thêm `_normalize_snapshot_url` chuẩn hóa đường dẫn thành `/snapshots/<filename>` khi lưu mới và khi đọc danh sách/chi tiết (tương thích cả bản ghi cũ); xóa 1 dòng decorator `@alert_bp.route("/api/internal/alerts", methods=["POST"])` bị trùng. |
| `web_app/views/static/js/hud.js` | Cập nhật `addSignToList` hiển thị thêm `• Khác loại xe` khi `sign.applies_to_vehicle === false`; chỉ gọi `SmartTTS.speak(...)` cho biển báo khi `sign.applies_to_vehicle !== false`. |
| `web_app/views/templates/driver/hud.html` | Bổ sung CSS `.min-w-0 { min-width: 0; }`, cho phép `#alert-message` tự xuống dòng (`white-space: normal; overflow-wrap: break-word`) và bỏ class `text-truncate`; mở rộng `.hud-sign-icon` thành `3.75rem` kèm `white-space: nowrap` để mã biển 5–6 ký tự (`P-103a`) không bị gãy dòng; hướng dẫn sửa `window.CURRENT_USER_ID = "{{ session.get('user_id') or '' }}";` tránh báo lỗi cú pháp JS trên editor. |
| `web_app/views/templates/driver/history.html` | Bổ sung phân trang phía client (`PAGE_SIZE = 6`) đồng bộ giữa bảng Desktop và Card Mobile, tự tính lại trang khi bấm nút lọc (`Tất cả` / `Nguy hiểm` / `Cảnh báo`), hiển thị thông tin trang (`Hiển thị X–Y / Z sự kiện`) và thông báo khi bộ lọc không có kết quả. |
| `web_app/views/templates/admin/signs.html` | Bổ sung phân trang phía client (`PAGE_SIZE = 6`) đồng bộ giữa bảng Desktop và Card Mobile, tự tính lại trang và quay về trang 1 khi nhập tìm kiếm hoặc đổi dropdown lọc nhóm biển báo. |

#### File đã xóa
- Không có file nào bị xóa.

#### Thay đổi về Cơ sở dữ liệu (Schema / Dữ liệu)
- **Schema bảng / cột / quan hệ:** Không thay đổi (đối chiếu đúng các cột có sẵn trong `web_app/models/user_setting.py`: `vehicle_type`, `tts_enabled`, `alert_sound_enabled`, `conf_threshold`, `ttc_warning_sec`, `ttc_danger_sec`).
- **Dữ liệu:** Phát sinh thêm các bản ghi `collision_alerts` mới có lưu `snapshot_path` kèm tệp ảnh `.jpg` trong `storage/snapshots/`.

#### Thay đổi về giao diện & xử lý nghiệp vụ
- **Nghiệp vụ cảnh báo va chạm:** Hỗ trợ vượt cooldown 5s khi mức độ tăng từ `WARNING` lên `CRITICAL`; tự động vẽ khung vật thể nguy hiểm lên ảnh chụp hiện trường và phục vụ ảnh qua `/snapshots/<filename>`.
- **Nghiệp vụ lọc loại xe:** Biển báo không áp dụng cho loại xe của tài xế vẫn báo nhận diện 1 lần duy nhất ở cột phải (kèm nhãn `Khác loại xe`, tắt TTS), sau đó bỏ qua hoàn toàn để tránh nhiễu.
- **Giao diện:** Chống tràn chữ ở hộp cảnh báo đỏ và chống gãy dòng mã biển trên HUD; rút gọn danh sách dài ở `/driver/history` và `/admin/signs` thành từng trang 6 dòng.

---

### 3. Công nghệ và kiến trúc
- **Công nghệ, framework & thư viện:** Giữ nguyên như Đợt 1 (Flask + SQLAlchemy + SQLite + Bootstrap 5; FastAPI + Uvicorn + Ultralytics YOLOv11 + ByteTrack + OpenCV + NumPy; Vanilla JS + WebSocket + Web Speech API).
- **Kiến trúc & luồng giao tiếp bổ sung trong đợt này:**
  - Trình duyệt (Lịch sử cảnh báo) -> Flask `GET /snapshots/<path:filename>` -> đọc ảnh từ thư mục dùng chung `storage/snapshots/` (`Config.SNAPSHOTS_DIR`).
  - Flask UC-06 (`sign_controller.py`) -> FastAPI `POST /api/v1/signs/reload-cache` -> nạp lại 56 biển báo từ SQLite lên RAM Cache của `SignDetector`.
  - Flask UC-05 (`POST /api/v1/config`) -> FastAPI cập nhật `conf_threshold` cho cả `ObstacleTracker` lẫn `SignDetector` và xóa cache `user_settings` + `_seen_irrelevant` trên RAM.
- **Quy ước lập trình đã thống nhất:**
  - Giữ nguyên schema ORM, không sửa tên cột DB, dùng xóa mềm (`TimestampSoftDeleteMixin`, `active_select`).
  - Phân trang tại `history.html` và `signs.html` thực hiện phía client với hằng số `PAGE_SIZE = 6` để không phá vỡ tìm kiếm/lọc nhanh tức thì và không cần thay đổi controller Python.

---

### 4. Lỗi đã gặp và cách khắc phục

| # | Nội dung lỗi | Nguyên nhân | Cách khắc phục | Trạng thái |
|---|---|---|---|---|
| 1 | Ảnh snapshot ở `/driver/history` hiện biểu tượng ảnh vỡ (`image_7a38ff.jpg`). | `AlertReporter` lưu tên file trần (`alert_u...jpg`), trong khi `history.html` gán trực tiếp vào `<img src="{{ img_src }}">` và Flask chưa có route phục vụ thư mục `storage/snapshots/`. | Thêm route `GET /snapshots/<path:filename>` (`send_from_directory`) và hàm `_normalize_snapshot_url` trong `web_app/controllers/alert_controller.py`. | **Đang kiểm tra** (đã giao code, chưa nhận phản hồi ảnh đã hiển thị). |
| 2 | Dòng cảnh báo `#alert-message` tràn ra ngoài khung đỏ và mã biển `P-103a` bị gãy dòng chật khung trên HUD (`image_7a47c3.png`). | Bootstrap 5 không có sẵn `.min-w-0` kết hợp class `text-truncate` làm flex item không co; `.hud-sign-icon` chỉ rộng `2.35rem`. | Định nghĩa `.min-w-0`, bỏ `text-truncate`, bật `overflow-wrap: break-word` cho `#alert-message` và mở rộng `.hud-sign-icon` lên `3.75rem` + `white-space: nowrap` trong `hud.html`. | **Đang kiểm tra** (đã giao toàn bộ file `hud.html`, chưa xác nhận kết quả hiển thị). |
| 3 | Dòng `window.CURRENT_USER_ID = {{ session.get('user_id') \| tojson }};` trong `hud.html` bị báo lỗi trên trình soạn thảo. | Linter JS trong editor không hiểu cú pháp Jinja `{{ ... }}` đứng trần không bọc chuỗi trong thẻ `<script>`. | Đổi sang bọc chuỗi `"{{ session.get('user_id') or '' }}"` (tương thích với `hud.js`). | **Đang kiểm tra** (chưa xác nhận người dùng đã hết lỗi hay là lỗi runtime). |
| 4 | Biển báo không áp dụng cho loại xe đang chọn vẫn tiếp tục vẽ khung và lặp nhận diện trên HUD. | Phiên bản đầu chỉ tắt TTS khi `applies_to_vehicle === false`, chưa lọc bỏ ở các khung hình kế tiếp trong `SignDetector`. | Thêm tập `_seen_irrelevant` trong `SignDetector` và gọi `reset_session(user_id)` trong `ws_detect.py` để chỉ ghi nhận đúng 1 lần rồi bỏ qua hoàn toàn. | **Đang kiểm tra** (đã giao code 2 file, chưa xác nhận test thực tế). |
| 5 | Xung đột âm thanh TTS giữa cảnh báo vật cản và biển báo (từ Đợt 1). | `tts.js` cũ gọi `speechSynthesis.cancel()` mỗi lần đọc. | Đã viết lại hàng đợi 3 mức ưu tiên trong `tts.js` + `hud.js`. | **Đang kiểm tra** (chưa nhận xác nhận rõ từ người dùng sau khi sửa). |
| 6 | Danh sách lịch sử cảnh báo (54+ dòng) và danh mục 56 biển báo quá dài phải cuộn nhiều. | Chưa có cơ chế phân trang trên `history.html` và `signs.html`. | Bổ sung phân trang client-side `PAGE_SIZE = 6` vào `history.html` và `signs.html`. | **Đang kiểm tra** (vừa bàn giao code, chưa xác nhận kết quả test). |

---

### 5. Những quyết định kỹ thuật đã thống nhất
- **Phương án đã lựa chọn:**
  - **Lưu & phục vụ ảnh Snapshot:** Lưu file `.jpg` (có vẽ khung vật thể nguy hiểm) vào `storage/snapshots/` ở luồng nền của `AlertReporter`; phục vụ qua route riêng `GET /snapshots/<path:filename>` trên Flask thay vì di chuyển thư mục lưu trữ vào `web_app/views/static/`.
  - **Hành vi với biển báo khác loại xe:** Nhận diện và đẩy vào danh sách cột phải đúng **1 lần duy nhất** (kèm nhãn `Khác loại xe`, không đọc TTS), sau đó bỏ qua hoàn toàn ở các khung hình tiếp theo (không vẽ bbox, không lặp lại) cho tới khi đổi loại xe/reload cache/bắt đầu phiên HUD mới. *Phương án loại bỏ:* Bỏ qua ngay từ lần đầu (người dùng muốn biết có biển báo đó 1 lần) hoặc tiếp tục vẽ khung liên tục.
  - **Phân trang danh sách:** Chọn phân trang phía client `PAGE_SIZE = 6` trên `history.html` và `signs.html`. *Phương án loại bỏ:* Phân trang phía server (SQL `LIMIT/OFFSET`) vì sẽ làm mất khả năng tìm kiếm/lọc tức thì hiện có trên trang mà chưa cần thiết với quy mô ~56–100 bản ghi.
- **Những điều AI phiên sau KHÔNG được tự ý thay đổi nếu chưa trao đổi:**
  - Không đổi lại hành vi "nhận diện 1 lần rồi bỏ qua" đối với biển khác loại xe trong `SignDetector`.
  - Không bỏ route `GET /snapshots/<path:filename>` hoặc di chuyển `storage/snapshots/` ra khỏi `Config.SNAPSHOTS_DIR`.
  - Không đổi schema DB, tên cột ORM (`user_settings`, `collision_alerts`, `ai_models`, `traffic_sign_catalog`), mã biển dấu gạch ngang (`-`) hay cơ chế xóa mềm.
  - Không làm mất khả năng chạy song song của `ObstacleTracker` và `SignDetector` trong `/ws/detect`.

---

### 6. Trạng thái hiện tại của dự án
- **Hoàn thành (đã xác nhận):**
  - Toàn bộ phân hệ Admin: UC-06 (56 biển báo), UC-07 (Upload & Hot-Reload + SHA-256 + Dummy Inference + Rollback), UC-08 (Quản lý tài khoản), Admin Dashboard nối CSDL thật & ping FastAPI.
  - Phân hệ Tài xế cốt lõi: UC-01, UC-02, UC-04, UC-05, HUD chạy song song `ObstacleTracker` (ByteTrack + ROI + TTC) và `SignDetector` (`best.pt` 56 lớp + RAM Cache), chụp ảnh snapshot vào DB & ổ cứng.
- **Đang thực hiện / Đang chờ kiểm thử xác nhận:**
  - Kiểm thử toàn bộ các bản vá đợt 2: hiển thị ảnh `/snapshots/<filename>` tại `/driver/history` và `/driver/history/<id>`, hàng đợi ưu tiên TTS (`tts.js`), giao diện cột phải HUD (`hud.html`), nhận diện 1 lần rồi bỏ qua biển khác loại xe (`sign_detector.py`), đồng bộ RAM Cache từ UC-06 (`sign_controller.py`), và phân trang 6 dòng/trang (`history.html`, `signs.html`).
- **Chưa thực hiện (tùy chọn mở rộng / kiểm tra thêm nếu cần):**
  - Kiểm tra hiển thị ảnh snapshot trên trang chi tiết `web_app/views/templates/driver/history_detail.html` (chưa đọc file này trong cuộc trò chuyện).
  - Kiểm tra đồng bộ cài đặt âm thanh (`tts_enabled`, `alert_sound_enabled`) từ `user_settings` xuống trạng thái ban đầu của 2 nút `TTS` / `Còi` trên `hud.html` (hiện chưa xác định đã nối hay chưa).
  - Kiểm tra lại `web_app/controllers/auth_controller.py` xem Admin đăng nhập đã đổi redirect từ `/admin/signs` sang `/admin/dashboard` theo UC-01 hay chưa (Chưa xác định).
  - Bổ sung bộ ảnh icon PNG thật cho 56 biển báo vào `web_app/views/static/sign_icons/` (nếu cần cho demo).
  - Tối ưu FPS (chạy `sign_detector` cách nhịp 2–3 frame/lần) nếu chạy trên máy CPU bị giật.
- **Đang gặp vấn đề:**
  - Chưa có lỗi chặn mới, nhưng toàn bộ 6 hạng mục sửa ở bảng mục 4 đều ở trạng thái **Đang kiểm tra** (cần người dùng chạy test thực tế để chốt).

---

### 7. Công việc tiếp theo (theo thứ tự ưu tiên)
1. **Chạy vòng kiểm thử tổng thể (Regression Test) toàn bộ đợt 2 (Ưu tiên 1 – làm ngay):**
   - **Bước thực hiện:** Khởi động lại cả 2 server (`python -m web_app.main` và `uvicorn ai_service.main:app --host 127.0.0.1 --port 8001`), bấm `Ctrl + F5` và kiểm tra lần lượt:
     1. `/driver/history` và `/driver/history/<id>`: Ảnh snapshot hiển thị rõ, Modal phóng to hoạt động, phân trang 6 dòng/trang và nút lọc chạy đúng.
     2. `/admin/signs`: Phân trang 6 dòng/trang + tìm kiếm + lọc nhóm chạy đúng; sửa thử kịch bản TTS của 1 biển và xem log FastAPI có tự nạp lại 56 biển vào RAM Cache không.
     3. `/driver/hud`: Không tràn chữ khung cảnh báo, mã `P-103a` gọn 1 dòng, `window.CURRENT_USER_ID` không báo lỗi Console, loa TTS đọc mượt cả biển báo và vật cản theo thứ tự ưu tiên, biển khác loại xe chỉ báo 1 lần rồi bỏ qua.
   - **File liên quan:** `alert_controller.py`, `hud.html`, `hud.js`, `tts.js`, `history.html`, `signs.html`, `sign_detector.py`, `ws_detect.py`, `sign_controller.py`, `config_routes.py`.
2. **Kiểm tra các điểm đồng bộ nhỏ còn lại trước khi đóng gói bảo vệ (Ưu tiên 2):**
   - Đọc `web_app/views/templates/driver/history_detail.html` để chắc chắn hiển thị ảnh chụp hiện trường + danh sách `alert_objects` khớp với `/snapshots/<filename>`.
   - Đọc `web_app/controllers/setting_controller.py` (hoặc controller xử lý UC-05) để chắc chắn khi lưu cài đặt có gọi `POST /api/v1/config` đúng chuẩn và truyền cấu hình ban đầu lên HUD nếu cần.
   - Kiểm tra redirect sau đăng nhập của Admin trong `web_app/controllers/auth_controller.py`.
3. **Tối ưu & chuẩn bị dữ liệu demo (Ưu tiên 3):**
   - Kiểm tra FPS thực tế trên video mẫu `.mp4`; nếu thấp mới tối ưu cách nhịp `sign_detector`.
   - Bổ sung icon PNG cho 56 biển báo (nếu người dùng yêu cầu).
- **Vấn đề cần kiểm tra trước khi triển khai:** Luôn yêu cầu người dùng cung cấp nội dung file chưa đọc (`history_detail.html`, `setting_controller.py`, `obstacle_tracker.py`) trước khi đề xuất sửa đổi.

---

### 8. Hướng dẫn dành cho AI ở phiên tiếp theo (HANDOFF)
Bạn đang tiếp nhận dự án **SmartDashcam** (Flask Web App cổng `8000` + FastAPI AI Service cổng `8001`, SQLite + SQLAlchemy ORM, YOLOv11n + ByteTrack) ở giai đoạn kiểm thử tổng thể và hoàn thiện cuối cùng.

**Nguyên tắc bắt buộc khi tiếp tục:**
1. **Hỏi kết quả kiểm thử trước khi sửa thêm:** 6 hạng mục vừa bàn giao trong Đợt 2 (ảnh snapshot `/snapshots/<filename>`, UI cột phải HUD, dòng `window.CURRENT_USER_ID`, lọc biển khác loại xe 1 lần duy nhất, hàng đợi ưu tiên TTS, và phân trang 6 dòng/trang ở `history.html` & `signs.html`) đều đang ở trạng thái **Đang kiểm tra**. Không giả định chúng đã chạy hoàn hảo; hãy xác nhận kết quả test thực tế với người dùng đầu tiên.
2. **Giữ nguyên các quyết định kiến trúc đã thống nhất:**
   - Không đổi cấu trúc thư mục, schema CSDL, tên cột ORM hay cơ chế xóa mềm (`TimestampSoftDeleteMixin`, `active_select`).
   - Giữ nguyên 56 mã biển báo dấu gạch ngang (`-`) khớp `best.pt`.
   - Giữ nguyên chạy song song `ObstacleTracker` + `SignDetector` trong `/ws/detect`.
   - Giữ nguyên cơ chế nhận diện đúng 1 lần rồi bỏ qua cho biển khác loại xe (`_seen_irrelevant`), phục vụ ảnh qua `GET /snapshots/<path:filename>`, và phân trang client-side `PAGE_SIZE = 6`.
3. **Không viết lại chức năng đã hoàn thành:** Phân hệ Admin (UC-06, UC-07, UC-08, Dashboard) và luồng AI nền đã ổn định; chỉ sửa cục bộ khi có lỗi cụ thể.
4. **Kiểm tra mã nguồn trước khi kết luận:** Với các file chưa có trong ngữ cảnh (như `history_detail.html`, `setting_controller.py`, `obstacle_tracker.py`), bắt buộc yêu cầu người dùng gửi file trước khi viết code.

---

## Phiên làm việc: 23/11/2026 – 24/11/2026 (Đợt 1 – Hoàn thiện Admin & Tích hợp Model Biển báo lên HUD)

### 1. Thông tin công việc
- **Ngày thực hiện:** 23/11/2026 – 24/11/2026.
- **Mục tiêu đặt ra:**
  1. Đồng bộ và nạp đủ 56 lớp biển báo giao thông từ mô hình `best.pt` đã huấn luyện vào SQLite (hoàn thiện dữ liệu nền UC-06).
  2. Xây dựng hoàn chỉnh **UC-07 (Quản lý & cập nhật Model AI – Local Hot-Reload)** trên cả Flask Web App và FastAPI AI Service theo đặc tả trong `Nhom_05.docx`.
  3. Xây dựng hoàn chỉnh **UC-08 (Quản lý tài khoản người dùng)** và kết nối dữ liệu thật từ SQLite + trạng thái AI Service cho trang **Admin Dashboard** (`/admin/dashboard`).
  4. Tích hợp mô hình nhận diện biển báo thật (`best.pt`) vào luồng Tài xế (UC-03 – HUD) chạy song song với nhận diện vật cản, kèm xử lý xung đột giọng đọc TTS.
- **Những nội dung đã thực hiện:**
  - Trích xuất 56 lớp nhãn (`0` đến `55`) từ `best.pt` và cập nhật `web_app/database/seed.py` để nạp vào SQLite, đồng thời xóa mềm 4 biển báo mẫu cũ dùng dấu chấm.
  - Hoàn thiện toàn bộ phân hệ Admin: UC-07 (`model_controller.py`, `models.html`, `checksum.py`, `model_manager.py`, `model_routes.py`), UC-08 (`user_controller.py`) và Dashboard (`/admin/dashboard` trong `web_app/main.py`).
  - Nâng cấp `SignDetector` chạy model YOLOv11 thật + nạp RAM Cache 56 biển báo từ SQLite + tự nạp bản `is_active = 1` khi khởi động FastAPI; nối Hot-Reload từ `ModelManager` sang `SignDetector`.
  - Bật nhận diện biển báo song song với vật cản trong WebSocket `/ws/detect` và vẽ khung biển báo màu xanh dương lên Canvas trên HUD (`hud.js`).
  - Đề xuất và viết bản sửa lỗi xung đột âm thanh TTS giữa cảnh báo vật cản và biển báo bằng hàng đợi 3 mức ưu tiên (`tts.js` và `hud.js`).
- **Kết quả đạt được:**
  - **Đã xác nhận hoạt động:** Toàn bộ phân hệ Admin (nạp 56 biển báo UC-06, tải lên/kích hoạt model UC-07, quản lý tài khoản UC-08, Admin Dashboard); model biển báo trên HUD Tài xế đã nhận diện được biển báo chạy song song với vật cản.
  - **Chuyển tiếp kiểm tra sang Đợt 2:** Bản sửa hàng đợi ưu tiên TTS (`tts.js` + `hud.js`).

### 2. Những thay đổi chính ở Đợt 1
- **Tạo mới:** `web_app/controllers/model_controller.py`, `ai_service/utils/checksum.py`, `ai_service/core/model_manager.py`, `ai_service/api/model_routes.py`, `web_app/controllers/user_controller.py`.
- **Chỉnh sửa:** `web_app/database/seed.py`, `web_app/views/templates/admin/models.html`, `web_app/main.py`, `ai_service/main.py`, `ai_service/core/sign_detector.py`, `ai_service/api/ws_detect.py`, `web_app/views/static/js/hud.js`, `web_app/views/static/js/tts.js`.
- **Lệnh vận hành hệ thống:**
  - Flask Web App (`http://127.0.0.1:8000`): `python -m web_app.main`
  - FastAPI AI Service (`http://127.0.0.1:8001`): `uvicorn ai_service.main:app --host 127.0.0.1 --port 8001`