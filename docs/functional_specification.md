# ĐẶC TẢ CHỨC NĂNG (FUNCTIONAL SPECIFICATION) — SMARTDASHCAM

* **Phiên bản tài liệu:** 1.2
* **Ngày cập nhật:** 24/11/2026

---

## 1. Tác Nhân (Actors)
* **Người dùng `{abstract}`:** Đăng nhập hệ thống (UC-01).
* **Tài xế (`role = 1`):** Kế thừa Người dùng; sử dụng UC-02, UC-03, UC-04, UC-05, UC-09.
* **Quản trị viên (`role = 0`):** Kế thừa Người dùng; sử dụng Admin Dashboard, UC-06, UC-07, UC-08.
* **Secondary Actor:** `FastAPI AI Service` (nhận diện biển báo `best.pt`, theo dõi vật cản `ByteTrack`, chụp ảnh hiện trường, đồng bộ cấu hình, làm mới RAM Cache, xác thực & nạp nóng model).

---

## 2. Tổng Hợp Use Case & Trạng Thái Triển Khai

| Mã UC | Tên Use Case | Tác nhân | Trạng thái hiện tại | Ghi chú thực tế so với đặc tả gốc |
| :--- | :--- | :--- | :--- | :--- |
| **UC-01** | Đăng nhập hệ thống | Tài xế, Admin | **Hoàn thành** *(1 điểm cần kiểm tra)* | Dùng Flask Signed Cookie, phân quyền `role = 0/1`. **Cần kiểm tra:** Chưa xác định `auth_controller.py` đã đổi redirect Admin từ `/admin/signs` sang `/admin/dashboard` hay chưa. |
| **UC-02** | Đăng ký tài khoản | Tài xế | **Hoàn thành** | Tự khởi tạo `user_settings` mặc định (`vehicle_type = 'car'`), không bắt buộc chọn loại xe lúc đăng ký. |
| **UC-03** | Giám sát lái xe trực tiếp (HUD) | Tài xế, AI Service | **Đã triển khai đầy đủ (Đã tối ưu âm thanh & chống lặp)** | **Đã xác nhận chạy song song:** `ObstacleTracker` (ByteTrack + ROI + TTC + ngoại lệ vật thể quá lớn) + `SignDetector` (`best.pt` 56 lớp + RAM Cache + vẽ khung xanh dương) + chụp ảnh snapshot lưu SQLite & `storage/snapshots/`.<br>**Cập nhật mới (Đã kiểm thử):** Tách kênh âm thanh (**Vật cản chỉ phát còi**, `CRITICAL` ngắt ngay TTS; **Biển báo chỉ đọc TTS**), áp dụng cooldown hiệu lực biển báo (`W-` 10 giây, nhóm khác 25 giây) kết hợp chống lặp khi dừng xe (4 giây) trên `hud.js`.<br>**Cần rà soát:** Đồng bộ trạng thái ban đầu của 2 nút `TTS`/`Còi` trên HUD từ `user_settings`. **Tạm hoãn:** Camera ngoài. |
| **UC-04** | Quản lý lịch sử cảnh báo | Tài xế | **Đã triển khai đầy đủ** *(Bản vá Đợt 2: Đang kiểm tra)* | Đã lưu cảnh báo kèm `snapshot_path`, hiển thị giờ UTC+7, badge đỏ `CRITICAL`, lọc 1 chạm, xóa mềm, phân trang client-side `PAGE_SIZE = 6`. Phục vụ ảnh qua `GET /snapshots/<path:filename>` (kèm `_normalize_snapshot_url`).<br>*(Quyết định phạm vi: Không triển khai tính năng xem lại & khôi phục bản ghi đã xóa mềm cho Lịch sử cảnh báo).* |
| **UC-05** | Quản lý cài đặt cá nhân | Tài xế, AI Service | **Hoàn thành** | Lưu `user_settings` vào SQLite (`ttc_danger_sec < ttc_warning_sec`) và gọi `POST /api/v1/config` cập nhật nóng cho `ObstacleTracker`, đồng thời cập nhật `conf_threshold` và xóa cache `user_settings` + `_seen_irrelevant` trên `SignDetector`. Tách biệt hoàn toàn với form Đổi mật khẩu (UC-09) trên cùng trang `/driver/settings`. |
| **UC-06** | Quản lý danh mục biển báo | Admin, AI Service | **Hoàn thành (Đã xác nhận)** | Đã nạp đủ **56 biển báo** mã dấu gạch ngang (`-`) khớp `best.pt` (xóa mềm 4 biển mẫu cũ), CRUD 3 bảng, phân trang client-side `PAGE_SIZE = 6` và tự động gọi `POST /api/v1/signs/reload-cache`.<br>**Mở rộng (Đã kiểm thử):** Bổ sung bộ tab `Đang hoạt động` / `Đã xóa mềm` (`?status=active\|deleted`) và chức năng **Khôi phục** (`POST /admin/signs/<id>/restore`) khôi phục cả `TrafficSignCatalog` + `TrafficSignVehicle` và tự động làm mới AI Cache. |
| **UC-07** | Cập nhật Model AI (Local Hot-Reload) | Admin, AI Service | **Hoàn thành (Đã xác nhận)** | Hoàn thiện tải `.pt` vào `storage/models/`, kiểm tra SHA-256, chạy thử (Dummy Inference), nạp nóng sang `SignDetector`/`ObstacleTracker` và tự động Rollback nếu lỗi.<br>**Mở rộng (Đã kiểm thử):** Bổ sung bộ tab `Đang hoạt động` / `Đã xóa mềm` (`?status=active\|deleted`) và chức năng **Khôi phục** (`POST /admin/models/<id>/restore`) đưa mô hình về trạng thái `Chờ kích hoạt` (`is_active = False`). |
| **UC-08** | Quản lý tài khoản người dùng | Admin | **Hoàn thành (Đã xác nhận)** | Hoàn thiện CRUD tài khoản, tạo kèm `user_settings`, cấm tự xóa chính mình, xóa mềm.<br>**Mở rộng (Đã kiểm thử):** Bổ sung bộ tab `Đang hoạt động` / `Đã xóa mềm` (`?status=active\|deleted`) và chức năng **Khôi phục** (`POST /admin/users/<id>/restore`) khôi phục đồng thời cả `User` và `UserSetting`. |
| **UC-09** *(Mới)* | Đổi mật khẩu tài khoản (Tài xế) | Tài xế | **Hoàn thành (Đã kiểm thử)** | Đặt gọn thành khối riêng trong `/driver/settings` (`POST /driver/settings/change-password`), xác thực mật khẩu cũ bằng `werkzeug.security`, tự động xóa phiên đăng nhập (`session.clear()`) và chuyển hướng về `/login` bắt đăng nhập lại sau khi đổi thành công. |
| *(Bổ sung)* | **Admin Dashboard** (`/admin/dashboard`) | Admin | **Hoàn thành (Đã xác nhận)** | Đã nối dữ liệu thật từ SQLite (KPI, phân bố 4 nhóm biển, cảnh báo gần đây) và ping trạng thái FastAPI AI Service (`:8001`). |

