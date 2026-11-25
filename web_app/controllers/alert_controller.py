from datetime import datetime
from pathlib import Path

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
)

from web_app.config import Config
from web_app.database.connection import get_db
from web_app.models import AlertObject, CollisionAlert

alert_bp = Blueprint("alert", __name__)


def _get_current_user_id():
    """Lấy user_id từ session; trả về None nếu chưa đăng nhập."""
    return session.get("user_id")


def _normalize_snapshot_url(raw_path: str | None) -> str | None:
    """Chuẩn hóa tên file / đường dẫn ảnh chụp thành URL '/snapshots/<filename>'."""
    if not raw_path:
        return None
    clean = raw_path.strip().replace("\\", "/")
    if clean.startswith(("/snapshots/", "/static/", "http://", "https://")):
        return clean
    return f"/snapshots/{Path(clean).name}"


# ================= 0. PHỤC VỤ ẢNH SNAPSHOT TỪ storage/snapshots/ =================
@alert_bp.route("/snapshots/<path:filename>", methods=["GET"])
def serve_snapshot(filename: str):
    if not _get_current_user_id():
        return "", 401
    return send_from_directory(str(Config.SNAPSHOTS_DIR), filename)


# ================= 1. API NỘI BỘ NHẬN CẢNH BÁO TỪ FASTAPI =================
@alert_bp.route("/api/internal/alerts", methods=["POST"])
def receive_internal_alert():
    """API nội bộ nhận sự kiện cảnh báo va chạm (WARNING/CRITICAL) từ FastAPI AI Service."""
    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id")
    risk_level = data.get("severity") or data.get("risk_level")
    alert_type = data.get("alert_type", "FCW")
    min_ttc = data.get("min_ttc")
    snapshot_path = _normalize_snapshot_url(data.get("snapshot_path"))
    objects = data.get("objects", [])

    if not user_id or risk_level not in ("WARNING", "CRITICAL"):
        return jsonify({"error": "Thiếu user_id hoặc risk_level không hợp lệ"}), 400

    ttc_text = f"{min_ttc}s" if min_ttc is not None else "--"
    if risk_level == "CRITICAL":
        message = f"Nguy cơ va chạm cao! Vật cản rất gần (TTC ~ {ttc_text})"
    else:
        message = f"Cảnh báo khoảng cách an toàn (TTC ~ {ttc_text})"

    try:
        now = datetime.now()
        with get_db() as db:
            alert = CollisionAlert(
                user_id=int(user_id),
                alert_type=alert_type,
                risk_level=risk_level,
                message=message,
                min_ttc=float(min_ttc) if min_ttc is not None else None,
                snapshot_path=snapshot_path,
                created_at=now,
                updated_at=now,
            )
            db.add(alert)
            db.flush()

            for obj in objects:
                bbox = obj.get("bbox") or [0, 0, 0, 0]
                x1, y1, x2, y2 = (bbox + [0, 0, 0, 0])[:4]

                alert_obj = AlertObject(
                    alert_id=alert.id,
                    track_id=obj.get("track_id"),
                    object_label=obj.get("label", "unknown"),
                    confidence=float(obj.get("conf", 0.0)),
                    bbox_x1=float(x1),
                    bbox_y1=float(y1),
                    bbox_x2=float(x2),
                    bbox_y2=float(y2),
                    estimated_ttc=obj.get("estimated_ttc"),
                    created_at=now,
                    updated_at=now,
                )
                db.add(alert_obj)

            db.commit()
            print(f"[Internal Alerts] Đã lưu alert #{alert.id} | level={risk_level} | min_ttc={min_ttc}")
            return jsonify({"status": "saved", "alert_id": alert.id}), 201

    except Exception as exc:
        print(f"[Internal Alerts] Lỗi lưu CSDL: {exc}")
        return jsonify({"error": str(exc)}), 500


