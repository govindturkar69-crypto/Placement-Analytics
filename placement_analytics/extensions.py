"""Flask extension instances, created unbound and wired up in init_app()
inside create_app(). Keeping them here (rather than on the app object
directly) is what lets route modules import mysql/mail/limiter without
a circular import back to the app factory.
"""
import pymysql
from flask import g, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect
from authlib.integrations.flask_client import OAuth

class MySQL:
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.teardown_appcontext(self.teardown)

    def connect(self):
        return pymysql.connect(
            host=current_app.config.get('MYSQL_HOST', 'localhost'),
            user=current_app.config.get('MYSQL_USER', ''),
            password=current_app.config.get('MYSQL_PASSWORD', ''),
            database=current_app.config.get('MYSQL_DB', ''),
            port=current_app.config.get('MYSQL_PORT', 3306),
            autocommit=current_app.config.get('MYSQL_AUTOCOMMIT', False)
        )

    @property
    def connection(self):
        ctx = g
        if ctx is not None:
            if not hasattr(ctx, 'mysql_db'):
                ctx.mysql_db = self.connect()
            return ctx.mysql_db

    def teardown(self, exception):
        ctx = g
        if hasattr(ctx, 'mysql_db'):
            ctx.mysql_db.close()

mysql = MySQL()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["300 per day", "60 per hour"],
    storage_uri="memory://",
)
oauth = OAuth()