---

## 3. Chi Tiết Logic Nghiệp Vụ Đã Chốt

### 3.1. Phát hiện vật cản & Chụp ảnh hiện trường (UC-03, UC-04)
* **Lọc theo ROI & Vật thể quá lớn (`ObstacleTracker`):**
  * Chỉ tính cảnh báo nếu điểm chân `(cx, y2)` nằm trong vùng ROI (`x1=15%`, `x2=85%`, `y1=50%`, `y2=95%`).
  * **Ngoại lệ:** Bỏ giới hạn `classes` trong `model.track()`; bất kỳ vật thể nào chiếm `>= 35%` diện tích khung hình hoặc `>= 45%` diện tích ROI sẽ bỏ qua bộ lọc ROI/lớp và ép thẳng lên mức `CRITICAL`.
* **Gửi cảnh báo & Lưu Snapshot (`AlertReporter`):**
  * Chạy trên luồng nền `_save_and_send` để không làm giảm FPS của WebSocket.
  * Áp dụng cooldown **5 giây** theo `user_id`; **vượt cooldown ngay lập tức** khi mức cảnh báo nâng từ `WARNING` lên `CRITICAL`.
  * Vẽ khung bao và nhãn vật thể nguy hiểm lên bản sao khung hình, lưu tệp `.jpg` vào `AIConfig.SNAPSHOTS_DIR` (`storage/snapshots/`) rồi gửi `POST /api/internal/alerts` về Flask.
