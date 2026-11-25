# QUY CHUẨN THIẾT KẾ GIAO DIỆN (UI/UX GUIDELINES) — SMARTDASHCAM

* **Phiên bản tài liệu:** 1.2
* **Ngày cập nhật:** 24/11/2026
* **Trạng thái:** Đã hoàn tất giao diện Frontend (Bootstrap 5 + Jinja2) và nối logic hiển thị cho toàn bộ 2 phân hệ Tài xế (`role = 1`) và Quản trị viên (`role = 0`). Đã bổ sung và kiểm thử hoàn chỉnh khối Đổi mật khẩu Tài xế, bộ tab Xem lại & Khôi phục dữ liệu đã xóa mềm cho 3 phân hệ Admin (Tài khoản, Biển báo, Mô hình AI) cùng cơ chế tách kênh âm thanh và cooldown chống lặp biển báo trên HUD.

---

## 1. Nguyên Tắc Responsive & Hệ Thống Thiết Kế

### 1.1. 5 Nguyên tắc Responsive cốt lõi
1. **Mobile-First Design:** Viết CSS mặc định từ màn hình điện thoại nhỏ rồi mở rộng lên Tablet và Desktop.
2. **Grid System & Flexbox:** Lưới 12 cột Bootstrap 5 kết hợp Flexbox chuyển bố cục ngang/dọc tự động.
3. **4 mốc Breakpoint chuẩn:**
   * Điện thoại nhỏ: `320px – 480px`
   * Phablet: `481px – 768px`
   * Tablet: `769px – 1024px`
   * Laptop / Desktop: `>= 1025px` (kèm tối ưu riêng cho chế độ xoay ngang `landscape`).
4. **Fluid Layouts & Typography:** Dùng `%`, `vw`, `vh`, `rem`, `clamp()` (cỡ chữ tối thiểu `14px` trên di động); ảnh dùng `object-fit: cover / contain`.
5. **Vùng chạm cảm ứng (Touch Target):** Toàn bộ nút bấm, liên kết điều hướng, tab lọc và công tắc tối thiểu `44x44px`.

### 1.2. Ngôn ngữ giao diện (`theme-soft-blue`)
* **Màu sắc:** Đồng bộ với `auth.css` — nền gradient xanh dương pastel, card trắng bo góc lớn, viền xanh nhạt, nút hành động chính xanh dương gradient (nút Dừng/Xóa dùng đỏ gradient).
* **Khung điều hướng (`base.html` & `style.css`):** Tự động phân nhánh theo `session.role`:
  * **Desktop (`>= 1025px`):** Top Navbar cố định trên cùng.
  * **Mobile / Tablet (`< 1025px`):** Tài xế dùng **Bottom Navigation Bar** cố định dưới đáy (3 mục: *HUD, Lịch sử, Cài đặt*); Admin dùng **Offcanvas Drawer** trượt từ cạnh trái.
* **Thông báo (`flash`):** Hiển thị dạng **Bootstrap Toast** nổi góc trên phải, tự ẩn sau 4 giây.
* **Tab trạng thái xóa mềm (`.status-pill-tab`):** Dùng thống nhất trên 3 trang quản trị (`/admin/users`, `/admin/signs`, `/admin/models`) để chuyển giữa `Đang hoạt động` (`?status=active`) và `Đã xóa mềm` (`?status=deleted`), kèm badge đếm số lượng từng tab và đạt chuẩn chiều cao tối thiểu `44px`.
* **Hiển thị danh sách & Phân trang:**
  * Dạng **Bảng** trên Desktop/Tablet (`>= 769px`) và tự chuyển thành **Card dọc** trên Mobile (`< 769px`) để bỏ thanh cuộn ngang.
  * **Quy ước phân trang đã thống nhất:** Áp dụng phân trang phía client với hằng số **`PAGE_SIZE = 6`** trên các trang danh sách dài (`/driver/history`, `/admin/signs`), đồng bộ giữa bảng Desktop, Card Mobile và các bộ lọc/tìm kiếm tức thì hiện có (không dùng SQL `LIMIT/OFFSET` để giữ tốc độ lọc tức thì).
* **An toàn Template:** Mọi biến Jinja2 đều kiểm tra `is defined` và có giá trị mặc định để tránh `UndefinedError`.

---

## 2. Bản Đồ Trang Giao Diện & Hợp Đồng Biến Jinja2

### 2.1. Phân hệ Xác thực (`web_app/views/templates/auth/`)
| File Template | Route | Đặc điểm UI/UX & Lưu ý |
| :--- | :--- | :--- |
| `login.html` | `GET, POST /auth/login` | Nền xanh pastel, 8 thẻ icon giao thông nổi (6 trắng + 2 xanh nhạt `soft-blue`), ẩn/hiện mật khẩu, ghi nhớ đăng nhập 7 ngày. |
| `register.html` | `GET, POST /auth/register` | Đồng bộ phong cách `login.html` (đã bổ sung đủ 8 thẻ icon nổi). Không bắt buộc chọn loại xe ở form đăng ký. |

