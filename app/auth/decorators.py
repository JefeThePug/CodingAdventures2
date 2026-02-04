from functools import wraps
from flask import abort
from flask_login import current_user

from app.appctx import get_app


def admin_only(func):
    """Restrict route access to users present in the admin permission cache."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.id not in get_app().data_cache.admin.permissions:
            abort(403)
        return func(*args, **kwargs)
    return wrapper