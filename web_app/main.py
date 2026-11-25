import requests
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload
from web_app.database.connection import active_select, get_db
from web_app.models import (
    AIModel,
    CollisionAlert,
    TrafficSignCatalog,
    TrafficSignCategory,
    User,
)
from datetime import timedelta
from flask import Flask, redirect, session, render_template

from web_app.config import Config
from web_app.controllers.auth_controller import auth_bp
from web_app.controllers.alert_controller import alert_bp
from web_app.controllers.setting_controller import setting_bp
from web_app.controllers.sign_controller import sign_bp
from web_app.controllers.model_controller import model_bp
from web_app.controllers.user_controller import user_bp
from web_app.utils.decorators import role_required


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="views/templates",
        static_folder="views/static",
    )
    app.secret_key = Config.SECRET_KEY
    app.permanent_session_lifetime = timedelta(days=7)

    # Đăng ký Blueprint
    app.register_blueprint(auth_bp)
    app.register_blueprint(alert_bp)
    app.register_blueprint(setting_bp)
    app.register_blueprint(sign_bp)
    app.register_blueprint(model_bp)
    app.register_blueprint(user_bp)

    @app.route("/")
    def index():
        if not session.get("user_id"):
            return redirect("/auth/login")
        return redirect("/admin/dashboard" if session.get("role") == 0 else "/driver/hud")

    # ================= NHÓM ROUTE TÀI XẾ (role = 1) =================
    @app.route("/driver/hud")
    @role_required(1)
    def driver_hud():
        return render_template("driver/hud.html")

    @app.route("/driver/history")
    @role_required(1)
    def driver_history():
        return render_template("driver/history.html", history=[], alerts=[])

    @app.route("/driver/history/<int:alert_id>")
    @role_required(1)
    def driver_history_detail(alert_id):
        return render_template("driver/history_detail.html", alert=None, alert_objects=[])

    @app.route("/driver/settings", methods=["GET", "POST"])
    @role_required(1)
    def driver_settings():
        dummy_setting = {
            "vehicle_type": "car",
            "conf_threshold": 0.5,
            "ttc_warning_sec": 2.5,
            "ttc_danger_sec": 1.2,
            "tts_enabled": True,
            "alert_sound_enabled": True,
        }
        return render_template("driver/settings.html", setting=dummy_setting)

    # ================= NHÓM ROUTE QUẢN TRỊ (role = 0) =================
    @app.route("/admin/dashboard")
    @role_required(0)
    def admin_dashboard():
        # 1. Kiểm tra trạng thái sống của FastAPI AI Service (:8001)
        ai_online = False
        base_ai = Config.AI_SERVICE_URL.rstrip("/")
        for health_ep in ("/health", "/api/v1/health"):
            try:
                resp = requests.get(f"{base_ai}{health_ep}", timeout=1.5)
                if resp.status_code == 200:
                    ai_online = True
                    break
            except requests.RequestException:
                break

        with get_db() as db:
            # 2. Thống kê 4 thẻ KPI (chỉ tính bản ghi chưa xóa mềm)
            total_users = db.scalar(
                select(func.count(User.id)).where(User.deleted_at.is_(None))
            ) or 0
            total_drivers = db.scalar(
                select(func.count(User.id)).where(
                    User.deleted_at.is_(None),
                    User.role == 1,
                    User.is_active.is_(True),
                )
            ) or 0
            total_signs = db.scalar(
                select(func.count(TrafficSignCatalog.id)).where(
                    TrafficSignCatalog.deleted_at.is_(None)
                )
            ) or 0
            total_models = db.scalar(
                select(func.count(AIModel.id)).where(AIModel.deleted_at.is_(None))
            ) or 0
            total_alerts = db.scalar(
                select(func.count(CollisionAlert.id)).where(
                    CollisionAlert.deleted_at.is_(None)
                )
            ) or 0

            stats = {
                "total_users": total_users,
                "total_drivers": total_drivers,
                "total_signs": total_signs,
                "total_models": total_models,
                "total_alerts": total_alerts,
            }

            # 3. Model AI đang kích hoạt trên hệ thống
            active_sign = db.scalar(
                active_select(AIModel)
                .where(AIModel.model_type == "sign", AIModel.is_active.is_(True))
                .order_by(AIModel.id.desc())
            )
            active_obs = db.scalar(
                active_select(AIModel)
                .where(AIModel.model_type == "obstacle", AIModel.is_active.is_(True))
                .order_by(AIModel.id.desc())
            )
            active_models = {
                "sign": (
                    f"{active_sign.name} ({active_sign.version})"
                    if active_sign
                    else "Chưa kích hoạt"
                ),
                "obstacle": (
                    f"{active_obs.name} ({active_obs.version})"
                    if active_obs
                    else "yolo11n.pt (COCO + ByteTrack)"
                ),
            }

            # 4. Phân bố 4 nhóm biển báo từ traffic_sign_categories & traffic_sign_catalog
            color_map = {
                "CAM": "bg-danger",
                "NGUY_HIEM": "bg-warning",
                "HIEU_LENH": "bg-primary",
                "CHI_DAN": "bg-info",
            }
            categories = db.scalars(
                active_select(TrafficSignCategory).order_by(TrafficSignCategory.id.asc())
            ).all()
            cat_counts = dict(
                db.execute(
                    select(
                        TrafficSignCatalog.category_id,
                        func.count(TrafficSignCatalog.id),
                    )
                    .where(TrafficSignCatalog.deleted_at.is_(None))
                    .group_by(TrafficSignCatalog.category_id)
                ).all()
            )
            category_stats = [
                {
                    "name": cat.name,
                    "count": cat_counts.get(cat.id, 0),
                    "color": color_map.get(cat.code, "bg-primary"),
                }
                for cat in categories
            ]

            # 5. Danh sách 10 cảnh báo va chạm gần nhất (kèm tên tài xế)
            recent_alerts = (
                db.execute(
                    active_select(CollisionAlert)
                    .options(joinedload(CollisionAlert.user))
                    .order_by(CollisionAlert.id.desc())
                    .limit(10)
                )
                .scalars()
                .all()
            )

            return render_template(
                "admin/dashboard.html",
                stats=stats,
                ai_status={"online": ai_online},
                active_models=active_models,
                category_stats=category_stats,
                recent_alerts=recent_alerts,
            )
    @app.route("/admin/models")
    @role_required(0)
    def admin_models():
        return render_template("admin/models.html", models=[])

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=Config.WEB_HOST, port=Config.WEB_PORT, debug=True)