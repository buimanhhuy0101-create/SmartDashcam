# HƯỚNG DẪN DÀNH CHO AI (AI INSTRUCTIONS / HANDOFF) — SMARTDASHCAM

* **Phiên bản tài liệu:** 1.2
* **Ngày cập nhật:** 24/11/2026
* **Trạng thái bàn giao:** Giai đoạn kiểm thử tổng thể (Regression Test) và hoàn thiện cuối cùng. Toàn bộ phân hệ Admin (UC-06, UC-07, UC-08, Dashboard) và phân hệ Tài xế (UC-01 đến UC-05, chạy song song `ObstacleTracker` + `SignDetector` `best.pt`, lưu ảnh snapshot, lọc loại xe, phân trang `PAGE_SIZE = 6`) đã được triển khai.
* **Các hạng mục vừa hoàn thiện & kiểm thử ổn định (Phiên 24/11/2026):**
  * **Đổi mật khẩu Tài xế (`/driver/settings`):** Khối form riêng trong `settings.html`, route `POST /driver/settings/change-password` trong `setting_controller.py`, kiểm tra mật khẩu cũ bằng `werkzeug.security`, tự động gọi `session.clear()` và chuyển về `/login` bắt đăng nhập lại sau khi đổi thành công.
  * **Xem lại & Khôi phục dữ liệu đã xóa mềm (`?status=active|deleted`, `POST .../restore`):** Đã hoàn thiện đồng bộ Desktop & Mobile cho 3 phân hệ Admin:
    * Quản lý tài khoản (`/admin/users` — khôi phục cả `User` và `UserSetting`).
    * Danh mục biển báo (`/admin/signs` — khôi phục `TrafficSignCatalog` + `TrafficSignVehicle` và tự động gọi `_sync_sign_cache_to_ai()`).
    * Quản lý mô hình AI (`/admin/models` — khôi phục về trạng thái Chờ kích hoạt, `is_active = False`).
    * *(Đã chốt bỏ qua tính năng xem lại & khôi phục cho Lịch sử cảnh báo `/driver/history`).*
  * **Tối ưu âm thanh & chống lặp biển báo trên HUD (`hud.js`):** Tách kênh âm thanh (Vật cản = Còi, Biển báo = TTS) và áp dụng thời gian hiệu lực + chống lặp khi dừng xe cho từng mã biển báo.

---

## 1. Quy Tắc Bắt Buộc Khi Tiếp Nhận Dự Án

1. **Xác nhận kết quả kiểm thử tổng thể trước khi sửa thêm:**
   * Không giả định các hạng mục kiểm thử cũ chưa xác nhận đã chạy hoàn hảo. Hãy xác nhận với người dùng các điểm còn lại của Regression Test nếu có liên quan:
     * Hiển thị ảnh chụp hiện trường qua `GET /snapshots/<path:filename>` tại `/driver/history` và `/driver/history/<id>`.
     * Bản sửa tràn chữ `#alert-message` và gãy dòng mã biển (`P-103a`) ở cột phải HUD (`hud.html`), cùng dòng bọc chuỗi `window.CURRENT_USER_ID`.
     * Cơ chế nhận diện đúng 1 lần rồi bỏ qua biển khác loại xe (`_seen_irrelevant` trong `sign_detector.py` & `ws_detect.py`).
     * Tự động làm mới RAM Cache 56 biển báo từ UC-06 (`sign_controller.py` → `POST /api/v1/signs/reload-cache`).
     * Phân trang client-side `PAGE_SIZE = 6` trên `history.html` và `signs.html`.
2. **Giữ nguyên kiến trúc 2 service tách biệt:**
   * **Flask Web App (`web_app`, cổng `8000`, venv `web_app\.venv`):** Khởi chạy bằng `python -m web_app.main`. Chịu trách nhiệm toàn bộ thao tác ghi/CRUD SQLite qua SQLAlchemy ORM.
   * **FastAPI AI Service (`ai_service`, cổng `8001`, venv `ai_service\.venv`):** Khởi chạy bằng `uvicorn ai_service.main:app --host 127.0.0.1 --port 8001`. Chỉ đọc (read-only) SQLite để nạp RAM Cache 56 biển báo, tự nạp model `is_active = 1` và cache `user_settings`.
   * Không tự ý gộp 2 service hoặc thay đổi cổng kết nối.
3. **Không viết lại các chức năng đã hoàn thành ổn định:**
   * Toàn bộ phân hệ Admin (UC-06, UC-07 Hot-Reload + SHA-256 + Dummy Inference + Rollback, UC-08, Admin Dashboard, Xem lại & Khôi phục xóa mềm) và luồng Tài xế (Cài đặt + Đổi mật khẩu, HUD tách kênh âm thanh) đã hoạt động ổn định. Chỉ sửa cục bộ khi có lỗi cụ thể hoặc yêu cầu nâng cấp từ người dùng.
4. **Bắt buộc đọc mã nguồn thực tế trước khi đề xuất sửa đổi:**
   * Với các file chưa có trong ngữ cảnh phiên làm việc (ví dụ: `history_detail.html`, `auth_controller.py`, `obstacle_tracker.py`, `alert_controller.py` hoặc các file ORM chưa in đủ danh sách cột), **phải yêu cầu người dùng gửi nội dung file trước khi viết code** để tránh lỗi lệch tên cột ORM hoặc phá vỡ logic đang chạy.

---

## 2. Các Quyết Định Kỹ Thuật KHÔNG Được Tự Ý Thay Đổi

