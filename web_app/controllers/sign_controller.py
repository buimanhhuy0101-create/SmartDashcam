import requests
from web_app.config import Config
from flask import Blueprint, flash, redirect, render_template, request
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from web_app.database.connection import active_select, get_db
from web_app.models.sign_catalog import TrafficSignCatalog
from web_app.models.sign_category import TrafficSignCategory
from web_app.models.sign_vehicle import TrafficSignVehicle
from web_app.utils.decorators import role_required

sign_bp = Blueprint("sign", __name__)

VALID_VEHICLES = ("car", "motorbike", "truck", "bus")
def _sync_sign_cache_to_ai() -> None:
    """Báo FastAPI AI Service làm mới RAM Cache biển báo sau khi Admin cập nhật CSDL."""
    url = f"{Config.AI_SERVICE_URL.rstrip('/')}/api/v1/signs/reload-cache"
    try:
        requests.post(url, timeout=2.0)
    except requests.RequestException:
        pass

def _extract_selected_vehicles(sign: TrafficSignCatalog) -> list[str]:
    """Lấy danh sách phương tiện áp dụng từ ORM để hiển thị đúng checkbox trên form."""
    types = [v.vehicle_type for v in sign.vehicles if v.deleted_at is None]
    if "all" in types:
        return list(VALID_VEHICLES)
    return [t for t in types if t in VALID_VEHICLES]


def _parse_vehicle_types(raw_list: list[str]) -> list[str]:
    """Lọc trùng và chỉ giữ các loại phương tiện hợp lệ."""
    seen = set()
    result = []
    for item in raw_list:
        val = (item or "").strip().lower()
        if val in VALID_VEHICLES and val not in seen:
            seen.add(val)
            result.append(val)
    return result


@sign_bp.route("/admin/signs", methods=["GET"])
@role_required(0)
def admin_signs():
    status = (request.args.get("status") or "active").strip().lower()
    if status not in ("active", "deleted"):
        status = "active"

    with get_db() as db:
        active_count = db.scalar(
            select(func.count(TrafficSignCatalog.id)).where(
                TrafficSignCatalog.deleted_at.is_(None)
            )
        ) or 0
        deleted_count = db.scalar(
            select(func.count(TrafficSignCatalog.id)).where(
                TrafficSignCatalog.deleted_at.is_not(None)
            )
        ) or 0

        if status == "deleted":
            signs = (
                db.execute(
                    select(TrafficSignCatalog)
                    .options(joinedload(TrafficSignCatalog.category))
                    .where(TrafficSignCatalog.deleted_at.is_not(None))
                    .order_by(TrafficSignCatalog.deleted_at.desc())
                )
                .unique()
                .scalars()
                .all()
            )
        else:
            signs = (
                db.execute(
                    active_select(TrafficSignCatalog)
                    .options(joinedload(TrafficSignCatalog.category))
                    .order_by(TrafficSignCatalog.id.desc())
                )
                .unique()
                .scalars()
                .all()
            )

        categories = (
            db.execute(
                active_select(TrafficSignCategory).order_by(TrafficSignCategory.id.asc())
            )
            .scalars()
            .all()
        )
        return render_template(
            "admin/signs.html",
            signs=signs,
            categories=categories,
            status=status,
            active_count=active_count,
            deleted_count=deleted_count,
        )


