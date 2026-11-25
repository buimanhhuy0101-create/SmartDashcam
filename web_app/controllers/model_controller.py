import hashlib
from datetime import datetime
from pathlib import Path

import requests
from flask import Blueprint, flash, redirect, render_template, request
from werkzeug.utils import secure_filename
from sqlalchemy import func, select

from web_app.config import Config
from web_app.database.connection import active_select, get_db
from web_app.models.ai_model import AIModel
from web_app.utils.decorators import role_required

model_bp = Blueprint("model", __name__)

VALID_MODEL_TYPES = ("sign", "obstacle")
VALID_IMGSZ = (320, 416, 640, 1280)


def _compute_sha256(file_path: Path) -> str:
    """Tính mã băm SHA-256 theo từng khối để tiết kiệm RAM với file .pt lớn."""
    sha256 = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


@model_bp.route("/admin/models", methods=["GET"])
@role_required(0)
def admin_models():
    status = (request.args.get("status") or "active").strip().lower()
    if status not in ("active", "deleted"):
        status = "active"

    with get_db() as db:
        active_count = db.scalar(
            select(func.count(AIModel.id)).where(AIModel.deleted_at.is_(None))
        ) or 0
        deleted_count = db.scalar(
            select(func.count(AIModel.id)).where(AIModel.deleted_at.is_not(None))
        ) or 0

        if status == "deleted":
            models = (
                db.execute(
                    select(AIModel)
                    .where(AIModel.deleted_at.is_not(None))
                    .order_by(AIModel.deleted_at.desc())
                )
                .scalars()
                .all()
            )
        else:
            models = (
                db.execute(active_select(AIModel).order_by(AIModel.id.desc()))
                .scalars()
                .all()
            )

        return render_template(
            "admin/models.html",
            models=models,
            status=status,
            active_count=active_count,
            deleted_count=deleted_count,
        )


@model_bp.route("/admin/models/upload", methods=["POST"])
@role_required(0)
def admin_model_upload():
    uploaded_file = request.files.get("model_file")
    name = (request.form.get("name") or "").strip()
    model_type = (request.form.get("model_type") or "").strip().lower()
    imgsz_raw = (request.form.get("imgsz") or "640").strip()

    # Luồng phụ 2a: Kiểm tra định dạng tệp và thông tin bắt buộc
    if not uploaded_file or not uploaded_file.filename:
        flash("Vui lòng chọn tệp mô hình (.pt).", "warning")
        return redirect("/admin/models")

    original_name = secure_filename(uploaded_file.filename)
    if not original_name.lower().endswith(".pt"):
        flash("Định dạng tệp không hợp lệ. Chỉ hỗ trợ tệp trọng số .pt.", "danger")
        return redirect("/admin/models")

    if not name or model_type not in VALID_MODEL_TYPES:
        flash("Vui lòng nhập tên mô hình và chọn loại nhiệm vụ hợp lệ.", "warning")
        return redirect("/admin/models")

    try:
        imgsz = int(imgsz_raw)
        if imgsz not in VALID_IMGSZ:
            imgsz = 640
    except ValueError:
        imgsz = 640

    # Lưu tệp vào thư mục dùng chung storage/models/
    Config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_filename = f"{model_type}_{ts}_{original_name}"
    dest_path = Config.MODELS_DIR / saved_filename

    try:
        uploaded_file.save(dest_path)
        checksum = _compute_sha256(dest_path)
    except OSError as exc:
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        flash(f"Lỗi khi lưu tệp mô hình: {exc}", "danger")
        return redirect("/admin/models")

    rel_path = f"storage/models/{saved_filename}"
    version = f"v{ts}"

    with get_db() as db:
        new_model = AIModel(
            name=name,
            model_type=model_type,
            version=version,
            file_path=rel_path,
            checksum_sha256=checksum,
            imgsz=imgsz,
            is_active=False,
        )
        db.add(new_model)

    flash(
        f"Đã tải lên mô hình '{name}' ({version}). Bấm 'Kích hoạt' để nạp nóng sang AI Service.",
        "success",
    )
    return redirect("/admin/models")