### 2.2. Phân hệ Tài xế (`web_app/views/templates/driver/`)
| File Template | Route | Biến Jinja2 mong đợi | Đặc điểm UI/UX & Cập nhật mới nhất |
| :--- | :--- | :--- | :--- |
| `hud.html` | `GET /driver/hud` | `session.get('user_id')` (bọc chuỗi: `window.CURRENT_USER_ID = "{{ session.get('user_id') or '' }}";`) | Khung `<video>` + `<canvas id="hud-canvas">` nền tối (~80% chiều rộng Desktop) vẽ song song: khung nét đứt **"VÙNG GIÁM SÁT"** (`data.roi`), khung bao vật cản và khung bao biển báo màu xanh dương. Cột phải hiển thị Trạng thái an toàn & Biển báo gần đây (`addSignToList` hiển thị thêm nhãn `• Khác loại xe` nếu `applies_to_vehicle === false`).<br>**Bản vá UI:** Định nghĩa `.min-w-0 { min-width: 0; }`, bỏ `text-truncate` và bật `white-space: normal; overflow-wrap: break-word` cho `#alert-message` chống tràn chữ; mở rộng `.hud-sign-icon` thành `3.75rem` + `white-space: nowrap` để mã biển 5–6 ký tự (`P-103a`) không gãy dòng.<br>**Ghi chú:** Đồng bộ trạng thái nút bật/tắt `TTS` & `Còi` ban đầu từ `user_settings` sang `hud.html` cần rà soát thêm. |
| `history.html` | `GET /driver/history` <br> `POST /driver/history/delete` <br> `GET /snapshots/<path:filename>` | `alerts` (hoặc `history`) | Chỉ hiển thị cảnh báo va chạm (`WARNING`/`CRITICAL`). Đọc `item.risk_level or item.severity or item.alert_level` ở cả Desktop và Mobile để hiện đúng badge đỏ `CRITICAL`. Dùng nút lọc 1 chạm (Pill Tabs). Ảnh thumbnail và Modal phóng to tải qua URL chuẩn hóa `/snapshots/<filename>`.<br>Áp dụng phân trang phía client **`PAGE_SIZE = 6`** đồng bộ Desktop & Mobile, tự tính lại trang khi đổi bộ lọc, hiển thị `Hiển thị X–Y / Z sự kiện`. *(Không triển khai tab khôi phục xóa mềm theo quyết định dự án).* |
| `history_detail.html` | `GET /driver/history/<id>` | `alert`, `alert_objects` | Bố cục 2 cột Desktop (ảnh hiện trường bên trái, 4 ô thông số bên phải), bảng danh sách vật thể bên dưới (`alert.risk_level`, `obj.object_label` dịch tiếng Việt, `obj.bbox_x1..y2`, `obj.confidence`, `obj.estimated_ttc`). |
| `settings.html` | `GET, POST /driver/settings` <br> `POST /driver/settings/change-password` | `setting` | Gồm **4 khối** (tách làm 2 `<form>` độc lập):<br>1. Radio Card 4 loại xe (`car`, `motorbike`, `truck`, `bus`).<br>2. Range Slider ngưỡng AI/TTC (kèm 3 nút Preset: *Nội thành, Tiêu chuẩn, Cao tốc*; khóa nút Lưu nếu `ttc_danger_sec >= ttc_warning_sec`).<br>3. Công tắc bật/tắt TTS (đọc biển báo) & Còi (cảnh báo vật cản).<br>4. **Bảo mật & Đổi mật khẩu:** Form riêng gồm Mật khẩu hiện tại, Mật khẩu mới (tối thiểu 6 ký tự), Xác nhận mật khẩu mới, nút ẩn/hiện mật khẩu chuẩn `44x44px`, kiểm tra khớp phía client; sau khi đổi thành công tự động xóa session (`session.clear()`) và chuyển về `/login` bắt đăng nhập lại. |

