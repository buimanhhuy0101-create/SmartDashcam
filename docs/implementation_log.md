# NHẬT KÝ CÔNG VIỆC & TIẾN ĐỘ (IMPLEMENTATION LOG) — SMARTDASHCAM

* **Phiên bản tài liệu:** 1.2
* **Ngày cập nhật:** 24/11/2026

---

## 1. Tiến Độ Theo Mốc Thời Gian

| Ngày | Nội dung chính đã hoàn thành | Trạng thái |
| :--- | :--- | :--- |
| **19/11/2026** | Phân tích & Thiết kế hệ thống (kiến trúc MVC–FastAPI, lược đồ 8 bảng SQLite + SQLAlchemy, sơ đồ ERD & Use Case). | Hoàn thành |
| **20/11/2026** | Hoàn thiện đặc tả 8 Use Case; dựng cây thư mục dự án, tạo 2 môi trường ảo (`web_app\.venv`, `ai_service\.venv`), cài thư viện, tạo `.env.example`, `.gitignore`, `README.md`. | Hoàn thành |
| **21/11/2026** | Hoàn thiện 8 bảng ORM SQLAlchemy, `TimestampSoftDeleteMixin`, `seed.py`, `init_db.py`; hoàn thành UC-01/UC-02; hoàn thiện 100% UI/UX Responsive cho toàn bộ phân hệ Tài xế & Quản trị viên. | Hoàn thành |
| **22/11/2026 (Phiên 1)** | Xây dựng `AlertReporter`, nối `user_id` qua WebSocket, tạo `POST /api/internal/alerts`, xây dựng `alert_controller.py` (UC-04), `setting_controller.py` (UC-05) và `POST /api/v1/config`. | Hoàn thành |
| **22/11/2026 (Phiên 2)** | Sửa đồng bộ ngưỡng TTC trên RAM của `ObstacleTracker`; thêm bộ lọc ROI + vẽ khung ROI lên HUD + ngoại lệ vật thể quá lớn; tích hợp TTS tiếng Việt cho vật cản; vá lỗi hiển thị `history.html` & `history_detail.html`. | Hoàn thành |
| **23–24/11/2026 (Đợt 1)** | Trích xuất & nạp đủ **56 lớp biển báo** (`best.pt`, mã dấu `-`) vào SQLite (xóa mềm 4 biển mẫu cũ); hoàn thiện toàn bộ phân hệ Admin: **UC-07** (`model_controller.py`, `models.html`, `checksum.py`, `model_manager.py`, `model_routes.py`), **UC-08** (`user_controller.py`) và **Admin Dashboard** nối CSDL thật + ping AI; tích hợp `SignDetector` chạy `best.pt` thật song song `ObstacleTracker` trong `/ws/detect` + vẽ khung xanh dương trên HUD; viết lại `tts.js` + `hud.js` dùng hàng đợi TTS 3 mức ưu tiên. | Hoàn thành |
| **24/11/2026 (Đợt 2)** | Bổ sung chụp & lưu ảnh hiện trường (`AlertReporter` vẽ khung + lưu `.jpg` vào `storage/snapshots/`, vượt cooldown 5s `WARNING -> CRITICAL`), thêm route `GET /snapshots/<path:filename>` & chuẩn hóa URL trong `alert_controller.py`; nâng cấp `SignDetector` lọc loại xe (`vehicle_type`, chuẩn hóa `motorcycle -> motorbike`, `_seen_irrelevant` chỉ báo 1 lần rồi bỏ qua, `reset_session`); đồng bộ `conf_threshold` & xóa cache trong `POST /api/v1/config`; thêm `POST /api/v1/signs/reload-cache` và nối từ `sign_controller.py`; sửa tràn chữ/gãy dòng cột phải HUD (`hud.html`) và bọc chuỗi `window.CURRENT_USER_ID`; bổ sung phân trang client-side `PAGE_SIZE = 6` cho `history.html` và `signs.html`. | Đã bàn giao mã nguồn *(các hạng mục Đợt 2 chờ xác nhận Regression Test)* |
| **24/11/2026 (Đợt 3)** | Bổ sung **UC-09 (Đổi mật khẩu Tài xế)** trong `/driver/settings` (`setting_controller.py`, `settings.html` — form riêng, ẩn/hiện mật khẩu, kiểm tra mật khẩu cũ bằng `werkzeug.security`, tự động `session.clear()` bắt đăng nhập lại); bổ sung **Xem lại & Khôi phục dữ liệu đã xóa mềm** (`?status=active\|deleted`, `POST .../restore`) đồng bộ Desktop/Mobile cho 3 phân hệ Admin: Tài khoản (`user_controller.py`, `users.html` — khôi phục cả `User` & `UserSetting`), Biển báo (`sign_controller.py`, `signs.html` — khôi phục cả `TrafficSignVehicle` + tự đồng bộ AI Cache) và Mô hình AI (`model_controller.py`, `models.html` — khôi phục về `is_active = False`); chốt bỏ qua khôi phục cho Lịch sử cảnh báo (`/driver/history`); tối ưu HUD (`hud.js`) tách kênh âm thanh (Vật cản = Còi, `CRITICAL` ngắt TTS; Biển báo = TTS) và thêm cooldown hiệu lực biển báo (`W-` 10s, nhóm khác 25s) kết hợp chống lặp dừng xe (4s). | **Hoàn thành (Đã kiểm thử)** |

