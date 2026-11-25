# SmartDashcam – Hệ thống Trợ lý Lái xe Thông minh (ADAS Local Prototype)

Ứng dụng web hỗ trợ tài xế quan sát đường bộ theo thời gian thực qua hai nhiệm vụ AI chạy song song:

1. **Nhận diện biển báo giao thông Việt Nam** (56 lớp từ mô hình `best.pt`, lọc theo loại phương tiện, đọc giọng nói TTS tiếng Việt có cooldown chống lặp).
2. **Phát hiện vật cản và cảnh báo nguy cơ va chạm** (YOLOv11n COCO + ByteTrack + vùng giám sát ROI + ước lượng TTC, phát còi phân cấp và tự động chụp ảnh hiện trường).

Dự án chạy cục bộ (*Local Prototype*), tích hợp hai phân hệ giao diện trên cùng một ứng dụng: **Tài xế (HUD, Lịch sử, Cài đặt)** và **Quản trị viên (Dashboard, Biển báo, Model AI, Tài khoản)**, tự động điều hướng theo phân quyền sau khi đăng nhập.

---

## 1. Kiến trúc hệ thống

Hệ thống gồm **2 dịch vụ tách biệt** với 2 môi trường ảo Python (`.venv`) riêng:

```text
[Trình duyệt (HUD / Admin)] ──(HTTP CRUD & GET /snapshots/...)──> [Flask Web App :8000 (web_app)] ──> [SQLite: smartdashcam.db]
             │                                                                    ▲                               ▲
   (WS /ws/detect?user_id=...)                                            (REST API nội bộ)            (Read-only RAM Cache)
             ▼                                                                    ▼                               │
[FastAPI AI Service :8001 (ai_service)] ◄──────► [Thư mục dùng chung: storage/models/ & storage/snapshots/] ──────┘
```

| Thành phần | Công nghệ | Vai trò chính |
| :--- | :--- | :--- |
| **Web MVC** (`web_app/`, cổng `8000`) | Flask, SQLAlchemy 2.0, SQLite, Bootstrap 5 | Xác thực, phân quyền, toàn bộ thao tác ghi/CRUD, phục vụ ảnh hiện trường, quản lý cài đặt & phân hệ Admin |
| **AI Service** (`ai_service/`, cổng `8001`) | FastAPI, YOLOv11n, ByteTrack, OpenCV | Chạy song song nhận diện biển báo & vật cản, lưu ảnh snapshot nền, kiểm tra SHA-256 & nạp nóng model |
| **Thư mục dùng chung** (`storage/`) | – | Lưu file trọng số `.pt` (`models/`), ảnh chụp hiện trường `.jpg` (`snapshots/`) và CSDL (`database/`) |

> **Nguyên tắc dữ liệu:** Mọi thao tác ghi/CRUD với SQLite đều tập trung tại **Flask Web App**. **FastAPI AI Service** chỉ đọc (*read-only*) để nạp RAM Cache 56 biển báo, tự nạp model đang kích hoạt (`is_active = 1`) và đọc cấu hình `user_settings`; các sự kiện cảnh báo nguy hiểm được gửi về Flask qua API nội bộ `POST /api/internal/alerts`.

---

## 2. Tính năng nổi bật

### Phân hệ Tài xế (`role = 1`)
* **Giám sát trực tiếp (HUD):** Hỗ trợ Webcam hoặc Video mẫu `.mp4`; vẽ đồng thời khung vùng giám sát (ROI), khung vật cản theo mức độ (`SAFE` / `WARNING` / `CRITICAL`) và khung biển báo màu xanh dương.
* **Tách kênh âm thanh chuẩn ADAS:**
  * **Vật cản → Chỉ phát còi** (`Web Audio API`): bíp đơn chậm khi `WARNING` (`1800ms`), bíp đôi dồn dập khi `CRITICAL` (`700ms`) và **ngắt ngay TTS** để ưu tiên cảnh báo khẩn cấp.
  * **Biển báo → Chỉ đọc TTS tiếng Việt** (`Web Speech API`): tự lọc theo loại xe (biển khác loại xe chỉ hiển thị 1 lần kèm nhãn `Khác loại xe` và tắt TTS); áp dụng thời gian hiệu lực (**10 giây** với biển nguy hiểm `W-`, **25 giây** với nhóm khác) kết hợp điều kiện biển biến mất tối thiểu **4 giây** để chống đọc lặp khi dừng đèn đỏ.
* **Lịch sử cảnh báo & Ảnh hiện trường:** Tự động vẽ khung vật thể nguy hiểm và lưu ảnh `.jpg` vào `storage/snapshots/`; hỗ trợ xem phóng to, xem chi tiết vật thể (`alert_objects`), lọc 1 chạm, xóa mềm và phân trang (`6` mục/trang).
* **Cài đặt cá nhân & Bảo mật:** Tùy chỉnh loại xe, ngưỡng độ tin cậy, ngưỡng TTC (kèm 3 preset *Nội thành / Tiêu chuẩn / Cao tốc*), bật/tắt TTS & Còi (đồng bộ nóng sang AI Service) và **Đổi mật khẩu** (tự động đăng xuất bắt đăng nhập lại sau khi đổi).

