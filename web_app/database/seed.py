from sqlalchemy import select
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash

from web_app.config import Config
from web_app.models import (
    User,
    UserSetting,
    TrafficSignCategory,
    TrafficSignCatalog,
    TrafficSignVehicle,
)

DEFAULT_CATEGORIES = [
    {"code": "CAM", "name": "Biển báo cấm", "description": "Biểu thị các điều cấm đối với người tham gia giao thông."},
    {"code": "NGUY_HIEM", "name": "Biển báo nguy hiểm", "description": "Cảnh báo các tình huống nguy hiểm phía trước."},
    {"code": "HIEU_LENH", "name": "Biển hiệu lệnh", "description": "Báo các hiệu lệnh bắt buộc phải thi hành."},
    {"code": "CHI_DAN", "name": "Biển chỉ dẫn", "description": "Chỉ dẫn hướng đi hoặc các thông tin cần thiết."},
]

# 4 mã mẫu cũ dùng dấu chấm cần xóa mềm khi chuyển sang bộ 56 mã chuẩn của best.pt
LEGACY_SIGN_CODES = ("P.102", "P.127", "W.224", "R.301a")

# Đủ 56 lớp biển báo khớp 100% với model best.pt (0 -> 55)
DEFAULT_SIGNS = [
    # --- BIỂN BÁO CẤM (23 biển) ---
    {
        "category_code": "CAM",
        "sign_code": "DP-135",
        "name": "Hết tất cả các lệnh cấm",
        "tts_script": "Đã hết tất cả các lệnh cấm",
        "icon_url": None,
        "priority": 1,
        "vehicles": ["all"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-102",
        "name": "Cấm đi ngược chiều",
        "tts_script": "Phía trước có biển cấm đi ngược chiều",
        "icon_url": None,
        "priority": 3,
        "vehicles": ["all"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-103a",
        "name": "Cấm xe ô tô",
        "tts_script": "Phía trước cấm xe ô tô",
        "icon_url": None,
        "priority": 3,
        "vehicles": ["car", "truck", "bus"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-103b",
        "name": "Cấm xe ô tô rẽ phải",
        "tts_script": "Phía trước cấm xe ô tô rẽ phải",
        "icon_url": None,
        "priority": 3,
        "vehicles": ["car", "truck", "bus"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-103c",
        "name": "Cấm xe ô tô rẽ trái",
        "tts_script": "Phía trước cấm xe ô tô rẽ trái",
        "icon_url": None,
        "priority": 3,
        "vehicles": ["car", "truck", "bus"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-104",
        "name": "Cấm xe máy",
        "tts_script": "Phía trước cấm xe máy",
        "icon_url": None,
        "priority": 3,
        "vehicles": ["motorbike"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-106a",
        "name": "Cấm xe ô tô tải",
        "tts_script": "Phía trước cấm xe ô tô tải",
        "icon_url": None,
        "priority": 3,
        "vehicles": ["truck"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-106b",
        "name": "Cấm xe ô tô tải vượt quá trọng tải quy định",
        "tts_script": "Phía trước cấm xe tải vượt quá trọng tải quy định",
        "icon_url": None,
        "priority": 3,
        "vehicles": ["truck"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-107a",
        "name": "Cấm xe ô tô khách",
        "tts_script": "Phía trước cấm xe ô tô khách",
        "icon_url": None,
        "priority": 3,
        "vehicles": ["bus"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-112",
        "name": "Cấm người đi bộ",
        "tts_script": "Phía trước có biển cấm người đi bộ",
        "icon_url": None,
        "priority": 1,
        "vehicles": ["all"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-115",
        "name": "Hạn chế trọng tải toàn bộ xe",
        "tts_script": "Chú ý biển hạn chế trọng tải toàn bộ xe phía trước",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["truck", "bus"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-117",
        "name": "Hạn chế chiều cao",
        "tts_script": "Chú ý biển hạn chế chiều cao phía trước",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["truck", "bus"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-123a",
        "name": "Cấm rẽ trái",
        "tts_script": "Phía trước cấm rẽ trái",
        "icon_url": None,
        "priority": 3,
        "vehicles": ["all"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-123b",
        "name": "Cấm rẽ phải",
        "tts_script": "Phía trước cấm rẽ phải",
        "icon_url": None,
        "priority": 3,
        "vehicles": ["all"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-124a",
        "name": "Cấm quay đầu xe",
        "tts_script": "Phía trước cấm quay đầu xe",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-124b",
        "name": "Cấm xe ô tô quay đầu xe",
        "tts_script": "Phía trước cấm xe ô tô quay đầu",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["car", "truck", "bus"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-124c",
        "name": "Cấm rẽ trái và quay đầu xe",
        "tts_script": "Phía trước cấm rẽ trái và quay đầu xe",
        "icon_url": None,
        "priority": 3,
        "vehicles": ["all"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-127",
        "name": "Tốc độ tối đa cho phép",
        "tts_script": "Chú ý giới hạn tốc độ tối đa phía trước",
        "icon_url": None,
        "priority": 3,
        "vehicles": ["all"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-128",
        "name": "Cấm sử dụng còi",
        "tts_script": "Khu vực cấm sử dụng còi",
        "icon_url": None,
        "priority": 1,
        "vehicles": ["all"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-130",
        "name": "Cấm dừng xe và đỗ xe",
        "tts_script": "Khu vực cấm dừng xe và đỗ xe",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-131a",
        "name": "Cấm đỗ xe",
        "tts_script": "Khu vực cấm đỗ xe",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-137",
        "name": "Cấm rẽ trái và rẽ phải",
        "tts_script": "Phía trước cấm rẽ trái và rẽ phải",
        "icon_url": None,
        "priority": 3,
        "vehicles": ["all"],
    },
    {
        "category_code": "CAM",
        "sign_code": "P-245a",
        "name": "Đi chậm",
        "tts_script": "Vui lòng giảm tốc độ, đi chậm phía trước",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    # --- BIỂN HIỆU LỆNH (6 biển) ---
    {
        "category_code": "HIEU_LENH",
        "sign_code": "R-301c",
        "name": "Các xe chỉ được rẽ phải",
        "tts_script": "Các xe chỉ được rẽ phải",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "HIEU_LENH",
        "sign_code": "R-301d",
        "name": "Các xe chỉ được rẽ phải (trước ngã rẽ)",
        "tts_script": "Phía trước các xe chỉ được rẽ phải",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "HIEU_LENH",
        "sign_code": "R-301e",
        "name": "Các xe chỉ được rẽ trái (trước ngã rẽ)",
        "tts_script": "Phía trước các xe chỉ được rẽ trái",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "HIEU_LENH",
        "sign_code": "R-302a",
        "name": "Hướng phải đi vòng chướng ngại vật sang phải",
        "tts_script": "Đi vòng chướng ngại vật sang bên phải",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "HIEU_LENH",
        "sign_code": "R-302b",
        "name": "Hướng phải đi vòng chướng ngại vật sang trái",
        "tts_script": "Đi vòng chướng ngại vật sang bên trái",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "HIEU_LENH",
        "sign_code": "R-303",
        "name": "Nơi giao nhau chạy theo vòng xuyến",
        "tts_script": "Phía trước có vòng xuyến, chú ý giảm tốc độ",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    # --- BIỂN CHỈ DẪN & BIỂN PHỤ (5 biển) ---
    {
        "category_code": "CHI_DAN",
        "sign_code": "R-407a",
        "name": "Đường một chiều",
        "tts_script": "Đường một chiều phía trước",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "CHI_DAN",
        "sign_code": "R-409",
        "name": "Chỗ quay xe",
        "tts_script": "Phía trước có chỗ quay xe",
        "icon_url": None,
        "priority": 1,
        "vehicles": ["all"],
    },
    {
        "category_code": "CHI_DAN",
        "sign_code": "R-425",
        "name": "Bệnh viện",
        "tts_script": "Phía trước có bệnh viện, chú ý giảm tốc độ",
        "icon_url": None,
        "priority": 1,
        "vehicles": ["all"],
    },
    {
        "category_code": "CHI_DAN",
        "sign_code": "R-434",
        "name": "Bến xe buýt",
        "tts_script": "Phía trước có bến xe buýt",
        "icon_url": None,
        "priority": 1,
        "vehicles": ["all"],
    },
    {
        "category_code": "CHI_DAN",
        "sign_code": "S-509a",
        "name": "Biển phụ thuyết minh",
        "tts_script": "Chú ý biển phụ hướng dẫn phía trước",
        "icon_url": None,
        "priority": 1,
        "vehicles": ["all"],
    },
    # --- BIỂN BÁO NGUY HIỂM (22 biển) ---
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-201a",
        "name": "Chỗ ngoặt nguy hiểm vòng bên trái",
        "tts_script": "Chú ý chỗ ngoặt nguy hiểm vòng sang trái phía trước",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-201b",
        "name": "Chỗ ngoặt nguy hiểm vòng bên phải",
        "tts_script": "Chú ý chỗ ngoặt nguy hiểm vòng sang phải phía trước",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-202a",
        "name": "Nhiều chỗ ngoặt nguy hiểm liên tiếp (trái trước)",
        "tts_script": "Chú ý nhiều chỗ ngoặt nguy hiểm liên tiếp phía trước",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-202b",
        "name": "Nhiều chỗ ngoặt nguy hiểm liên tiếp (phải trước)",
        "tts_script": "Chú ý nhiều chỗ ngoặt nguy hiểm liên tiếp phía trước",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-203b",
        "name": "Đường bị thu hẹp về phía trái",
        "tts_script": "Chú ý đường bị thu hẹp về phía trái",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-203c",
        "name": "Đường bị thu hẹp về phía phải",
        "tts_script": "Chú ý đường bị thu hẹp về phía phải",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-205a",
        "name": "Đường giao nhau (ngã tư)",
        "tts_script": "Phía trước có ngã tư đường giao nhau",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-205b",
        "name": "Đường giao nhau (ngã ba bên phải)",
        "tts_script": "Phía trước có ngã ba giao nhau bên phải",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-205d",
        "name": "Đường giao nhau (ngã ba chữ T)",
        "tts_script": "Phía trước có ngã ba chữ T",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-207a",
        "name": "Giao nhau với đường không ưu tiên",
        "tts_script": "Phía trước giao nhau với đường không ưu tiên",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-207b",
        "name": "Giao nhau với đường không ưu tiên bên phải",
        "tts_script": "Phía trước giao nhau với đường không ưu tiên bên phải",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-207c",
        "name": "Giao nhau với đường không ưu tiên bên trái",
        "tts_script": "Phía trước giao nhau với đường không ưu tiên bên trái",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-208",
        "name": "Giao nhau với đường ưu tiên",
        "tts_script": "Chú ý giao nhau với đường ưu tiên, nhường đường",
        "icon_url": None,
        "priority": 3,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-209",
        "name": "Giao nhau có tín hiệu đèn",
        "tts_script": "Phía trước có giao lộ đèn tín hiệu",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-210",
        "name": "Giao nhau với đường sắt có rào chắn",
        "tts_script": "Cảnh báo giao nhau với đường sắt có rào chắn phía trước",
        "icon_url": None,
        "priority": 3,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-219",
        "name": "Dốc xuống nguy hiểm",
        "tts_script": "Cảnh báo dốc xuống nguy hiểm phía trước",
        "icon_url": None,
        "priority": 3,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-224",
        "name": "Đường người đi bộ cắt ngang",
        "tts_script": "Chú ý đường người đi bộ cắt ngang phía trước",
        "icon_url": None,
        "priority": 3,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-225",
        "name": "Trẻ em",
        "tts_script": "Chú ý khu vực có trẻ em qua đường phía trước",
        "icon_url": None,
        "priority": 3,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-227",
        "name": "Công trường",
        "tts_script": "Chú ý phía trước có công trường đang thi công",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-233",
        "name": "Nguy hiểm khác",
        "tts_script": "Chú ý nguy hiểm phía trước",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-235",
        "name": "Đường đôi",
        "tts_script": "Phía trước bắt đầu đoạn đường đôi",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
    {
        "category_code": "NGUY_HIEM",
        "sign_code": "W-245a",
        "name": "Đi chậm",
        "tts_script": "Chú ý giảm tốc độ, đi chậm phía trước",
        "icon_url": None,
        "priority": 2,
        "vehicles": ["all"],
    },
]


def seed_admin(db: Session) -> None:
    existing = db.scalar(select(User).where(User.email == Config.ADMIN_EMAIL))
    if existing:
        return

    admin = User(
        email=Config.ADMIN_EMAIL,
        password_hash=generate_password_hash(Config.ADMIN_PASSWORD),
        full_name="Quản trị viên Hệ thống",
        role=0,  # 0: Admin
        is_active=True,
    )
    db.add(admin)
    db.flush()

    db.add(UserSetting(user_id=admin.id))


def seed_signs(db: Session) -> None:
    category_map: dict[str, int] = {}

    for cat_data in DEFAULT_CATEGORIES:
        cat = db.scalar(
            select(TrafficSignCategory).where(TrafficSignCategory.code == cat_data["code"])
        )
        if not cat:
            cat = TrafficSignCategory(**cat_data)
            db.add(cat)
            db.flush()
        category_map[cat.code] = cat.id

    # Xóa mềm 4 biển mẫu cũ dùng dấu chấm để tránh trùng nghĩa với bộ 56 biển chuẩn
    legacy_signs = db.scalars(
        select(TrafficSignCatalog).where(
            TrafficSignCatalog.sign_code.in_(LEGACY_SIGN_CODES),
            TrafficSignCatalog.deleted_at.is_(None),
        )
    ).all()
    for old_sign in legacy_signs:
        old_sign.soft_delete()
        for v in old_sign.vehicles:
            if v.deleted_at is None:
                v.soft_delete()

    for sign_data in DEFAULT_SIGNS:
        existing_sign = db.scalar(
            select(TrafficSignCatalog).where(TrafficSignCatalog.sign_code == sign_data["sign_code"])
        )
        if existing_sign:
            continue

        sign = TrafficSignCatalog(
            category_id=category_map[sign_data["category_code"]],
            sign_code=sign_data["sign_code"],
            name=sign_data["name"],
            tts_script=sign_data["tts_script"],
            icon_url=sign_data["icon_url"],
            priority=sign_data["priority"],
        )
        db.add(sign)
        db.flush()

        for v_type in sign_data["vehicles"]:
            db.add(TrafficSignVehicle(sign_id=sign.id, vehicle_type=v_type))


def seed_all(db: Session) -> None:
    seed_admin(db)
    seed_signs(db)