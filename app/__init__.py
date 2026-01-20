from flask import Flask
from itsdangerous import URLSafeTimedSerializer

from .cache import DataCache
from .config import Config, ProdConfig, DevConfig
from .extensions import db

CONFIG_MAP = {
    "development": DevConfig,
    "production": ProdConfig,
}


def create_app(env):
    app = Flask(__name__)
    app.config.from_object(CONFIG_MAP[env])
    app.serializer = URLSafeTimedSerializer(
        app.secret_key,
        salt="cookie"
    )

    db.init_app(app)
    app.data_cache = DataCache(app)

    from .templating import register_globals
    from .blueprints import main_bp, auth_bp, route_bp, challenge_bp, admin_bp, errors_bp

    with app.app_context():
        register_globals()
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(route_bp)
    app.register_blueprint(challenge_bp)
    # app.register_blueprint(admin_bp)
    app.register_blueprint(errors_bp)

    return app
