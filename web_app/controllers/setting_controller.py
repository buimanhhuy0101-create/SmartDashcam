import os
import requests
from flask import Blueprint, flash, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from web_app.database.connection import get_db
from web_app.models import User, UserSetting

setting_bp = Blueprint("setting", __name__)

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/")


def _get_or_create_setting(db, user_id: int) -> UserSetting:
    setting = (
        db.query(UserSetting)
        .filter(
            UserSetting.user_id == user_id,
            UserSetting.deleted_at.is_(None),
        )
        .first()
    )
    if not setting:
        setting = UserSetting(
            user_id=user_id,
            vehicle_type="car",
            tts_enabled=True,
            alert_sound_enabled=True,
            conf_threshold=0.45,
            ttc_warning_sec=2.5,
            ttc_danger_sec=1.2,
        )
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting


def _sync_config_to_ai(setting: UserSetting) -> bool:
    """Đẩy ngưỡng mới sang FastAPI để áp dụng ngay cho ObstacleTracker."""
    payload = {
        "conf_threshold": float(setting.conf_threshold),
        "ttc_warning_sec": float(setting.ttc_warning_sec),
        "ttc_danger_sec": float(setting.ttc_danger_sec),
    }
    try:
        resp = requests.post(f"{AI_SERVICE_URL}/api/v1/config", json=payload, timeout=2.0)
        return resp.status_code == 200
    except Exception as exc:
        print(f"[Setting] Không đồng bộ được sang AI Service: {exc}")
        return False


@setting_bp.route("/driver/settings", methods=["GET", "POST"])
def driver_settings():
    user_id = session.get("user_id")
    if not user_id:
        flash("Vui lòng đăng nhập để cấu hình hệ thống.", "warning")
        return redirect("/login")

    with get_db() as db:
        setting = _get_or_create_setting(db, int(user_id))

        if request.method == "POST":
            vehicle_type = request.form.get("vehicle_type", setting.vehicle_type or "car")
            tts_enabled = request.form.get("tts_enabled") in ("on", "true", "1", "yes")
            alert_sound_enabled = request.form.get("alert_sound_enabled") in ("on", "true", "1", "yes")

            try:
                conf_threshold = float(request.form.get("conf_threshold", setting.conf_threshold))
                ttc_warning_sec = float(request.form.get("ttc_warning_sec", setting.ttc_warning_sec))
                ttc_danger_sec = float(request.form.get("ttc_danger_sec", setting.ttc_danger_sec))
            except ValueError:
                flash("Giá trị ngưỡng nhập vào không hợp lệ.", "danger")
                return render_template("driver/settings.html", setting=setting)

            if ttc_danger_sec >= ttc_warning_sec:
                flash("Ngưỡng Nguy hiểm (Đỏ) phải nhỏ hơn ngưỡng Cảnh báo (Vàng).", "warning")
                return render_template("driver/settings.html", setting=setting)

            setting.vehicle_type = vehicle_type
            setting.tts_enabled = tts_enabled
            setting.alert_sound_enabled = alert_sound_enabled
            setting.conf_threshold = conf_threshold
            setting.ttc_warning_sec = ttc_warning_sec
            setting.ttc_danger_sec = ttc_danger_sec

            db.commit()

            synced = _sync_config_to_ai(setting)
            if synced:
                flash("Đã lưu cài đặt và đồng bộ trực tiếp sang AI Service!", "success")
            else:
                flash("Đã lưu cài đặt vào CSDL (AI Service chưa kết nối để đồng bộ nóng).", "warning")

            return redirect("/driver/settings")

        return render_template("driver/settings.html", setting=setting)


@setting_bp.route("/driver/settings/change-password", methods=["POST"])
def change_password():
    user_id = session.get("user_id")
    if not user_id:
        flash("Vui lòng đăng nhập để thực hiện thao tác này.", "warning")
        return redirect("/login")

    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not current_password or not new_password or not confirm_password:
        flash("Vui lòng nhập đầy đủ mật khẩu hiện tại và mật khẩu mới.", "warning")
        return redirect("/driver/settings")

    if len(new_password) < 6:
        flash("Mật khẩu mới phải có ít nhất 6 ký tự.", "warning")
        return redirect("/driver/settings")

    if new_password != confirm_password:
        flash("Xác nhận mật khẩu mới không khớp.", "danger")
        return redirect("/driver/settings")

    if new_password == current_password:
        flash("Mật khẩu mới không được trùng với mật khẩu hiện tại.", "warning")
        return redirect("/driver/settings")

    with get_db() as db:
        user = (
            db.query(User)
            .filter(
                User.id == int(user_id),
                User.deleted_at.is_(None),
            )
            .first()
        )
        if not user:
            flash("Không tìm thấy tài khoản hợp lệ.", "danger")
            return redirect("/login")

        if not check_password_hash(user.password_hash, current_password):
            flash("Mật khẩu hiện tại không chính xác.", "danger")
            return redirect("/driver/settings")

        user.password_hash = generate_password_hash(new_password)
        db.commit()

    session.clear()
    flash("Đổi mật khẩu thành công! Vui lòng đăng nhập lại bằng mật khẩu mới.", "success")
    return redirect("/login")