### Phân hệ Quản trị viên (`role = 0`)
* **Admin Dashboard:** Thống kê KPI thực tế từ SQLite, phân bố 4 nhóm biển báo, danh sách cảnh báo gần đây và kiểm tra trạng thái kết nối trực tiếp của FastAPI AI Service.
* **Quản lý danh mục 56 biển báo:** CRUD đầy đủ kèm nút nghe thử TTS, tìm kiếm/lọc nhóm, phân trang (`6` mục/trang) và **tự động làm mới RAM Cache** trên AI Service ngay khi thêm/sửa/xóa/khôi phục.
* **Quản lý & Nạp nóng Model AI (Hot-Reload):** Tải lên file `.pt`, kiểm tra checksum SHA-256, chạy thử (*Dummy Inference*), nạp nóng không cần khởi động lại server và tự động *Rollback* nếu model lỗi.
* **Quản lý tài khoản & Khôi phục xóa mềm:** CRUD tài khoản người dùng (tự khóa thao tác tự xóa chính mình); hỗ trợ bộ tab **`Đang hoạt động` / `Đã xóa mềm`** và nút **Khôi phục** trên cả 3 phân hệ Admin (`users`, `signs`, `models`).

---

## 3. Cấu trúc thư mục

```text
SmartDashcam/
├── .env, .env.example, .gitignore, README.md
├── requirements_web.txt, requirements_ai.txt
├── run_web.bat, run_ai.bat, yolo11n.pt
├── scripts/
│   ├── init_db.py                # Khởi tạo 8 bảng & nạp dữ liệu mẫu (56 biển báo + Admin)
│   └── test_video_source/        # Video mẫu .mp4 phục vụ demo/kiểm thử
├── storage/
│   ├── database/smartdashcam.db  # CSDL SQLite
│   ├── models/                   # Chứa file trọng số .pt (bao gồm best.pt 56 lớp)
│   └── snapshots/                # Chứa ảnh .jpg chụp hiện trường cảnh báo
├── tests/                        # Unit tests (auth, collision logic, model manager)
├── ai_service/                   # FastAPI: api/, core/, services/, utils/
└── web_app/                      # Flask MVC: database/, models/, controllers/, services/, utils/, views/
```

---

## 4. Yêu cầu & Cài đặt

### Yêu cầu môi trường
* **Python:** `3.10 – 3.12`
* **Hệ điều hành:** Windows (các lệnh bên dưới sử dụng Windows PowerShell)

### Các bước cài đặt

```powershell
# 1. Tạo môi trường ảo riêng cho từng dịch vụ
python -m venv web_app\.venv
python -m venv ai_service\.venv

# 2. Cài thư viện cho Web App (Flask)
web_app\.venv\Scripts\Activate.ps1
pip install -r requirements_web.txt
deactivate

# 3. Cài thư viện cho AI Service (FastAPI + YOLOv11)
ai_service\.venv\Scripts\Activate.ps1
pip install -r requirements_ai.txt
deactivate

# 4. Tạo file cấu hình môi trường
Copy-Item .env.example .env
```

Mở file `.env` và kiểm tra/điền các biến cấu hình chính (`SECRET_KEY`, mật khẩu Admin mặc định, cổng kết nối):

```env
WEB_HOST=127.0.0.1
WEB_PORT=8000
WEB_APP_URL=http://127.0.0.1:8000

AI_HOST=127.0.0.1
AI_PORT=8001
AI_SERVICE_URL=http://127.0.0.1:8001

DATABASE_URL=sqlite:///storage/database/smartdashcam.db
MODELS_DIR=storage/models
SNAPSHOTS_DIR=storage/snapshots
```

---

## 5. Khởi tạo cơ sở dữ liệu

```powershell
web_app\.venv\Scripts\Activate.ps1
python scripts\init_db.py
```

Lệnh này khởi tạo `storage/database/smartdashcam.db` gồm **8 bảng** (`users`, `user_settings`, `collision_alerts`, `alert_objects`, `ai_models`, `traffic_sign_categories`, `traffic_sign_catalog`, `traffic_sign_vehicles`) kèm dữ liệu mặc định gồm 56 biển báo giao thông Việt Nam và tài khoản Admin (`role = 0`).

---

## 6. Chạy ứng dụng

Mở **hai cửa sổ PowerShell** riêng biệt (hoặc chạy trực tiếp `run_ai.bat` và `run_web.bat`):

**Cửa sổ 1 – FastAPI AI Service (cổng `8001`)**
```powershell
ai_service\.venv\Scripts\Activate.ps1
uvicorn ai_service.main:app --host 127.0.0.1 --port 8001
```

**Cửa sổ 2 – Flask Web App (cổng `8000`)**
```powershell
web_app\.venv\Scripts\Activate.ps1
python -m web_app.main
```

