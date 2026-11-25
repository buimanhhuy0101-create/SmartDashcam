from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload
from werkzeug.security import generate_password_hash


from web_app.database.connection import active_select, get_db
from web_app.models.user import User
from web_app.models.user_setting import UserSetting
from web_app.utils.decorators import role_required

user_bp = Blueprint("user", __name__)


@user_bp.route("/admin/users", methods=["GET"])
@role_required(0)
def admin_users():
    status = (request.args.get("status") or "active").strip().lower()
    if status not in ("active", "deleted"):
        status = "active"

    with get_db() as db:
        active_count = db.scalar(
            select(func.count(User.id)).where(User.deleted_at.is_(None))
        ) or 0
        deleted_count = db.scalar(
            select(func.count(User.id)).where(User.deleted_at.is_not(None))
        ) or 0

        if status == "deleted":
            users = (
                db.execute(
                    select(User)
                    .where(User.deleted_at.is_not(None))
                    .order_by(User.deleted_at.desc())
                )
                .scalars()
                .all()
            )
        else:
            users = (
                db.execute(active_select(User).order_by(User.id.desc()))
                .scalars()
                .all()
            )

        return render_template(
            "admin/users.html",
            users=users,
            status=status,
            active_count=active_count,
            deleted_count=deleted_count,
        )


@user_bp.route("/admin/users/new", methods=["GET", "POST"])
@role_required(0)
def admin_user_create():
    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        role_raw = (request.form.get("role") or "1").strip()

        if not full_name or not email or "@" not in email:
            flash("Vui lòng nhập đầy đủ họ tên và địa chỉ email hợp lệ.", "warning")
            return render_template("admin/user_form.html", user=None)

        if len(password) < 6:
            flash("Mật khẩu phải có tối thiểu 6 ký tự.", "warning")
            return render_template("admin/user_form.html", user=None)

        try:
            role = int(role_raw)
            if role not in (0, 1):
                raise ValueError
        except ValueError:
            flash("Vai trò người dùng không hợp lệ.", "danger")
            return render_template("admin/user_form.html", user=None)

        with get_db() as db:
            # Kiểm tra trùng email trên toàn bảng (kể cả tài khoản đã xóa mềm vì cột UNIQUE)
            existing = db.scalar(select(User).where(User.email == email))
            if existing:
                if existing.deleted_at is not None:
                    flash("Email này đã tồn tại trong dữ liệu tài khoản đã xóa mềm.", "warning")
                else:
                    flash("Email này đã được sử dụng.", "warning")
                return render_template("admin/user_form.html", user=None)

            new_user = User(
                full_name=full_name,
                email=email,
                password_hash=generate_password_hash(password),
                role=role,
                is_active=True,
            )
            db.add(new_user)
            db.flush()

            # Tự động khởi tạo cấu hình mặc định trong user_settings (theo đặc tả UC-08)
            db.add(UserSetting(user_id=new_user.id))

        flash(f"Đã tạo tài khoản '{full_name}' thành công.", "success")
        return redirect("/admin/users")

    return render_template("admin/user_form.html", user=None)


@user_bp.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
@role_required(0)
def admin_user_edit(user_id: int):
    with get_db() as db:
        user = db.execute(
            active_select(User).where(User.id == user_id)
        ).scalar_one_or_none()

        if not user:
            flash("Không tìm thấy tài khoản cần chỉnh sửa.", "warning")
            return redirect("/admin/users")

        if request.method == "POST":
            full_name = (request.form.get("full_name") or "").strip()
            email = (request.form.get("email") or "").strip().lower()
            password = request.form.get("password") or ""
            role_raw = (request.form.get("role") or str(user.role)).strip()

            if not full_name or not email or "@" not in email:
                flash("Vui lòng nhập đầy đủ họ tên và địa chỉ email hợp lệ.", "warning")
                return render_template("admin/user_form.html", user=user)

            if password and len(password) < 6:
                flash("Mật khẩu mới phải có tối thiểu 6 ký tự.", "warning")
                return render_template("admin/user_form.html", user=user)

            try:
                role = int(role_raw)
                if role not in (0, 1):
                    raise ValueError
            except ValueError:
                flash("Vai trò người dùng không hợp lệ.", "danger")
                return render_template("admin/user_form.html", user=user)

            # Chặn Admin tự hạ quyền chính mình
            if user.id == session.get("user_id") and role != 0:
                flash("Bạn không thể tự thay đổi vai trò của tài khoản đang đăng nhập.", "warning")
                return render_template("admin/user_form.html", user=user)

            # Kiểm tra trùng email (loại trừ chính tài khoản đang sửa)
            duplicate = db.scalar(
                select(User).where(User.email == email, User.id != user_id)
            )
            if duplicate:
                flash("Email này đã được sử dụng bởi tài khoản khác.", "warning")
                return render_template("admin/user_form.html", user=user)

            user.full_name = full_name
            user.email = email
            user.role = role
            if password:
                user.password_hash = generate_password_hash(password)

            # Đồng bộ tên hiển thị trên thanh menu nếu đang sửa chính mình
            if user.id == session.get("user_id"):
                session["full_name"] = user.full_name

            flash(f"Đã cập nhật tài khoản '{user.full_name}' thành công.", "success")
            return redirect("/admin/users")

        return render_template("admin/user_form.html", user=user)


@user_bp.route("/admin/users/delete", methods=["POST"])
@role_required(0)
def admin_user_delete():
    user_id_raw = (request.form.get("user_id") or "").strip()
    try:
        user_id = int(user_id_raw)
    except ValueError:
        flash("ID tài khoản không hợp lệ.", "danger")
        return redirect("/admin/users")

    # Luồng phụ 3a: Chặn Admin tự xóa chính mình
    if user_id == session.get("user_id"):
        flash("Không thể tự xóa tài khoản đang đăng nhập.", "danger")
        return redirect("/admin/users")

    with get_db() as db:
        user = (
            db.execute(
                active_select(User)
                .options(joinedload(User.setting))
                .where(User.id == user_id)
            )
            .scalar_one_or_none()
        )
        if not user:
            flash("Không tìm thấy tài khoản hoặc tài khoản đã bị xóa.", "warning")
            return redirect("/admin/users")

        user_name = user.full_name
        user.soft_delete()
        if user.setting and user.setting.deleted_at is None:
            user.setting.soft_delete()

        flash(f"Đã xóa mềm tài khoản '{user_name}'.", "success")
        return redirect("/admin/users")


@user_bp.route("/admin/users/<int:user_id>/restore", methods=["POST"])
@role_required(0)
def admin_user_restore(user_id: int):
    with get_db() as db:
        user = (
            db.execute(
                select(User)
                .options(joinedload(User.setting))
                .where(User.id == user_id)
            )
            .scalar_one_or_none()
        )
        if not user or user.deleted_at is None:
            flash("Tài khoản không tồn tại hoặc không ở trạng thái đã xóa mềm.", "warning")
            return redirect("/admin/users")

        user.restore()
        if user.setting and user.setting.deleted_at is not None:
            user.setting.restore()

        flash(f"Đã khôi phục tài khoản '{user.full_name}'.", "success")
        return redirect("/admin/users")