from flask import render_template, redirect, url_for, flash
from flask_wtf.csrf import CSRFError

from .utils import safe_redirect_back


def register(app):
    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html'), 500

    @app.errorhandler(429)
    def rate_limited(e):
        flash('Too many attempts! Please wait a minute and try again.', 'danger')
        return redirect(url_for('login'))

    @app.errorhandler(413)
    def too_large(e):
        flash('That file is too large. Please keep uploads under 16MB.', 'danger')
        return safe_redirect_back('dashboard')

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        flash('Your session expired. Please try that again.', 'danger')
        return safe_redirect_back('login')
