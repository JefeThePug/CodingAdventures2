from flask import Flask
from itsdangerous import URLSafeTimedSerializer

from .cache import DataCache


class AppFlask(Flask):
    data_cache: DataCache
    serializer: URLSafeTimedSerializer
