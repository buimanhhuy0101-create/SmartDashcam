# BỐI CẢNH TỔNG THỂ DỰ ÁN — SMARTDASHCAM (ADAS LOCAL PROTOTYPE)

* **Phiên bản tài liệu:** 1.2
* **Ngày cập nhật:** 24/11/2026
* **Trạng thái dự án:** Giai đoạn kiểm thử tổng thể (Regression Test) và hoàn thiện cuối cùng — Toàn bộ phân hệ Quản trị viên (UC-06, UC-07, UC-08, Admin Dashboard, kèm Xem lại & Khôi phục dữ liệu đã xóa mềm) và phân hệ Tài xế (UC-01 đến UC-05, UC-09, chạy song song nhận diện vật cản + nhận diện biển báo thật `best.pt`, lưu ảnh snapshot, lọc loại xe, tách kênh âm thanh + cooldown chống lặp biển báo, phân trang) đã được triển khai.

---

## 1. Mục Lục
1. [Tổng quan dự án](#2-tổng-quan-dự-án)
2. [Phạm vi triển khai & Phạm vi lược bỏ](#3-phạm-vi-triển-khai--phạm-vi-lược-bỏ)
3. [Thông số mô hình AI & Xử lý thời gian thực](#4-thông-số-mô-hình-ai--xử-lý-thời-gian-thực)
4. [Các thay đổi so với thiết kế ban đầu](#5-các-thay-đổi-so-với-thiết-kế-ban-đầu)
5. [Định hướng phát triển sau đồ án](#6-định-hướng-phát-triển-sau-đồ-án)

---

## 2. Tổng Quan Dự Án

* **Tên dự án:** SmartDashcam – Hệ thống Trợ lý Lái xe Thông minh (ADAS Local Prototype).
* **Mục tiêu cốt lõi:** Hỗ trợ tài xế quan sát đường bộ theo thời gian thực qua 2 nhiệm vụ chính chạy song song:
  1. **Nhận diện biển báo giao thông Việt Nam** (56 phân lớp từ mô hình `best.pt` đã huấn luyện và tích hợp).
  2. **Phát hiện vật cản và cảnh báo nguy cơ va chạm** gần xe (ô tô, xe máy, xe tải, xe buýt, người đi bộ, động vật và ngoại lệ vật thể quá lớn).
* **Mô hình triển khai:** Local Prototype tích hợp sẵn 2 phân hệ giao diện (**Tài xế** `role = 1` và **Quản trị viên** `role = 0`) trên cùng một ứng dụng chạy cục bộ, tự động điều hướng theo phân quyền sau khi đăng nhập để thuận tiện cho việc demo, hiệu chỉnh danh mục biển báo và kiểm thử model AI trực tiếp.
* **Tình trạng mô hình huấn luyện:** Mô hình nhận diện biển báo `best.pt` (56 lớp nhãn từ `0` đến `55`) đã được tiếp nhận, trích xuất danh sách lớp, nạp đủ 56 biển báo vào SQLite (dùng mã dấu gạch ngang `-`) và tích hợp chạy thật trên FastAPI AI Service.

---

## 3. Phạm Vi Triển Khai & Phạm Vi Lược Bỏ

### 3.1. Phạm vi đã triển khai (Đủ 9 Use Case + Admin Dashboard)
* **Xác thực:** UC-01 (Đăng nhập), UC-02 (Đăng ký).
* **Phân hệ Tài xế:**
  * UC-03 (Giám sát lái xe trực tiếp HUD song song vật cản + biển báo thật + lưu snapshot + lọc loại xe + tách kênh âm thanh còi/TTS + cooldown chống lặp biển báo).
  * UC-04 (Quản lý lịch sử cảnh báo kèm xem ảnh snapshot & phân trang; không áp dụng khôi phục xóa mềm).
  * UC-05 (Quản lý cài đặt cá nhân & đồng bộ nóng sang AI Service).
  * UC-09 (Đổi mật khẩu tài khoản Tài xế đặt gọn trong `/driver/settings`, xác thực mật khẩu cũ và tự động bắt đăng nhập lại).
* **Phân hệ Quản trị viên:**
  * Admin Dashboard (nối CSDL thật + ping FastAPI).
  * UC-06 (Quản lý 56 biển báo + tự động làm mới RAM Cache + phân trang + xem lại & khôi phục xóa mềm).
  * UC-07 (Upload & Local Hot-Reload Model AI kèm SHA-256, Dummy Inference, Rollback + xem lại & khôi phục xóa mềm).
  * UC-08 (Quản lý tài khoản người dùng + xem lại & khôi phục cả `User` và `UserSetting` đã xóa mềm).

### 3.2. Phạm vi đã lược bỏ (Đã thống nhất)
* Không triển khai quản lý chuyến đi (`trips`).
* Không lưu lịch sử từng lần nhận diện biển báo (`sign_detections`) — nhận diện biển báo chạy qua RAM Cache.
* Không làm bản đồ biển báo GPS (`verified_map_signs`).
* Không thu thập dữ liệu phản hồi huấn luyện (`dataset_feedbacks`).
* Không tra cứu mức phạt (`penalty_info`).
* Không triển khai xem lại & khôi phục bản ghi đã xóa mềm cho Lịch sử cảnh báo (`/driver/history`).

### 3.3. Hạng mục tạm hoãn / Tùy chọn mở rộng
* **Kết nối camera ngoài:** Giữ nguyên luồng webcam trình duyệt và video mẫu `.mp4` để demo/kiểm thử.
* **Bộ ảnh icon PNG cho 56 biển báo:** Chưa bổ sung vào `web_app/views/static/sign_icons/` (tùy chọn nếu cần cho demo).
* **Tối ưu FPS trên CPU:** Tùy chọn chạy `sign_detector` cách nhịp 2–3 frame/lần nếu chạy video mẫu bị giật.

---

## 4. Thông Số Mô Hình AI & Xử Lý Thời Gian Thực

| Nhiệm vụ | Mô hình & Thuật toán | Hiệu suất / Nguồn dữ liệu | Cơ chế vận hành thực tế |
| :--- | :--- | :--- | :--- |
| **Nhận diện biển báo** | `YOLOv11n` (`best.pt` thật, tự nạp bản `is_active = 1` khi khởi động, hỗ trợ Hot-Reload) | Tập `vietnam-traffic-sign-altsi` (9,635 ảnh, 56 lớp nhãn `0–55`). `mAP@50 = 97.9%`, `Precision = 95.2%`, `Recall = 95.8%`. | Nạp 56 biển báo từ SQLite lên **RAM Cache** (tự làm mới khi Admin thêm/sửa/xóa/khôi phục UC-06); không ghi DB. Lọc theo `user_settings.vehicle_type` (biển khác loại xe chỉ báo 1 lần kèm nhãn `Khác loại xe`, tắt TTS, rồi bỏ qua). Trên HUD chỉ phát **giọng nói TTS** (tắt khi đang `CRITICAL`) kèm cooldown chống lặp (`W-`: 10s, nhóm khác: 25s, biến mất tối thiểu 4s). |
| **Phát hiện vật cản** | `YOLOv11n (COCO)` (`yolo11n.pt`) + `ByteTrack` | Chạy song song cùng `SignDetector` trên RAM trong `/ws/detect`. | Lọc theo khung ROI (`x: 15%–85%`, `y: 50%–95%`) + ngoại lệ vật thể quá lớn (`>= 35%` khung hình hoặc `>= 45%` ROI ép `CRITICAL`). Trên HUD chỉ phát **còi cảnh báo** (`WARNING` bíp đơn 1800ms, `CRITICAL` bíp đôi 700ms và ngắt ngay TTS). Khi đạt `WARNING`/`CRITICAL` (cooldown 5s, vượt cooldown khi tăng mức `WARNING -> CRITICAL`), vẽ khung vật thể nguy hiểm và lưu ảnh `.jpg` vào `storage/snapshots/` trên luồng nền rồi ghi DB. |

---

## 5. Các Thay Đổi So Với Thiết Kế Ban Đầu

| Hạng mục | Thiết kế ban đầu | Thực tế đã chốt / triển khai | Lý do thay đổi |
| :--- | :--- | :--- | :--- |
| **Hệ quản trị CSDL** | SQL Server | **SQLite** (`smartdashcam.db`) + **SQLAlchemy 2.0 ORM** | Gọn nhẹ, dành tối đa RAM/CPU cho 2 model AI chạy cục bộ; dễ nâng cấp lên PostgreSQL/SQL Server sau này. |
| **Framework Web** | Chưa chốt | **Flask** (Blueprint, Jinja2, session) | Đã cài đặt và triển khai ổn định. |
| **Cổng Web App (`WEB_PORT`)** | `5000` → `8080` | **`8000`** (`http://127.0.0.1:8000`) | Cổng `5000` bị Windows chặn (`WinError 10013`); chốt chạy ổn định trên cổng `8000`. |
| **API đồng bộ cấu hình** | `POST /api/v1/config/sync` | **`POST /api/v1/config`** | Đồng bộ `conf_threshold`, `ttc_warning_sec`, `ttc_danger_sec` cho cả `ObstacleTracker` và `SignDetector`, kèm xóa cache `user_settings`. |
| **Định dạng mã biển báo (`sign_code`)** | 4 biển mẫu dùng dấu chấm (`P.102`, `P.127`...) | **56 biển báo dùng dấu gạch ngang (`-`, ví dụ `P-103a`)** | Khớp trực tiếp với 56 lớp nhãn trích xuất từ mô hình `best.pt`; đã xóa mềm 4 bản ghi mẫu cũ. |
| **Hành vi với biển khác loại xe** | Chỉ tắt TTS hoặc bỏ qua hoàn toàn | **Nhận diện đúng 1 lần duy nhất** (gắn nhãn `Khác loại xe`, tắt TTS), sau đó bỏ qua hoàn toàn ở các khung hình sau | Giúp tài xế vẫn nắm thông tin có biển báo 1 lần mà không gây nhiễu khung hình liên tục. |
| **Form Đăng ký (UC-02)** | Nhập thêm loại xe mặc định | Không bắt buộc chọn loại xe lúc đăng ký | Giữ form gọn nhẹ; Backend tự tạo `user_settings` với `vehicle_type = 'car'`. |
| **Âm thanh cảnh báo & Chống lặp HUD** | Phát TTS chung cho cả vật cản và biển báo | **Tách kênh hoàn toàn:** Vật cản chỉ phát còi (`SmartAlertSound`, `CRITICAL` ngắt ngay TTS); Biển báo chỉ đọc TTS (`SmartTTS`) kèm cooldown (`W-` 10s, nhóm khác 25s) và chống lặp dừng xe (4s) | Loại bỏ tình trạng chồng chéo âm thanh khi 2 luồng chạy song song, tăng tốc độ phản xạ khi sắp va chạm và tránh đọc lặp biển báo trên cùng đoạn đường. |
| **Phân trang danh sách** | Chưa có phân trang | **Phân trang phía client (`PAGE_SIZE = 6`)** trên `history.html` và `signs.html` | Rút gọn danh sách dài (54–56+ dòng) mà vẫn giữ nguyên tìm kiếm/lọc nhanh tức thì phía trình duyệt. |
| **Đổi mật khẩu Tài xế (UC-09)** | Chưa có trong đặc tả ban đầu | **Tích hợp gọn thành khối form riêng** trong `/driver/settings` (`POST /driver/settings/change-password`), bắt đăng nhập lại sau khi đổi | Hoàn thiện vòng đời bảo mật tài khoản tài xế mà không làm phình menu điều hướng hay ảnh hưởng form lưu ngưỡng AI. |
| **Xem lại & Khôi phục xóa mềm** | Chỉ có thao tác xóa mềm (`deleted_at`) | **Bổ sung tab `Đang hoạt động` / `Đã xóa mềm` & nút Khôi phục** cho 3 phân hệ Admin (`users`, `signs`, `models`); lược bỏ cho `/driver/history` | Giúp Admin phục hồi an toàn dữ liệu xóa nhầm (tài khoản + cài đặt, biển báo + AI Cache, phiên bản model). |

---

## 6. Định Hướng Phát Triển Sau Đồ Án
* Tách phân hệ `ADMIN` thành Web Admin Portal chạy trên máy chủ riêng; thiết bị gắn trên xe chỉ chạy Client cho `DRIVER`.
* Chuyển đổi chuỗi kết nối SQLAlchemy từ SQLite sang PostgreSQL/SQL Server mà không cần sửa logic nghiệp vụ.
* Bổ sung đồng bộ danh mục biển báo và cập nhật model qua mạng (OTA) khi có Wi-Fi/4G.