* **Cơ sở dữ liệu & Xóa mềm:**
  * Không thay đổi cấu trúc thư mục, schema CSDL, tên cột ORM (`user_settings`, `collision_alerts`, `alert_objects`, `ai_models`, `traffic_sign_catalog`...) hay cơ chế xóa mềm (`TimestampSoftDeleteMixin`, `active_select`, `deleted_at IS NULL`).
  * Phạm vi chức năng **Xem lại & Khôi phục xóa mềm** chỉ áp dụng cho 3 phân hệ Admin (`users`, `signs`, `models`); **không** bổ sung cho Lịch sử cảnh báo (`/driver/history`).
  * Giữ nguyên định dạng **56 mã biển báo dấu gạch ngang (`-`, ví dụ `P-103a`)** khớp với mô hình `best.pt`.
  * Truyền tường minh `datetime.now()` cho `created_at` / `updated_at` khi tạo bản ghi cảnh báo để giữ đúng giờ địa phương (UTC+7).
* **Bảo mật tài khoản Tài xế (`/driver/settings`):**
  * Giữ tách biệt 2 `<form>` độc lập trong `settings.html`: form cấu hình AI (`POST /driver/settings`) và form đổi mật khẩu (`POST /driver/settings/change-password`).
  * Sau khi đổi mật khẩu thành công, bắt buộc gọi `session.clear()` trước khi `flash(...)` và chuyển hướng về `/login` để yêu cầu đăng nhập lại.
* **Luồng AI, Âm thanh & Xử lý trên HUD (`hud.js`):**
  * Không làm mất khả năng chạy song song của `ObstacleTracker` và `SignDetector` trong `WS /ws/detect`.
  * **Tách kênh âm thanh bắt buộc:** Vật cản (`WARNING`/`CRITICAL`) chỉ phát còi qua `alert_sound.js` (`WARNING`: bíp đơn 1800ms, `CRITICAL`: bíp đôi 700ms), **không** đọc TTS cho vật cản; khi đạt mức `CRITICAL` phải gọi ngay `SmartTTS.stop()` để ngắt giọng đọc biển báo. Biển báo chỉ đọc TTS khi `applies_to_vehicle !== false` và hệ thống không ở mức `CRITICAL`.
  * **Thời gian hiệu lực & chống lặp biển báo (`signStateMap` trong `hud.js`):** Vẫn vẽ khung xanh dương liên tục trên `<canvas>`, nhưng việc đọc TTS và thêm vào cột phải chỉ kích hoạt khi thỏa đồng thời hết cooldown (**10 giây** với biển nguy hiểm `W-`, **25 giây** với các nhóm còn lại) **VÀ** biển đã biến mất khỏi khung hình ít nhất **4 giây** (`SIGN_REAPPEAR_GAP_MS = 4000`). Reset `signStateMap` khi bấm Dừng (`stopHUD`).
  * Giữ nguyên hành vi đối với **biển báo khác loại xe** trong `SignDetector`: nhận diện và hiển thị đúng **1 lần duy nhất** (kèm nhãn `• Khác loại xe`, tắt TTS), sau đó bỏ qua hoàn toàn ở các khung hình tiếp theo (`_seen_irrelevant`) cho tới khi đổi cài đặt, reload cache hoặc mở phiên HUD mới.
* **Ảnh chụp hiện trường (Snapshot):**
  * Giữ nguyên cơ chế lưu ảnh `.jpg` (có vẽ khung vật thể nguy hiểm) vào thư mục dùng chung `storage/snapshots/` (`Config.SNAPSHOTS_DIR` / `AIConfig.SNAPSHOTS_DIR`) và phục vụ qua route riêng `GET /snapshots/<path:filename>` trên Flask; không di chuyển vào `web_app/views/static/`.
* **Giao diện & Phân trang:**
  * Giữ nguyên cơ chế phân trang phía client với `PAGE_SIZE = 6` trên `history.html` và `signs.html` (không tự ý đổi sang SQL `LIMIT/OFFSET`).
* **Quy ước lập trình & Phạm vi tạm hoãn:**
  * Controller Flask đặt tên theo hậu tố `*_controller.py`; render template bên trong khối `with get_db() as db:` để tránh `DetachedInstanceError`.
  * Không tự ý thêm logic kết nối camera ngoài, bộ icon PNG biển báo hay tối ưu bỏ nhịp khung hình (`sign_detector`) khi người dùng chưa yêu cầu.

---

## 3. Danh Sách Kiểm Tra Mở Rộng (Cần Xác Nhận Trước Khi Đóng Gói)

Các điểm nhỏ cần rà soát trước khi đóng gói bảo vệ đồ án gồm:
1. Kiểm tra `web_app/views/templates/driver/history_detail.html` có hiển thị đúng ảnh chụp qua `/snapshots/<filename>` cùng danh sách `alert_objects` hay không.
2. Kiểm tra `web_app/controllers/setting_controller.py` và `hud.html` xem trạng thái ban đầu của 2 nút `TTS` / `Còi` trên HUD đã đồng bộ từ `user_settings` (`tts_enabled`, `alert_sound_enabled`) hay chưa.
3. Kiểm tra `web_app/controllers/auth_controller.py` xem Admin sau khi đăng nhập đã chuyển hướng đúng về `/admin/dashboard` theo UC-01 hay chưa.

---

## 4. Phong Cách Phối Hợp

* Chia nhỏ từng bước, đi tuần tự theo từng file, chờ người dùng kiểm thử/xác nhận rồi mới sang bước tiếp theo.
* Cung cấp mã nguồn rõ ràng theo đúng đường dẫn file thực tế trong dự án, kèm hướng dẫn hoặc lệnh kiểm thử ngắn gọn sau mỗi thay đổi.