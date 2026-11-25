# NHẬT KÝ PHÁT TRIỂN #4 (DEVELOP LOG 4) — SMARTDASHCAM

* **Ngày thực hiện:** 24/11/2026 (Đợt 3)
* **Phạm vi:** Hoàn thiện bảo mật tài khoản Tài xế, cơ chế Xem lại & Khôi phục xóa mềm cho phân hệ Quản trị, tối ưu kênh âm thanh & chống lặp biển báo trên HUD và đồng bộ bộ tài liệu dự án lên phiên bản `1.2`.
* **Trạng thái chung:** Toàn bộ các hạng mục triển khai trong phiên đã được kiểm thử thực tế và hoạt động ổn định.

---

## 1. Mục Tiêu Phiên Làm Việc

1. Bổ sung tính năng **Đổi mật khẩu cho Tài xế (UC-09)** đặt gọn trong trang Cài đặt cá nhân (`/driver/settings`), tách biệt hoàn toàn với form lưu ngưỡng AI.
2. Triển khai cơ chế **Xem lại & Khôi phục dữ liệu đã xóa mềm** cho các phân hệ Quản trị viên (`users`, `signs`, `models`).
3. Giải quyết tình trạng rối âm thanh khi chạy song song 2 luồng AI (Vật cản + Biển báo) trên HUD và chống đọc lặp lại cùng một biển báo trên cùng đoạn đường / khi dừng đèn đỏ.
4. Cập nhật đồng bộ toàn bộ hệ thống tài liệu dự án lên phiên bản `1.2`.

---

## 2. Chi Tiết Các Hạng Mục Đã Triển Khai & Kiểm Thử

### 2.1. Tính năng Đổi mật khẩu cho Tài xế (UC-09)
* **Files cập nhật:**
  * `web_app/controllers/setting_controller.py`
  * `web_app/views/templates/driver/settings.html`
* **Chi tiết triển khai:**
  * Bổ sung route độc lập `POST /driver/settings/change-password`, không ảnh hưởng đến luồng lưu `user_settings` và đồng bộ `POST /api/v1/config` sang FastAPI.
  * Kiểm tra đầy đủ dữ liệu đầu vào (không bỏ trống, mật khẩu mới tối thiểu 6 ký tự, xác nhận khớp, không trùng mật khẩu cũ) và đối chiếu mật khẩu hiện tại qua `werkzeug.security.check_password_hash`.
  * Cập nhật `users.password_hash` bằng `generate_password_hash(new_password)`.
  * **Nâng cấp bảo mật:** Sau khi đổi mật khẩu thành công, gọi `session.clear()` trước khi `flash(...)` và chuyển hướng về `/login` để bắt buộc tài xế đăng nhập lại bằng mật khẩu mới.
  * Giao diện bổ sung khối **4. Bảo mật & Đổi mật khẩu** bằng `<form>` riêng, đồng bộ `theme-soft-blue`, có nút ẩn/hiện mật khẩu đạt chuẩn vùng chạm `44x44px` và kiểm tra khớp mật khẩu phía client.
* **Kết quả kiểm thử:** Đạt yêu cầu (đã xác nhận đổi mật khẩu, bắt đăng nhập lại và form lưu ngưỡng AI vẫn chạy độc lập).

### 2.2. Xem lại & Khôi phục dữ liệu đã xóa mềm (Phân hệ Admin)
Áp dụng thống nhất bộ tab Pill `.status-pill-tab` (`Đang hoạt động` `?status=active` / `Đã xóa mềm` `?status=deleted`, kèm badge đếm số lượng) và nút **Khôi phục** đồng bộ trên cả Bảng Desktop lẫn Card Mobile:

1. **Quản lý tài khoản (`/admin/users`):**
   * **Files:** `web_app/controllers/user_controller.py`, `web_app/views/templates/admin/users.html`.
   * Đếm và lọc `deleted_at IS NULL` / `deleted_at IS NOT NULL`, đổi cột `Ngày tạo` thành `Ngày xóa` khi ở tab xóa mềm, ẩn nút Sửa/Xóa với bản ghi đã xóa mềm.
   * Sử dụng route `POST /admin/users/<int:user_id>/restore` khôi phục đồng thời cả `User` và `UserSetting` liên quan.
2. **Danh mục biển báo (`/admin/signs`):**
   * **Files:** `web_app/controllers/sign_controller.py`, `web_app/views/templates/admin/signs.html`.
   * Bổ sung route `POST /admin/signs/<int:sign_id>/restore` khôi phục cả `TrafficSignCatalog` và toàn bộ bản ghi `TrafficSignVehicle` liên quan, sau đó gọi `_sync_sign_cache_to_ai()` để nạp lại RAM Cache trên FastAPI.
   * Giữ nguyên cơ chế tìm kiếm, lọc nhóm và phân trang client-side `PAGE_SIZE = 6`.
3. **Quản lý mô hình AI (`/admin/models`):**
   * **Files:** `web_app/controllers/model_controller.py`, `web_app/views/templates/admin/models.html`.
   * Bổ sung route `POST /admin/models/<int:model_id>/restore` khôi phục bản ghi `AIModel` và đặt tường minh `is_active = False` để mô hình quay về trạng thái **Chờ kích hoạt**, tránh xung đột với mô hình đang chạy trên RAM.
