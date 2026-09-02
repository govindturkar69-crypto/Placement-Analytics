import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # Render (and most PaaS) terminate TLS at the edge and forward internally
    # over plain HTTP -- ProxyFix (wired up in create_app) is what makes
    # request.is_secure and client IPs correct despite that.
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB request body cap
    SEND_FILE_MAX_AGE_DEFAULT = 31536000
    PERMANENT_SESSION_LIFETIME = 1800
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'true').lower() == 'true'
    SESSION_COOKIE_SAMESITE = 'Lax'

    MYSQL_HOST = os.environ.get('MYSQL_HOST')
    MYSQL_USER = os.environ.get('MYSQL_USER')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_DB = os.environ.get('MYSQL_DB')

    # "Continue with Google" login. Left unset in dev/test -- the button
    # still renders, the route just declines with a friendly message
    # instead of calling out to Google with empty credentials.
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