### 2.3. Phân hệ Quản trị viên (`web_app/views/templates/admin/`)
| File Template | Route | Biến Jinja2 mong đợi | Đặc điểm UI/UX & Cập nhật mới nhất |
| :--- | :--- | :--- | :--- |
| `dashboard.html` | `GET /admin/dashboard` | `stats`, `ai_status`, `active_models`, `category_stats`, `recent_alerts` | Thuần giám sát & thống kê (đã nối dữ liệu SQLite thật & ping FastAPI `:8001`). 4 thẻ KPI, tình trạng AI Service & 2 model trên RAM, biểu đồ thanh ngang 4 nhóm biển báo, bảng cảnh báo gần đây. |
| `signs.html` | `GET /admin/signs` (`?status=active\|deleted`) <br> `POST /admin/signs/delete` <br> `POST /admin/signs/<id>/restore` | `signs`, `categories`, `status`, `active_count`, `deleted_count` | Tìm kiếm theo mã biển dấu gạch ngang (`sign_code`, ví dụ `P-103a`) hoặc tên, lọc theo nhóm biển, Modal xác nhận xóa mềm. Bổ sung **Tab Đang hoạt động / Đã xóa mềm** và nút **Khôi phục** đồng bộ cả Desktop & Mobile (khôi phục cả `TrafficSignVehicle` liên quan và tự động làm mới AI Cache). Giữ nguyên phân trang phía client **`PAGE_SIZE = 6`**. |
| `sign_form.html` | `GET, POST /admin/signs/new` <br> `GET, POST /admin/signs/<id>/edit` | `sign`, `categories`, `selected_vehicles` | Form dùng chung Thêm/Sửa: `sign_code`, `category_id`, `priority`, `name`, `tts_script` (có nút Nghe thử TTS bằng Web Speech API), `icon_url` (xem trước ảnh), checkbox `vehicle_types`. |
| `models.html` | `GET /admin/models` (`?status=active\|deleted`) <br> `POST /admin/models/upload`, `/activate`, `/delete` <br> `POST /admin/models/<id>/restore` | `models`, `status`, `active_count`, `deleted_count` | Bố cục 4:8 (trái: Drag & Drop file `.pt`, kiểm tra đuôi `.pt`, chọn `sign`/`obstacle` và `imgsz`; phải: danh sách phiên bản, checksum SHA-256, trạng thái). Bổ sung **Tab Đang hoạt động / Đã xóa mềm** và nút **Khôi phục** đồng bộ Desktop & Mobile (đưa mô hình về trạng thái `Chờ kích hoạt`, `is_active = False`). Modal Kích hoạt (Hot-Reload) & Xóa mềm (khóa xóa model đang chạy). |
| `users.html` | `GET /admin/users` (`?status=active\|deleted`) <br> `POST /admin/users/delete` <br> `POST /admin/users/<id>/restore` | `users`, `status`, `active_count`, `deleted_count` | 3 thẻ KPI, tìm kiếm tên/email, lọc vai trò, Modal xóa mềm (tự khóa nút xóa với `session.user_id`). Bổ sung **Tab Đang hoạt động / Đã xóa mềm** (đổi cột `Ngày tạo` sang `Ngày xóa` ở tab xóa mềm, ẩn nút Sửa) và nút **Khôi phục** đồng bộ cả Desktop & Mobile (khôi phục cả `User` và `UserSetting`). |
| `user_form.html` | `GET, POST /admin/users/new` <br> `GET, POST /admin/users/<id>/edit` | `user` | Form dùng chung Thêm/Sửa: `full_name`, `email`, `password` (bắt buộc khi tạo mới, để trống khi sửa để giữ cũ), Radio Card vai trò (`0`: Admin, `1`: Tài xế). |

---

## 3. Tương Tác Frontend JS Trên Màn Hình HUD (`web_app/views/static/js/`)
* **`hud.js`:** Mở webcam/video mẫu, gửi frame qua `WS /ws/detect?user_id=...`, vẽ khung ROI + khung vật cản + khung biển báo xanh dương lên `<canvas id="hud-canvas">`.
  * **Tách kênh âm thanh:** Vật cản chỉ phát còi (`SmartAlertSound`), không đọc TTS; khi đạt mức `CRITICAL` lập tức gọi `SmartTTS.stop()` để nhường toàn bộ âm thanh cho còi khẩn cấp. Biển báo chỉ đọc TTS khi `applies_to_vehicle !== false` và hệ thống không ở mức `CRITICAL`.
  * **Thời gian hiệu lực & chống lặp biển báo (`signStateMap`):** Vẫn vẽ khung biển báo liên tục trên Canvas, nhưng việc đọc TTS và thêm vào danh sách cột phải áp dụng cooldown theo từng `sign_code` (**10 giây** với biển nguy hiểm `W-`, **25 giây** với nhóm cấm/hiệu lệnh/chỉ dẫn) kết hợp điều kiện biển đã biến mất khỏi khung hình ít nhất **4 giây** (`SIGN_REAPPEAR_GAP_MS = 4000`) để chống lặp khi dừng đèn đỏ. Tự động reset `signStateMap` khi bấm Dừng (`stopHUD`).
* **`tts.js`:** Đảm nhiệm đọc biển báo giao thông qua Web Speech API (giọng `vi-VN`), có hàng đợi ưu tiên và hàm `SmartTTS.stop()` để ngắt ngay khi gặp vật cản `CRITICAL`.
* **`alert_sound.js`:** Đảm nhiệm toàn bộ âm thanh cảnh báo vật cản qua Web Audio API (không cần file âm thanh ngoài), phân 2 nhịp rõ ràng: `WARNING` (bíp đơn `780Hz`, giãn cách tối thiểu `1800ms`) và `CRITICAL` (bíp đôi dồn dập `1150Hz–1350Hz`, giãn cách tối thiểu `700ms`).