---

## 2. Danh Sách Lỗi Đã Khắc Phục & Đang Kiểm Tra

| # | Lỗi / Vấn đề | Nguyên nhân | Cách khắc phục | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `WinError 10013` không mở được cổng `5000` | Windows (Hyper-V/WSL) chặn cổng `5000`. | Đổi `WEB_PORT` sang `8080` rồi chốt chạy ổn định trên `8000`. | **Đã sửa** |
| 2 | `500 Internal Server Error`: `'severity' is an invalid keyword argument for CollisionAlert` | Lệch tên cột ORM so với thiết kế cũ. | Đổi sang đúng cột thực tế (`risk_level`, `object_label`, `bbox_x1..y2`, `confidence`, `message`). | **Đã sửa** |
| 3 | `POST /api/v1/config 404 Not Found` | Trùng `prefix="/api/v1"` giữa `main.py` và `config_routes.py`. | Chỉ khai báo `prefix="/api/v1"` tại 1 nơi duy nhất. | **Đã sửa** |
| 4 | Không ghi nhận `CRITICAL` / chỉnh `ttc_danger_sec` không ăn | Cooldown 5s chặn chuyển mức; `ObstacleTracker` dùng tham số cứng thay vì thuộc tính trên RAM. | Cho `CRITICAL` vượt cooldown `WARNING`; đồng bộ tên thuộc tính `conf_threshold`, `ttc_warning_sec`, `ttc_danger_sec` trong `ObstacleTracker`. | **Đã sửa** |
| 5 | Giờ lịch sử chậm 7 tiếng (UTC) | SQLite mặc định lưu UTC. | Truyền tường minh `created_at=datetime.now()`, `updated_at=datetime.now()`. | **Đã sửa** |
| 6 | Không hiện badge đỏ `CRITICAL` trên `/driver/history` | `history.html` đọc `item.severity` thiếu `item.risk_level` ở cả Mobile và Desktop. | Cập nhật đọc `item.risk_level` ở cả 2 vị trí. | **Đã sửa** |
| 7 | Ảnh snapshot ở `/driver/history` hiện biểu tượng ảnh vỡ | `AlertReporter` lưu tên file trần (`alert_u...jpg`), `history.html` gán trực tiếp vào `src` và Flask chưa có route phục vụ `storage/snapshots/`. | Thêm route `GET /snapshots/<path:filename>` (`send_from_directory`) và hàm `_normalize_snapshot_url` trong `alert_controller.py` (đồng thời xóa decorator route bị trùng). | **Đang kiểm tra** |
| 8 | Dòng `#alert-message` tràn khung đỏ và mã biển `P-103a` bị gãy dòng trên HUD | Bootstrap 5 thiếu `.min-w-0` kết hợp `text-truncate` làm flex item không co; `.hud-sign-icon` chỉ rộng `2.35rem`. | Định nghĩa `.min-w-0`, bỏ `text-truncate`, bật `overflow-wrap: break-word` cho `#alert-message` và mở rộng `.hud-sign-icon` lên `3.75rem` + `white-space: nowrap` trong `hud.html`. | **Đang kiểm tra** |
| 9 | Dòng `window.CURRENT_USER_ID = {{ session.get('user_id') \| tojson }};` bị báo lỗi trên editor | Linter JS không hiểu cú pháp Jinja `{{ ... }}` đứng trần không bọc chuỗi trong `<script>`. | Đổi sang bọc chuỗi `"{{ session.get('user_id') or '' }}"` trong `hud.html`. | **Đang kiểm tra** |
| 10 | Biển báo không áp dụng cho loại xe đang chọn vẫn vẽ khung và lặp nhận diện trên HUD | Phiên bản đầu chỉ tắt TTS khi `applies_to_vehicle === false`, chưa lọc bỏ ở các khung hình sau trong `SignDetector`. | Thêm tập `_seen_irrelevant` trong `SignDetector` và gọi `reset_session(user_id)` trong `ws_detect.py` để chỉ báo đúng 1 lần rồi bỏ qua hoàn toàn. | **Đang kiểm tra** |
| 11 | Xung đột và rối âm thanh khi chạy song song luồng vật cản và biển báo trên HUD | Cả 2 luồng cùng dùng TTS (`tts.js`) dẫn đến chồng chéo câu đọc và phản xạ chậm khi gặp vật cản. | Tách kênh âm thanh hoàn toàn trong `hud.js`: bỏ `speakObstacleAlert`, vật cản chỉ phát còi qua `SmartAlertSound` (`WARNING` 1800ms, `CRITICAL` 700ms + gọi ngay `SmartTTS.stop()`), biển báo chỉ đọc TTS qua `SmartTTS`. | **Đã sửa** |
| 12 | Danh sách `/driver/history` (54+ dòng) và `/admin/signs` (56 biển) quá dài phải cuộn nhiều | Chưa có cơ chế phân trang trên giao diện. | Bổ sung phân trang client-side `PAGE_SIZE = 6` đồng bộ Desktop/Mobile và bộ lọc trên `history.html` & `signs.html`. | **Đang kiểm tra** |
| 13 | Biển báo gặp lại trên cùng cung đường hoặc khi dừng đèn đỏ bị đọc lặp lại liên tục | `hud.js` chưa có bộ đếm thời gian hiệu lực và kiểm tra khoảng trống biến mất khỏi khung hình cho từng `sign_code`. | Bổ sung `signStateMap` trong `hud.js` với cooldown **10 giây** (biển `W-`) / **25 giây** (nhóm khác) kết hợp điều kiện biển biến mất tối thiểu **4 giây** (`SIGN_REAPPEAR_GAP_MS = 4000`), reset khi bấm Dừng (`stopHUD`). | **Đã sửa** |
| 14 | `jinja2.exceptions.UndefinedError: 'm' is undefined` tại `/admin/models` | Dòng khai báo `is_deleted` bị đặt ngoài vòng lặp `{% for m in model_list %}` khi thêm tab xóa mềm. | Đưa khai báo `is_deleted` vào trong vòng lặp `{% for m in model_list %}` ở cả bảng Desktop và Card Mobile trong `models.html`. | **Đã sửa** |

