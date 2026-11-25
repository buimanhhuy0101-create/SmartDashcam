from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy import select
from werkzeug.security import generate_password_hash, check_password_hash

from web_app.database.connection import get_db, active_select
from web_app.models import User, UserSetting

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        with get_db() as db:
            user = db.scalar(active_select(User).where(User.email == email))

            if not user or not check_password_hash(user.password_hash, password):
                flash("Email hoặc mật khẩu không đúng.", "danger")
                return render_template("auth/login.html")

            if not user.is_active:
                flash("Tài khoản của bạn đã bị khóa.", "danger")
                return render_template("auth/login.html")

            session.clear()
            session["user_id"] = user.id
            session["role"] = user.role
            session["full_name"] = user.full_name
            session.permanent = remember

        if user.role == 0:
            return redirect("/admin/signs")
        return redirect("/driver/hud")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("index"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not full_name or not email or len(password) < 6:
            flash("Vui lòng nhập đầy đủ thông tin (mật khẩu tối thiểu 6 ký tự).", "danger")
            return render_template("auth/register.html")

        with get_db() as db:
            existing = db.scalar(select(User).where(User.email == email))
            if existing:
                flash("Email này đã được sử dụng.", "danger")
                return render_template("auth/register.html")

            new_user = User(
                full_name=full_name,
                email=email,
                password_hash=generate_password_hash(password),
                role=1,  # Tài xế
                is_active=True,
            )
            db.add(new_user)
            db.flush()

            db.add(UserSetting(user_id=new_user.id))

        flash("Đăng ký thành công! Bạn có thể đăng nhập ngay.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Đã đăng xuất thành công.", "success")
    return redirect(url_for("auth.login"))