# ================= 2. UC-04: DANH SÁCH LỊCH SỬ CẢNH BÁO =================
@alert_bp.route("/driver/history", methods=["GET"])
def driver_history():
    user_id = _get_current_user_id()
    if not user_id:
        flash("Vui lòng đăng nhập để xem lịch sử cảnh báo.", "warning")
        return redirect("/login")

    risk_filter = request.args.get("risk_level", "ALL").upper()

    with get_db() as db:
        base_query = db.query(CollisionAlert).filter(
            CollisionAlert.user_id == int(user_id),
            CollisionAlert.deleted_at.is_(None),
        )

        # Thống kê nhanh cho các thẻ tổng quan
        total_count = base_query.count()
        critical_count = base_query.filter(CollisionAlert.risk_level == "CRITICAL").count()
        warning_count = base_query.filter(CollisionAlert.risk_level == "WARNING").count()

        # Lọc theo mức độ nếu người dùng chọn
        filtered_query = base_query
        if risk_filter in ("WARNING", "CRITICAL"):
            filtered_query = filtered_query.filter(CollisionAlert.risk_level == risk_filter)

        alerts = (
            filtered_query.order_by(CollisionAlert.created_at.desc())
            .limit(100)
            .all()
        )

        for item in alerts:
            if item.snapshot_path:
                item.snapshot_path = _normalize_snapshot_url(item.snapshot_path)

        # Render ngay trong phiên db để tránh lỗi DetachedInstanceError
        return render_template(
            "driver/history.html",
            alerts=alerts,
            risk_filter=risk_filter,
            total_count=total_count,
            critical_count=critical_count,
            warning_count=warning_count,
        )


# ================= 3. UC-04: CHI TIẾT CẢNH BÁO =================
@alert_bp.route("/driver/history/<int:alert_id>", methods=["GET"])
def driver_history_detail(alert_id: int):
    user_id = _get_current_user_id()
    if not user_id:
        flash("Vui lòng đăng nhập để xem chi tiết cảnh báo.", "warning")
        return redirect("/login")

    with get_db() as db:
        alert = (
            db.query(CollisionAlert)
            .filter(
                CollisionAlert.id == alert_id,
                CollisionAlert.user_id == int(user_id),
                CollisionAlert.deleted_at.is_(None),
            )
            .first()
        )

        if not alert:
            flash("Không tìm thấy cảnh báo hoặc bạn không có quyền xem.", "danger")
            return redirect("/driver/history")

        if alert.snapshot_path:
            alert.snapshot_path = _normalize_snapshot_url(alert.snapshot_path)

        objects = (
            db.query(AlertObject)
            .filter(
                AlertObject.alert_id == alert.id,
                AlertObject.deleted_at.is_(None),
            )
            .all()
        )

        return render_template(
            "driver/history_detail.html",
            alert=alert,
            objects=objects,
        )


# ================= 4. UC-04: XÓA MỀM CẢNH BÁO =================
@alert_bp.route("/driver/history/<int:alert_id>/delete", methods=["POST"])
def delete_driver_history(alert_id: int):
    user_id = _get_current_user_id()
    if not user_id:
        return redirect("/login")

    with get_db() as db:
        alert = (
            db.query(CollisionAlert)
            .filter(
                CollisionAlert.id == alert_id,
                CollisionAlert.user_id == int(user_id),
                CollisionAlert.deleted_at.is_(None),
            )
            .first()
        )

        if not alert:
            flash("Không tìm thấy cảnh báo để xóa.", "warning")
            return redirect("/driver/history")

        now = datetime.now()
        alert.deleted_at = now

        # Xóa mềm kèm các bản ghi con trong alert_objects
        db.query(AlertObject).filter(
            AlertObject.alert_id == alert.id,
            AlertObject.deleted_at.is_(None),
        ).update({"deleted_at": now})

        db.commit()
        flash("Đã xóa cảnh báo khỏi lịch sử.", "success")

    return redirect("/driver/history")


@alert_bp.route("/driver/history/delete", methods=["POST"])
def delete_driver_history_form():
    """Nhận POST từ Modal xác nhận xóa trong history.html."""
    alert_id = request.form.get("alert_id", type=int)
    if not alert_id:
        flash("Thiếu mã cảnh báo cần xóa.", "warning")
        return redirect("/driver/history")
    return delete_driver_history(alert_id)