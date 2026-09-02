import hashlib
import hmac
from functools import wraps

from flask import current_app, session, redirect, url_for, flash

from .extensions import mysql


def auth_version(password_hash):
    return hmac.new(
        current_app.secret_key.encode(), password_hash.encode(), hashlib.sha256,
    ).hexdigest()


def _current_user():
    if 'logged_in' not in session or not session.get('user_id'):
        return None
    cur = mysql.connection.cursor()
    cur.execute(
        'SELECT name, role, password FROM students WHERE student_id=%s',
        (session['user_id'],),
    )
    user = cur.fetchone()
    cur.close()
    if not user or not hmac.compare_digest(
            session.get('auth_version', ''), auth_version(user[2])):
        session.clear()
        return None
    session['user_name'] = user[0]
    session['role'] = user[1]
    return user


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not _current_user():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = _current_user()
        if not user:
            return redirect(url_for('login'))
        if user[1] != 'admin':
            flash('Access denied!', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated
