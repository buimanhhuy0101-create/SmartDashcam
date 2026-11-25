from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            flash("Vui lòng đăng nhập để tiếp tục.", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def role_required(required_role: int):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("user_id"):
                flash("Vui lòng đăng nhập để tiếp tục.", "danger")
                return redirect(url_for("auth.login"))
            if session.get("role") != required_role:
                flash("Bạn không có quyền truy cập trang này.", "danger")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return decorated
    return decorator