Sau khi cả hai dịch vụ khởi chạy thành công, mở trình duyệt tại **`http://127.0.0.1:8000`**.

---

## 7. Mô hình AI

Đặt các file trọng số `.pt` vào thư mục `storage/models/` (hoặc tải trực tiếp từ giao diện Admin):

| Mô hình | Nhiệm vụ | Chi tiết |
| :--- | :--- | :--- |
| `best.pt` | Nhận diện 56 biển báo Việt Nam (`YOLOv11n`) | Huấn luyện trên tập `vietnam-traffic-sign-altsi` (`mAP@50 = 97.9%`); mã lớp dùng dấu gạch ngang (ví dụ `P-103a`) khớp với `traffic_sign_catalog.sign_code`. |
| `yolo11n.pt` | Phát hiện & theo dõi vật cản (`COCO`) | Chạy song song cùng `ByteTrack`, lọc theo vùng ROI và ngoại lệ vật thể quá lớn (`>= 35%` khung hình hoặc `>= 45%` ROI ép `CRITICAL`). |

---

## 8. Hợp đồng giao tiếp (API nội bộ)

| Giao thức & Endpoint | Chiều gọi | Chức năng |
| :--- | :--- | :--- |
| `WS /ws/detect?user_id=<id>` | Trình duyệt ↔ FastAPI | Truyền khung hình JPEG, nhận đồng thời kết quả vật cản, ROI, mức cảnh báo và biển báo |
| `POST /api/v1/config` | Flask → FastAPI | Cập nhật nóng ngưỡng `conf_threshold`, `ttc_warning_sec`, `ttc_danger_sec` và xóa cache cấu hình |
| `POST /api/v1/signs/reload-cache` | Flask → FastAPI | Tự động nạp lại RAM Cache biển báo khi Admin thêm, sửa, xóa mềm hoặc khôi phục ở UC-06 |
| `POST /api/v1/models/reload` | Flask → FastAPI | Kiểm tra SHA-256, chạy thử (Dummy Inference), nạp nóng model mới và tự động Rollback nếu lỗi |
| `GET /api/v1/health` | Flask → FastAPI | Kiểm tra trạng thái sống của AI Service (hiển thị trên Admin Dashboard) |
| `POST /api/internal/alerts` | FastAPI → Flask | Gửi sự kiện cảnh báo kèm tên ảnh snapshot đã lưu để ghi vào SQLite |
| `GET /snapshots/<path:filename>` | Trình duyệt → Flask | Phục vụ ảnh chụp hiện trường từ `storage/snapshots/` (có kiểm tra phiên đăng nhập) |

---

## 9. Danh sách Use Case

| Mã UC | Tên chức năng | Vai trò |
| :--- | :--- | :--- |
| **UC-01** | Đăng nhập hệ thống | Tất cả |
| **UC-02** | Đăng ký tài khoản | Tài xế |
| **UC-03** | Giám sát lái xe trực tiếp (HUD) | Tài xế |
| **UC-04** | Quản lý lịch sử cảnh báo | Tài xế |
| **UC-05** | Quản lý cài đặt cá nhân | Tài xế |
| **UC-06** | Quản lý danh mục biển báo *(kèm xem lại & khôi phục xóa mềm)* | Admin |
| **UC-07** | Cập nhật Model AI – Local Hot-Reload *(kèm xem lại & khôi phục xóa mềm)* | Admin |
| **UC-08** | Quản lý tài khoản người dùng *(kèm xem lại & khôi phục xóa mềm)* | Admin |
| **UC-09** | Đổi mật khẩu tài khoản *(tích hợp trong `/driver/settings`, tự đăng xuất sau khi đổi)* | Tài xế |
| *(Bổ sung)* | **Admin Dashboard** (`/admin/dashboard`) | Admin |

---

## 10. Quy ước Cơ sở dữ liệu

* **SQLite + SQLAlchemy 2.0 ORM** với 8 bảng nghiệp vụ.
* Bật `PRAGMA foreign_keys = ON` và `PRAGMA journal_mode = WAL` khi khởi tạo engine.
* Áp dụng **xóa mềm** toàn bộ bảng qua cột `deleted_at` (mặc định lọc `deleted_at IS NULL`; hỗ trợ xem lại & khôi phục bản ghi đã xóa mềm ở 3 phân hệ Admin).
* Phân quyền số nguyên: `0` = Admin, `1` = Tài xế (`Driver`).

---

## 11. Định hướng phát triển

* Tách phân hệ Quản trị viên thành Web Admin Portal chạy trên máy chủ riêng; thiết bị trên xe chỉ chạy Client cho Tài xế.
* Chuyển đổi chuỗi kết nối SQLAlchemy từ SQLite sang PostgreSQL/SQL Server mà không cần sửa logic nghiệp vụ.
* Bổ sung đồng bộ danh mục biển báo và cập nhật mô hình AI qua mạng (OTA) khi có kết nối Wi-Fi/4G.