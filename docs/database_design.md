# THIẾT KẾ CƠ SỞ DỮ LIỆU (DATABASE DESIGN) — SMARTDASHCAM

* **Phiên bản tài liệu:** 1.1
* **Ngày cập nhật:** 24/11/2026
* **Công nghệ:** SQLite (`storage/database/smartdashcam.db`) + SQLAlchemy 2.0 ORM.
* **Trạng thái Schema:** Giữ nguyên cấu trúc 8 bảng đã triển khai, **không thay đổi schema/cột/quan hệ** trong các đợt cập nhật gần nhất.

---

## 1. Cấu Hình & Quy Ước Chung

* **PRAGMA bắt buộc** (tự động bật trong `web_app/database/connection.py` mỗi khi kết nối):
  * `PRAGMA foreign_keys = ON;` (kiểm tra ràng buộc khóa ngoại).
  * `PRAGMA journal_mode = WAL;` (Write-Ahead Logging, hạn chế lỗi `database is locked` khi Flask ghi và FastAPI đọc cache).
* **Mixin dùng chung (`TimestampSoftDeleteMixin` trong `web_app/database/base.py`):**
  * Toàn bộ 8 bảng đều có: `created_at`, `updated_at`, `deleted_at` và các phương thức `is_deleted`, `soft_delete()`, `restore()`.
  * Mọi truy vấn hiển thị dữ liệu bắt buộc lọc `deleted_at IS NULL` thông qua hàm tiện ích `active_select(model)`.
  * **Lưu ý múi giờ:** SQLite/SQLAlchemy mặc định lưu UTC; khi tạo bản ghi mới (`CollisionAlert`, `AlertObject`) cần truyền tường minh `created_at=datetime.now()`, `updated_at=datetime.now()` để hiển thị đúng giờ Việt Nam (UTC+7).
* **Phân quyền (`users.role`):** Kiểu `Integer` (`0`: Admin, `1`: Tài xế).
* **Quy ước lưu & chuẩn hóa dữ liệu đặc thù:**
  * **Mã biển báo (`sign_code`):** Chuẩn hóa theo định dạng dấu gạch ngang (`-`, ví dụ `P-103a`) khớp 100% với 56 lớp nhãn trích xuất từ mô hình `best.pt`.
  * **Loại phương tiện (`vehicle_type`):** Chuẩn hóa giá trị `motorcycle -> motorbike` khi đọc/so khớp trong `SignDetector`.
  * **Đường dẫn ảnh chụp (`collision_alerts.snapshot_path`):** Lưu tệp `.jpg` tại `storage/snapshots/`. Hàm `_normalize_snapshot_url` trong `alert_controller.py` chuẩn hóa đường dẫn thành `/snapshots/<filename>` khi lưu mới và khi đọc (tương thích ngược với cả các bản ghi cũ lưu tên file trần).

---

## 2. Danh Sách 8 Bảng ORM (`web_app/models/`)

> **LƯU Ý QUAN TRỌNG:** Các bảng đã được đối chiếu trực tiếp từ SQLAlchemy được liệt kê đầy đủ cột thực tế. Với 5 bảng còn lại (đã hoàn thiện CRUD ở phân hệ Admin nhưng chưa gửi file model chi tiết trong phiên hiện tại), AI phiên sau **vẫn phải kiểm tra file ORM thực tế** trước khi viết thêm truy vấn mới để tránh lệch tên cột.

| STT | File Model | Tên bảng | Trạng thái xác nhận cột | Danh sách cột / Ghi chú thực tế |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `collision_alert.py` | `collision_alerts` | **Đã xác nhận đầy đủ** | `id`, `user_id`, `alert_type`, `risk_level`, `message`, `min_ttc`, `snapshot_path`, `created_at`, `updated_at`, `deleted_at`.<br>*Dữ liệu thực tế:* Các bản ghi mới đã lưu `snapshot_path` tương ứng ảnh `.jpg` trong `storage/snapshots/`. |
| 2 | `alert_object.py` | `alert_objects` | **Đã xác nhận đầy đủ** | `id`, `alert_id`, `track_id`, `object_label`, `confidence`, `bbox_x1`, `bbox_y1`, `bbox_x2`, `bbox_y2`, `estimated_ttc`, `created_at`, `updated_at`, `deleted_at`. |
| 3 | `user_setting.py` | `user_settings` | **Đã xác nhận đầy đủ** | `id`, `user_id`, `vehicle_type`, `tts_enabled`, `alert_sound_enabled`, `conf_threshold`, `ttc_warning_sec`, `ttc_danger_sec`, `created_at`, `updated_at`, `deleted_at`.<br>*Tương tác AI:* `SignDetector` đọc & cache `vehicle_type`, `conf_threshold` theo `user_id`. |
| 4 | `user.py` | `users` | **Đã dùng ổn định (UC-01/02/08)** *(Chưa in đủ danh sách cột)* | Lưu tài khoản người dùng (`role`: 0/1, `full_name`, `email`, `password_hash`...). Quan hệ `1:1` với `user_settings`, `1:N` với `collision_alerts`. |
| 5 | `ai_model.py` | `ai_models` | **Đã dùng ổn định (UC-07)** *(Chưa in đủ danh sách cột)* | Lưu phiên bản file `.pt` (loại `sign`/`obstacle`, checksum SHA-256, `imgsz`, `is_active`...).<br>*Tương tác AI:* FastAPI tự nạp model có `is_active = 1` khi khởi động. |
| 6 | `sign_category.py` | `traffic_sign_categories` | **Đã dùng ổn định (UC-06)** *(Chưa in đủ danh sách cột)* | Lưu 4 nhóm biển báo (Cấm, Nguy hiểm, Hiệu lệnh, Chỉ dẫn). |
| 7 | `sign_catalog.py` | `traffic_sign_catalog` | **Đã dùng ổn định (UC-06)** *(Chưa in đủ danh sách cột)* | Từ điển **56 biển báo** (`sign_code` dùng dấu gạch ngang `-` khớp `best.pt`, `tts_script`, `icon_url`, `priority`...).<br>*Tương tác AI:* Nạp toàn bộ lên RAM Cache của `SignDetector`, làm mới tự động khi Admin cập nhật UC-06. |
| 8 | `sign_vehicle.py` | `traffic_sign_vehicles` | **Đã dùng ổn định (UC-06)** *(Chưa in đủ danh sách cột)* | Ánh xạ biển báo theo loại phương tiện (ràng buộc duy nhất `sign_id`, `vehicle_type`). Dùng để xác định cờ `applies_to_vehicle` trên HUD. |

---

## 3. Dữ Liệu Khởi Tạo (`web_app/database/seed.py` & `scripts/init_db.py`)

* **Tài khoản Admin mặc định:** Tạo từ `ADMIN_EMAIL`, `ADMIN_PASSWORD` trong `.env` (`role = 0`) kèm 1 bản ghi `UserSetting` mặc định (chống trùng lặp).
* **Danh mục biển báo (Đã hoàn thiện Đợt 1 — 23–24/11/2026):**
  * Seed 4 nhóm biển báo cơ bản.
  * Đã trích xuất và nạp **đủ 56 lớp biển báo giao thông (`0` đến `55`)** từ mô hình `best.pt` vào bảng `traffic_sign_catalog` (dùng mã dấu gạch ngang `-`) cùng ánh xạ loại xe tương ứng.
  * Đã **xóa mềm** 4 biển báo mẫu cũ dùng dấu chấm (`P.102`, `P.127`, `W.224`, `R.301a`) khỏi dữ liệu hoạt động.