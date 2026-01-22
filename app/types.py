from typing import TYPE_CHECKING
from flask import Flask
from itsdangerous import URLSafeTimedSerializer

if TYPE_CHECKING:
    from app.cache import DataCache


class AppFlask(Flask):
    data_cache: "DataCache"
    serializer: URLSafeTimedSerializer