@model_bp.route("/admin/models/activate", methods=["POST"])
@role_required(0)
def admin_model_activate():
    model_id_raw = (request.form.get("model_id") or "").strip()
    try:
        model_id = int(model_id_raw)
    except ValueError:
        flash("ID mô hình không hợp lệ.", "danger")
        return redirect("/admin/models")

    with get_db() as db:
        target = db.execute(
            active_select(AIModel).where(AIModel.id == model_id)
        ).scalar_one_or_none()
        if not target:
            flash("Không tìm thấy mô hình cần kích hoạt.", "warning")
            return redirect("/admin/models")

        # Gọi API Local Hot-Reload sang FastAPI AI Service
        reload_url = f"{Config.AI_SERVICE_URL.rstrip('/')}/api/v1/models/reload"
        payload = {
            "model_id": target.id,
            "name": target.name,
            "model_type": target.model_type,
            "version": target.version,
            "file_path": target.file_path,
            "checksum_sha256": target.checksum_sha256,
            "imgsz": target.imgsz,
        }

        try:
            resp = requests.post(reload_url, json=payload, timeout=30)
        except requests.RequestException:
            # Luồng phụ 3a: Mất kết nối AI Service -> không kích hoạt trong DB
            flash(
                "Không thể liên lạc với FastAPI AI Service để nạp nóng mô hình. Vui lòng kiểm tra AI Service.",
                "danger",
            )
            return redirect("/admin/models")

        if resp.status_code != 200:
            # Luồng phụ 4a: SHA-256 lỗi hoặc Dummy Inference thất bại -> Rollback, không kích hoạt
            detail = "Nạp nóng thất bại, AI Service đã giữ nguyên phiên bản cũ."
            try:
                body = resp.json()
                detail = body.get("detail") or body.get("message") or detail
            except ValueError:
                pass
            flash(f"Kích hoạt thất bại (Rollback): {detail}", "danger")
            return redirect("/admin/models")

        # Thành công -> Tắt is_active các bản cùng loại và bật bản mới
        same_type_models = (
            db.execute(
                active_select(AIModel).where(AIModel.model_type == target.model_type)
            )
            .scalars()
            .all()
        )
        for m in same_type_models:
            m.is_active = m.id == target.id

        flash(
            f"Đã kích hoạt và nạp nóng thành công mô hình '{target.name}' ({target.version}).",
            "success",
        )
        return redirect("/admin/models")


@model_bp.route("/admin/models/delete", methods=["POST"])
@role_required(0)
def admin_model_delete():
    model_id_raw = (request.form.get("model_id") or "").strip()
    try:
        model_id = int(model_id_raw)
    except ValueError:
        flash("ID mô hình không hợp lệ.", "danger")
        return redirect("/admin/models")

    with get_db() as db:
        target = db.execute(
            active_select(AIModel).where(AIModel.id == model_id)
        ).scalar_one_or_none()
        if not target:
            flash("Không tìm thấy mô hình hoặc mô hình đã bị xóa.", "warning")
            return redirect("/admin/models")

        if target.is_active:
            flash("Không thể xóa mô hình đang ở trạng thái hoạt động.", "warning")
            return redirect("/admin/models")

        target_name = target.name
        target.soft_delete()
        flash(f"Đã xóa mềm mô hình '{target_name}'.", "success")
        return redirect("/admin/models")

@model_bp.route("/admin/models/<int:model_id>/restore", methods=["POST"])
@role_required(0)
def admin_model_restore(model_id: int):
    with get_db() as db:
        target = db.execute(
            select(AIModel).where(AIModel.id == model_id)
        ).scalar_one_or_none()
        if not target or target.deleted_at is None:
            flash("Mô hình không tồn tại hoặc không ở trạng thái đã xóa mềm.", "warning")
            return redirect("/admin/models")

        target.restore()
        target.is_active = False
        target_name = target.name
        flash(
            f"Đã khôi phục mô hình '{target_name}' (trạng thái Chờ kích hoạt).",
            "success",
        )
        return redirect("/admin/models")