---

## 3. Kế Hoạch Công Việc Tiếp Theo (Theo Thứ Tự Ưu Tiên)

1. **Ưu tiên 1 — Chạy vòng kiểm thử tổng thể (Regression Test) các hạng mục Đợt 2 còn lại:**
   * Khởi động lại cả 2 server (`python -m web_app.main` và `uvicorn ai_service.main:app --host 127.0.0.1 --port 8001`), bấm `Ctrl + F5` và xác nhận lần lượt:
     1. `/driver/history` & `/driver/history/<id>`: Ảnh snapshot hiển thị rõ, Modal phóng to hoạt động, phân trang 6 dòng/trang và nút lọc chạy đúng.
     2. `/admin/signs`: Phân trang 6 dòng/trang + tìm kiếm + lọc nhóm chạy đúng; sửa/khôi phục thử 1 biển và kiểm tra log FastAPI tự nạp lại RAM Cache.
     3. `/driver/hud`: Không tràn chữ khung cảnh báo, mã `P-103a` gọn 1 dòng, `window.CURRENT_USER_ID` không báo lỗi Console, biển khác loại xe chỉ báo 1 lần rồi bỏ qua.
2. **Ưu tiên 2 — Kiểm tra các điểm đồng bộ nhỏ còn lại trước khi đóng gói bảo vệ:**
   * Đọc `web_app/views/templates/driver/history_detail.html` để chắc chắn hiển thị ảnh chụp hiện trường khớp `/snapshots/<filename>` cùng danh sách `alert_objects`.
   * Kiểm tra đồng bộ trạng thái ban đầu của 2 nút `TTS` / `Còi` trên `hud.html` từ `user_settings` (`tts_enabled`, `alert_sound_enabled`).
   * Kiểm tra `web_app/controllers/auth_controller.py` xem Admin đăng nhập đã đổi redirect từ `/admin/signs` sang `/admin/dashboard` theo UC-01 hay chưa.
3. **Ưu tiên 3 — Tối ưu & chuẩn bị dữ liệu demo (nếu cần):**
   * Kiểm tra FPS thực tế trên video mẫu `.mp4`; nếu chạy CPU bị giật mới tối ưu chạy `sign_detector` cách nhịp 2–3 frame/lần.
   * Bổ sung bộ ảnh icon PNG cho 56 biển báo vào `web_app/views/static/sign_icons/` (tùy chọn theo yêu cầu).