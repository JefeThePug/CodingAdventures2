from typing import cast

from flask import current_app

from app.types import AppFlask


def get_app() -> AppFlask:
    return cast(AppFlask, current_app)
