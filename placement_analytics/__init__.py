from dotenv import load_dotenv
load_dotenv()

import gzip
import io

from flask import Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .extensions import mysql, mail, csrf, limiter, oauth
from . import errors
from .routes import register_all


def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config.from_object(Config)

    # Render (and most PaaS) terminate TLS at the edge and forward internally
    # over plain HTTP -- without this, request.remote_addr is always the
    # proxy's IP (breaking per-client rate limiting) and url_for(_external=True)
    # generates http:// links instead of https://.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    mysql.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )

    errors.register(app)
    register_all(app)

    @app.after_request
    def after_request(response):
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options']         = 'SAMEORIGIN'
        response.headers['X-XSS-Protection']        = '1; mode=block'
        response.headers['Referrer-Policy']         = 'strict-origin-when-cross-origin'
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        # Cache
        if request.endpoint == 'static':
            response.headers['Cache-Control'] = 'public, max-age=31536000'
        else:
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        # Gzip
        if (200 <= response.status_code < 300
                and 'Content-Encoding' not in response.headers
                and len(response.get_data()) >= 500
                and 'gzip' in request.headers.get('Accept-Encoding', '')):
            try:
                buf = io.BytesIO()
                with gzip.GzipFile(mode='wb', fileobj=buf) as f:
                    f.write(response.get_data())
                response.set_data(buf.getvalue())
                response.headers['Content-Encoding'] = 'gzip'
                response.headers['Content-Length']   = len(response.get_data())
            except Exception:
                pass
        return response

    return app
