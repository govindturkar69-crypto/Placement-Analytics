"""Flask extension instances, created unbound and wired up in init_app()
inside create_app(). Keeping them here (rather than on the app object
directly) is what lets route modules import mysql/mail/limiter without
a circular import back to the app factory.
"""
import pymysql
pymysql.install_as_MySQLdb()

from flask_mysqldb import MySQL
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect

mysql = MySQL()
mail = Mail()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["300 per day", "60 per hour"],
    storage_uri="memory://",
)