* **Phục vụ ảnh Snapshot (`alert_controller.py`):**
  * Phục vụ tệp ảnh qua route `GET /snapshots/<path:filename>` (có kiểm tra đăng nhập qua session).
  * Hàm `_normalize_snapshot_url` chuẩn hóa đường dẫn thành `/snapshots/<filename>` khi lưu mới và khi đọc danh sách/chi tiết (tương thích ngược với các bản ghi cũ).

### 3.2. Nhận diện biển báo, Lọc loại xe & Đồng bộ RAM Cache (UC-03, UC-05, UC-06)
* **Chạy song song & RAM Cache (`SignDetector`):**
  * Tự nạp mô hình biển báo đang `is_active = 1` từ SQLite khi khởi động FastAPI; nạp toàn bộ 56 biển báo lên RAM Cache.
  * Chạy song song cùng `ObstacleTracker` trong `/ws/detect`; trả về tọa độ để `hud.js` vẽ khung bao màu xanh dương.
* **Lọc theo loại phương tiện (`user_settings.vehicle_type`):**
  * `SignDetector` đọc và cache `vehicle_type`, `conf_threshold` từ `user_settings` theo `user_id` (chuẩn hóa `motorcycle -> motorbike`), gắn cờ `applies_to_vehicle`.
  * **Quy tắc biển báo khác loại xe (`applies_to_vehicle === false`):** Nhận diện và hiển thị ở cột phải HUD đúng **1 lần duy nhất** (kèm nhãn `• Khác loại xe`, **không đọc TTS**), sau đó lưu vào tập `_seen_irrelevant` để **bỏ qua hoàn toàn** ở các khung hình tiếp theo (không vẽ bbox, không lặp lại) cho tới khi người dùng đổi cài đặt (`POST /api/v1/config`), Admin reload cache (`POST /api/v1/signs/reload-cache`) hoặc mở phiên HUD mới (`reset_session(user_id)`).
* **Đồng bộ nóng RAM Cache (UC-06 → AI Service):**
  * Khi Admin thêm, sửa, xóa mềm hoặc **khôi phục** biển báo trong `sign_controller.py`, hệ thống thực hiện `db.commit()` và gọi `_sync_sign_cache_to_ai()` (`POST /api/v1/signs/reload-cache`) để FastAPI nạp lại danh sách biển báo hoạt động lên RAM Cache (bắt lỗi an toàn nếu AI Service đang tắt).

### 3.3. Tách kênh âm thanh & Chống lặp biển báo trên HUD (`hud.js`, `tts.js`, `alert_sound.js`)
* **Tách kênh âm thanh hoàn toàn (khớp với 2 công tắc `tts_enabled` và `alert_sound_enabled` trong `user_settings`):**
  * **Cảnh báo vật cản (`ObstacleTracker`) → Chỉ phát còi (`SmartAlertSound`):**
    * Mức `WARNING`: Bíp đơn (`780Hz`), giãn cách tối thiểu `1800ms`.
    * Mức `CRITICAL`: Bíp đôi dồn dập (`1150Hz–1350Hz`), giãn cách tối thiểu `700ms`, đồng thời lập tức gọi `SmartTTS.stop()` để ngắt giọng đọc biển báo và nhường toàn bộ âm thanh cho cảnh báo khẩn cấp.
    * Không đọc TTS cho vật cản nhằm tránh chồng chéo và tăng tốc độ phản xạ.
  * **Nhận diện biển báo (`SignDetector`) → Chỉ đọc giọng nói TTS (`SmartTTS`):**
    * Chỉ đọc giọng tiếng Việt (`vi-VN`) khi `applies_to_vehicle !== false` và trạng thái va chạm hiện tại không phải `CRITICAL`.