4. **Quyết định phạm vi:** Chốt **lược bỏ** chức năng xem lại & khôi phục xóa mềm đối với **Lịch sử cảnh báo (`/driver/history`)**.
* **Kết quả kiểm thử:** Đạt yêu cầu trên cả 3 phân hệ Admin.

### 2.3. Tối ưu âm thanh HUD & Cooldown chống lặp biển báo
* **File cập nhật:** `web_app/views/static/js/hud.js` *(tận dụng các hàm có sẵn của `alert_sound.js` và `tts.js`, không cần thay đổi schema CSDL vì khớp 100% với 2 cột `tts_enabled` và `alert_sound_enabled` trong `user_settings`)*.
* **Chi tiết triển khai:**
  * **Tách kênh âm thanh hoàn toàn:**
    * Bỏ `speakObstacleAlert(...)`: Vật cản chỉ phát còi qua `SmartAlertSound.play(level)` (`WARNING`: bíp đơn giãn cách `1800ms`; `CRITICAL`: bíp đôi dồn dập giãn cách `700ms`).
    * Khi cảnh báo vật cản đạt mức `CRITICAL`, lập tức gọi `SmartTTS.stop()` để ngắt giọng đọc biển báo và ưu tiên tối đa cho còi khẩn cấp.
    * Biển báo chỉ đọc giọng nói TTS khi `applies_to_vehicle !== false` và hệ thống không ở mức `CRITICAL`.
  * **Thời gian hiệu lực & Chống lặp khi dừng đèn đỏ (`signStateMap`):**
    * Vẫn vẽ khung xanh dương liên tục trên `<canvas>` theo thời gian thực.
    * Chỉ đọc TTS và thêm vào danh sách cột phải khi thỏa đồng thời 2 điều kiện: đã qua thời gian hiệu lực (**10 giây** với biển nguy hiểm `W-`, **25 giây** với nhóm cấm/hiệu lệnh/chỉ dẫn) **VÀ** biển báo đã biến mất khỏi khung hình ít nhất **4 giây** (`SIGN_REAPPEAR_GAP_MS = 4000`).
    * Tự động gọi `signStateMap.clear()` khi bấm **Dừng** (`stopHUD`).
* **Kết quả kiểm thử:** Đạt yêu cầu; luồng âm thanh gọn gàng, dễ phản xạ và không còn bị đọc lặp biển báo.

---

## 3. Lỗi Phát Sinh & Cách Khắc Phục Trong Phiên

| # | Lỗi phát sinh | Nguyên nhân | Cách khắc phục | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `jinja2.exceptions.UndefinedError: 'm' is undefined` tại `/admin/models` | Dòng khai báo `{% set is_deleted = ... %}` bị đặt bên ngoài vòng lặp `{% for m in model_list %}` khi chèn giao diện tab xóa mềm. | Chuẩn hóa lại toàn bộ template `admin/models.html`, đưa khai báo `is_deleted` vào bên trong vòng lặp `{% for m in model_list %}` cho cả bảng Desktop và Card Mobile. | **Đã sửa** |

---

## 4. Đồng Bộ Tài Liệu Dự Án (Phiên Bản 1.2)

Đã rà soát và cập nhật đồng bộ 6 tài liệu dự án lên **phiên bản 1.2** (giữ nguyên `DATABASE_DESIGN.md` do không thay đổi schema):
* `UI_UX_GUIDELINES.md`: Cập nhật khối Đổi mật khẩu trên `settings.html`, bộ tab xóa mềm trên `users.html`/`signs.html`/`models.html` và luồng JS tách kênh âm thanh + cooldown biển báo.
* `AI_INSTRUCTIONS.md`: Bổ sung các quy ước bắt buộc mới (tách kênh âm thanh HUD, cooldown biển báo, đổi mật khẩu xóa session, phạm vi khôi phục xóa mềm).
* `functional_specification.md`: Bổ sung **UC-09 (Đổi mật khẩu Tài xế)** và chi tiết nghiệp vụ cho cơ chế khôi phục xóa mềm & tách kênh âm thanh HUD.
* `implementation_log.md`: Ghi nhận mốc Đợt 3, cập nhật trạng thái lỗi #11 và bổ sung lỗi #13, #14 đã xử lý.
* `project_context.md`: Nâng phạm vi lên 9 Use Case + Admin Dashboard, cập nhật bảng thay đổi so với thiết kế ban đầu.
* `system_architecture.md`: Bổ sung trường hợp gọi `POST /api/v1/signs/reload-cache` khi khôi phục biển báo và ngoại lệ lọc xóa mềm cho tab `?status=deleted` của 3 phân hệ Admin.

---

## 5. Hạng Mục Cần Rà Soát Ở Phiên Kế Tiếp (Trước Khi Đóng Gói)

1. Kiểm tra `web_app/views/templates/driver/history_detail.html` để xác nhận hiển thị ảnh chụp hiện trường qua `/snapshots/<filename>` cùng danh sách `alert_objects`.
2. Kiểm tra đồng bộ trạng thái ban đầu của 2 nút `TTS` / `Còi` trên `hud.html` theo giá trị `tts_enabled` và `alert_sound_enabled` trong `user_settings`.
3. Kiểm tra `web_app/controllers/auth_controller.py` xem Admin sau khi đăng nhập đã chuyển hướng đúng về `/admin/dashboard` theo UC-01 hay chưa.