@sign_bp.route("/admin/signs/new", methods=["GET", "POST"])
@role_required(0)
def admin_sign_create():
    with get_db() as db:
        categories = (
            db.execute(
                active_select(TrafficSignCategory).order_by(TrafficSignCategory.id.asc())
            )
            .scalars()
            .all()
        )

        if request.method == "POST":
            sign_code = (request.form.get("sign_code") or "").strip()
            name = (request.form.get("name") or "").strip()
            tts_script = (request.form.get("tts_script") or "").strip()
            icon_url = (request.form.get("icon_url") or "").strip() or None
            category_id_raw = (request.form.get("category_id") or "").strip()
            priority_raw = (request.form.get("priority") or "1").strip()
            vehicle_types = _parse_vehicle_types(request.form.getlist("vehicle_types"))

            # Kiểm tra dữ liệu bắt buộc
            if not sign_code or not name or not tts_script or not category_id_raw:
                flash("Vui lòng điền đầy đủ Mã biển báo, Nhóm, Tên và Kịch bản TTS.", "warning")
                return render_template(
                    "admin/sign_form.html",
                    sign=None,
                    categories=categories,
                    selected_vehicles=vehicle_types or list(VALID_VEHICLES),
                )

            try:
                category_id = int(category_id_raw)
                priority = max(1, min(3, int(priority_raw)))
            except ValueError:
                flash("Nhóm biển báo hoặc mức ưu tiên không hợp lệ.", "danger")
                return render_template(
                    "admin/sign_form.html",
                    sign=None,
                    categories=categories,
                    selected_vehicles=vehicle_types or list(VALID_VEHICLES),
                )

            # Kiểm tra nhóm biển báo có tồn tại (chưa xóa mềm)
            category = db.execute(
                active_select(TrafficSignCategory).where(TrafficSignCategory.id == category_id)
            ).scalar_one_or_none()
            if not category:
                flash("Nhóm biển báo không tồn tại.", "danger")
                return render_template(
                    "admin/sign_form.html",
                    sign=None,
                    categories=categories,
                    selected_vehicles=vehicle_types or list(VALID_VEHICLES),
                )

            # Kiểm tra trùng sign_code trên toàn bảng (kể cả bản ghi đã xóa mềm vì cột UNIQUE)
            existing = db.execute(
                select(TrafficSignCatalog).where(TrafficSignCatalog.sign_code == sign_code)
            ).scalar_one_or_none()
            if existing:
                if existing.deleted_at is not None:
                    flash(f"Mã biển báo '{sign_code}' đã tồn tại trong dữ liệu đã xóa mềm.", "warning")
                else:
                    flash(f"Mã biển báo '{sign_code}' đã tồn tại.", "warning")
                return render_template(
                    "admin/sign_form.html",
                    sign=None,
                    categories=categories,
                    selected_vehicles=vehicle_types or list(VALID_VEHICLES),
                )

            new_sign = TrafficSignCatalog(
                category_id=category_id,
                sign_code=sign_code,
                name=name,
                tts_script=tts_script,
                icon_url=icon_url,
                priority=priority,
            )
            for vt in vehicle_types:
                new_sign.vehicles.append(TrafficSignVehicle(vehicle_type=vt))

            db.add(new_sign)
            db.commit()
            _sync_sign_cache_to_ai()
            flash(f"Đã thêm biển báo '{sign_code}' thành công.", "success")
            return redirect("/admin/signs")

        return render_template(
            "admin/sign_form.html",
            sign=None,
            categories=categories,
            selected_vehicles=list(VALID_VEHICLES),
        )


