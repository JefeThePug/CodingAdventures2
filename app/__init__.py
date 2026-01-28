import os

from itsdangerous import URLSafeTimedSerializer

from .cache import DataCache
from .config import ProdConfig, DevConfig
from .extensions import db
from .types import AppFlask

SERIALIZER_SALT = "cookie"
CONFIG_MAP = {
    "development": DevConfig,
    "production": ProdConfig,
}


def create_app() -> AppFlask:
    env = os.getenv("FLASK_ENV", "development")

    try:
        config_type = CONFIG_MAP[env]
    except KeyError:
        raise RuntimeError(f"Unknown environment: {env}")

    app = AppFlask(__name__)
    app.config.from_object(config_type)
    app.serializer = URLSafeTimedSerializer(app.secret_key, salt=SERIALIZER_SALT)

    db.init_app(app)
    app.data_cache = DataCache()

    from .templating import register_globals
    from .blueprints import (
        main_bp,
        auth_bp,
        route_bp,
        challenge_bp,
        admin_bp,
        errors_bp,
    )

    with app.app_context():
        app.data_cache.load()
        register_globals()
    for bp in (
        main_bp,
        auth_bp,
        route_bp,
        challenge_bp,
        admin_bp,
        errors_bp,
    ):
        app.register_blueprint(bp)

    return app