* **Thời gian hiệu lực & Chống lặp khi dừng xe (`signStateMap` trong `hud.js`):**
  * Khung bao xanh dương trên `<canvas>` vẫn vẽ liên tục theo thời gian thực.
  * Việc đọc TTS và thêm bản ghi vào cột phải chỉ kích hoạt lại cho cùng một `sign_code` khi thỏa đồng thời 2 điều kiện:
    1. Đã qua thời gian hiệu lực (**10 giây** với nhóm biển nguy hiểm mã `W-`; **25 giây** với nhóm biển cấm, hiệu lệnh, chỉ dẫn).
    2. Biển báo đó đã biến mất khỏi khung hình ít nhất **4 giây** (`SIGN_REAPPEAR_GAP_MS = 4000`), tránh việc xe dừng đèn đỏ trước biển báo bị đọc lặp lại.
  * Bộ nhớ `signStateMap` được xóa sạch khi bấm **Dừng** (`stopHUD`).

### 3.4. Phân trang danh sách (`history.html`, `signs.html`)
* Thực hiện phân trang phía client với hằng số **`PAGE_SIZE = 6`** đồng bộ giữa bảng Desktop và Card Mobile.
* Tự động tính lại số trang và đưa về trang 1 khi thay đổi bộ lọc mức độ (`/driver/history`) hoặc nhập tìm kiếm / đổi nhóm biển báo (`/admin/signs`).

### 3.5. Đổi mật khẩu tài khoản Tài xế (UC-09)
* **Điều kiện tiên quyết:** Tài xế đã đăng nhập hợp lệ vào hệ thống.
* **Luồng chính (`POST /driver/settings/change-password`):**
  1. Tài xế nhập Mật khẩu hiện tại, Mật khẩu mới và Xác nhận mật khẩu mới tại khối *4. Bảo mật & Đổi mật khẩu* trong `/driver/settings`.
  2. Hệ thống kiểm tra hợp lệ: không bỏ trống, mật khẩu mới tối thiểu 6 ký tự, xác nhận khớp mật khẩu mới và mật khẩu mới không trùng mật khẩu cũ.
  3. Hệ thống truy vấn bản ghi `users` đang hoạt động (`deleted_at IS NULL`) và đối chiếu mật khẩu hiện tại bằng `werkzeug.security.check_password_hash`.
  4. Cập nhật `users.password_hash` bằng `generate_password_hash(new_password)` và lưu CSDL.
  5. Gọi `session.clear()` để hủy phiên hiện tại, hiển thị thông báo thành công và chuyển hướng về `/login` yêu cầu đăng nhập lại bằng mật khẩu mới.
* **Luồng phụ:** Nhập sai mật khẩu hiện tại hoặc dữ liệu không hợp lệ → báo lỗi qua Toast và giữ nguyên trang `/driver/settings`, không ảnh hưởng dữ liệu `user_settings`.

### 3.6. Xem lại & Khôi phục dữ liệu đã xóa mềm (Mở rộng UC-06, UC-07, UC-08)
* **Phạm vi áp dụng:** Áp dụng thống nhất cho 3 phân hệ Admin (`/admin/users`, `/admin/signs`, `/admin/models`); không áp dụng cho Lịch sử cảnh báo (`/driver/history`).
* **Luồng xem dữ liệu đã xóa mềm:**
  * Admin chuyển đổi giữa 2 tab `Đang hoạt động` (`?status=active`) và `Đã xóa mềm` (`?status=deleted`).
  * Hệ thống đếm số lượng bản ghi cho từng tab (`deleted_at IS NULL` và `deleted_at IS NOT NULL`) và hiển thị danh sách tương ứng (ẩn nút Sửa/Xóa/Kích hoạt đối với bản ghi đã xóa mềm, thay bằng nút **Khôi phục** đồng bộ trên cả Desktop và Mobile).
* **Luồng khôi phục (`POST .../restore`):**
  * **Tài khoản (`/admin/users/<id>/restore`):** Gọi `.restore()` cho cả bản ghi `users` và bản ghi `user_settings` liên quan.
  * **Biển báo (`/admin/signs/<id>/restore`):** Gọi `.restore()` cho `traffic_sign_catalog` và toàn bộ bản ghi `traffic_sign_vehicles` liên quan, `db.commit()` và gọi `_sync_sign_cache_to_ai()` để đồng bộ lại RAM Cache trên FastAPI.
  * **Mô hình AI (`/admin/models/<id>/restore`):** Gọi `.restore()` cho `ai_models` và đặt tường minh `is_active = False` để mô hình quay về trạng thái `Chờ kích hoạt`, tránh xung đột với mô hình đang chạy trên RAM.