@sign_bp.route("/admin/signs/<int:sign_id>/edit", methods=["GET", "POST"])
@role_required(0)
def admin_sign_edit(sign_id: int):
    with get_db() as db:
        sign = (
            db.execute(
                active_select(TrafficSignCatalog)
                .options(joinedload(TrafficSignCatalog.vehicles))
                .where(TrafficSignCatalog.id == sign_id)
            )
            .unique()
            .scalar_one_or_none()
        )
        if not sign:
            flash("Không tìm thấy biển báo cần chỉnh sửa.", "warning")
            return redirect("/admin/signs")

        categories = (
            db.execute(
                active_select(TrafficSignCategory).order_by(TrafficSignCategory.id.asc())
            )
            .scalars()
            .all()
        )

        if request.method == "POST":
            sign_code = (request.form.get("sign_code") or "").strip()
            name = (request.form.get("name") or "").strip()
            tts_script = (request.form.get("tts_script") or "").strip()
            icon_url = (request.form.get("icon_url") or "").strip() or None
            category_id_raw = (request.form.get("category_id") or "").strip()
            priority_raw = (request.form.get("priority") or "1").strip()
            vehicle_types = _parse_vehicle_types(request.form.getlist("vehicle_types"))

            if not sign_code or not name or not tts_script or not category_id_raw:
                flash("Vui lòng điền đầy đủ Mã biển báo, Nhóm, Tên và Kịch bản TTS.", "warning")
                return render_template(
                    "admin/sign_form.html",
                    sign=sign,
                    categories=categories,
                    selected_vehicles=vehicle_types,
                )

            try:
                category_id = int(category_id_raw)
                priority = max(1, min(3, int(priority_raw)))
            except ValueError:
                flash("Nhóm biển báo hoặc mức ưu tiên không hợp lệ.", "danger")
                return render_template(
                    "admin/sign_form.html",
                    sign=sign,
                    categories=categories,
                    selected_vehicles=vehicle_types,
                )

            category = db.execute(
                active_select(TrafficSignCategory).where(TrafficSignCategory.id == category_id)
            ).scalar_one_or_none()
            if not category:
                flash("Nhóm biển báo không tồn tại.", "danger")
                return render_template(
                    "admin/sign_form.html",
                    sign=sign,
                    categories=categories,
                    selected_vehicles=vehicle_types,
                )

            # Kiểm tra trùng sign_code (loại trừ chính bản ghi đang sửa)
            duplicate = db.execute(
                select(TrafficSignCatalog).where(
                    TrafficSignCatalog.sign_code == sign_code,
                    TrafficSignCatalog.id != sign_id,
                )
            ).scalar_one_or_none()
            if duplicate:
                flash(f"Mã biển báo '{sign_code}' đã được sử dụng.", "warning")
                return render_template(
                    "admin/sign_form.html",
                    sign=sign,
                    categories=categories,
                    selected_vehicles=vehicle_types,
                )

            sign.category_id = category_id
            sign.sign_code = sign_code
            sign.name = name
            sign.tts_script = tts_script
            sign.icon_url = icon_url
            sign.priority = priority

            # Đồng bộ bảng traffic_sign_vehicles: xóa cũ + flush trước khi thêm mới để tránh lỗi UNIQUE
            sign.vehicles.clear()
            db.flush()
            for vt in vehicle_types:
                sign.vehicles.append(TrafficSignVehicle(vehicle_type=vt))
            db.commit()
            _sync_sign_cache_to_ai()
            flash(f"Đã cập nhật biển báo '{sign_code}' thành công.", "success")
            return redirect("/admin/signs")

        selected_vehicles = _extract_selected_vehicles(sign)
        return render_template(
            "admin/sign_form.html",
            sign=sign,
            categories=categories,
            selected_vehicles=selected_vehicles,
        )


@sign_bp.route("/admin/signs/delete", methods=["POST"])
@role_required(0)
def admin_sign_delete():
    sign_id_raw = (request.form.get("sign_id") or "").strip()
    try:
        sign_id = int(sign_id_raw)
    except ValueError:
        flash("ID biển báo không hợp lệ.", "danger")
        return redirect("/admin/signs")

    with get_db() as db:
        sign = (
            db.execute(
                active_select(TrafficSignCatalog)
                .options(joinedload(TrafficSignCatalog.vehicles))
                .where(TrafficSignCatalog.id == sign_id)
            )
            .unique()
            .scalar_one_or_none()
        )
        if not sign:
            flash("Không tìm thấy biển báo hoặc biển báo đã bị xóa.", "warning")
            return redirect("/admin/signs")

        sign_code = sign.sign_code
        sign.soft_delete()
        for v in sign.vehicles:
            if v.deleted_at is None:
                v.soft_delete()
        db.commit()
        _sync_sign_cache_to_ai()
        flash(f"Đã xóa mềm biển báo '{sign_code}'.", "success")
        return redirect("/admin/signs")

@sign_bp.route("/admin/signs/<int:sign_id>/restore", methods=["POST"])
@role_required(0)
def admin_sign_restore(sign_id: int):
    with get_db() as db:
        sign = (
            db.execute(
                select(TrafficSignCatalog)
                .options(joinedload(TrafficSignCatalog.vehicles))
                .where(TrafficSignCatalog.id == sign_id)
            )
            .unique()
            .scalar_one_or_none()
        )
        if not sign or sign.deleted_at is None:
            flash("Biển báo không tồn tại hoặc không ở trạng thái đã xóa mềm.", "warning")
            return redirect("/admin/signs")

        sign_code = sign.sign_code
        sign.restore()
        for v in sign.vehicles:
            if v.deleted_at is not None:
                v.restore()

        db.commit()
        _sync_sign_cache_to_ai()
        flash(f"Đã khôi phục biển báo '{sign_code}' và đồng bộ AI Cache.", "success")
        return redirect("/admin/signs")