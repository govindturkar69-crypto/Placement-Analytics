import logging
import re
import secrets
from datetime import datetime, timedelta

import pymysql

from flask import render_template, request, redirect, url_for, session, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash


from ..email import send_email
from ..extensions import mysql, limiter, oauth

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
PASSWORD_RE = re.compile(r'^(?=.*[A-Za-z])(?=.*\d).{8,}$')

OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
OTP_MAX_RESENDS = 3
OTP_RESEND_COOLDOWN_SECONDS = 60
# How long a successful OTP verification stays good for before the user
# has to re-verify -- keeps a browser tab left open on the reset-password
# screen from being usable indefinitely.
OTP_VERIFIED_TTL_MINUTES = 10

INVALID_OTP_MESSAGE = 'That code is incorrect or has expired. Please try again or request a new one.'


def _generate_otp():
    return ''.join(secrets.choice('0123456789') for _ in range(OTP_LENGTH))


def _mask_email(email):
    """For logs and the Verify OTP screen -- never the full address."""
    local, _, domain = email.partition('@')
    if len(local) <= 2:
        masked_local = local[:1] + '*' * max(len(local) - 1, 1)
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    return f'{masked_local}@{domain}' if domain else masked_local


def _send_otp_email(email, name, otp):
    body = f'''Hello {name},

Your password reset code is: {otp}

This code expires in {OTP_EXPIRY_MINUTES} minutes and can only be used once.
If you did not request this, ignore this email -- your password will not be changed.

Regards, Placement Analytics Team'''
    send_email(email, 'Your Password Reset Code – Placement Analytics', body)


def _issue_otp(email):
    """Creates and emails a fresh OTP if `email` belongs to a real account.
    Silently does nothing otherwise -- callers must respond identically
    either way so this never becomes an account-enumeration oracle.
    """
    cur = mysql.connection.cursor()
    # Opportunistic cleanup so this table doesn't grow unbounded.
    cur.execute("DELETE FROM password_otps WHERE expires_at < %s", (datetime.now(),))
    cur.execute("SELECT student_id, name FROM students WHERE email=%s", (email,))
    user = cur.fetchone()
    if user:
        cur.execute("DELETE FROM password_otps WHERE email=%s", (email,))  # only one active code
        otp = _generate_otp()
        expires_at = datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
        cur.execute(
            "INSERT INTO password_otps(email, otp_hash, expires_at) VALUES(%s, %s, %s)",
            (email, generate_password_hash(otp), expires_at)
        )
        mysql.connection.commit()
        _send_otp_email(email, user[1], otp)
        logger.info('Password reset OTP issued for %s', _mask_email(email))
    else:
        mysql.connection.commit()
        logger.info('Password reset requested for unregistered email %s', _mask_email(email))
    cur.close()


def register(app):
    BASE_URL = 'https://placement-analytics.onrender.com'

    @app.route('/robots.txt')
    def robots_txt():
        content = (
            "User-agent: *\n"
            "Disallow: /dashboard\n"
            "Disallow: /students\n"
            "Disallow: /add_student\n"
            "Disallow: /edit_student/\n"
            "Disallow: /delete_student/\n"
            "Disallow: /companies\n"
            "Disallow: /add_company\n"
            "Disallow: /edit_company/\n"
            "Disallow: /delete_company/\n"
            "Disallow: /placements\n"
            "Disallow: /add_placement\n"
            "Disallow: /delete_placement/\n"
            "Disallow: /analytics\n"
            "Disallow: /reports\n"
            "Disallow: /predict\n"
            "Disallow: /profile\n"
            "Disallow: /change_password\n"
            "Disallow: /upload_csv\n"
            "Disallow: /api/\n"
            "Disallow: /login/google/callback\n"
            "Disallow: /register/google/callback\n"
            "Disallow: /register/google/complete\n"
            "Allow: /\n"
            "Allow: /register\n"
            "Allow: /login\n"
            "Allow: /forgot_password\n"
            f"\nSitemap: {BASE_URL}/sitemap.xml\n"
        )
        return Response(content, mimetype='text/plain')

    @app.route('/sitemap.xml')
    def sitemap_xml():
        pages = [
            {'loc': f'{BASE_URL}/',          'priority': '1.0', 'changefreq': 'weekly'},
            {'loc': f'{BASE_URL}/register',   'priority': '0.8', 'changefreq': 'monthly'},
            {'loc': f'{BASE_URL}/login',      'priority': '0.6', 'changefreq': 'monthly'},
            {'loc': f'{BASE_URL}/forgot_password', 'priority': '0.3', 'changefreq': 'yearly'},
        ]
        lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for p in pages:
            lines += [
                '  <url>',
                f'    <loc>{p["loc"]}</loc>',
                f'    <changefreq>{p["changefreq"]}</changefreq>',
                f'    <priority>{p["priority"]}</priority>',
                '  </url>',
            ]
        lines.append('</urlset>')
        return Response('\n'.join(lines), mimetype='application/xml')

    @app.route('/')
    def index():
        if 'logged_in' in session:
            return redirect(url_for('dashboard'))
        return render_template('landing.html')

    @app.route('/register', methods=['GET', 'POST'])
    @limiter.limit("5 per minute", methods=["POST"])
    def register():
        if 'logged_in' in session:
            return redirect(url_for('dashboard'))
        if request.method == 'POST':
            name     = request.form.get('name', '').strip()
            email    = request.form.get('email', '').strip().lower()
            branch   = request.form.get('branch', '').strip()
            cgpa_str = request.form.get('cgpa', '').strip()
            skills   = request.form.get('skills', '').strip()
            password = request.form.get('password', '')
            confirm  = request.form.get('confirm_password', '')

            if not name or not email or not branch or not cgpa_str or not password or not confirm:
                flash('All fields except skills are required.', 'danger')
                return render_template('register.html')

            if not EMAIL_RE.match(email):
                flash('Please enter a valid email address.', 'danger')
                return render_template('register.html')

            try:
                cgpa = float(cgpa_str)
                if not (0.0 <= cgpa <= 10.0):
                    raise ValueError
            except ValueError:
                flash('CGPA must be a number between 0.0 and 10.0.', 'danger')
                return render_template('register.html')

            if not PASSWORD_RE.match(password):
                flash('Password must be at least 8 characters and include a letter and a number.', 'danger')
                return render_template('register.html')

            if password != confirm:
                flash('Passwords do not match.', 'danger')
                return render_template('register.html')

            cur = mysql.connection.cursor()
            try:
                cur.execute(
                    "INSERT INTO students(name,email,branch,cgpa,skills,password,role)"
                    " VALUES(%s,%s,%s,%s,%s,%s,'student')",
                    (name, email, branch, cgpa, skills, generate_password_hash(password))
                )
                mysql.connection.commit()
            except pymysql.err.IntegrityError:
                mysql.connection.rollback()
                flash('That email is already registered. Please sign in or use a different email.', 'danger')
                return render_template('register.html')
            finally:
                cur.close()

            logger.info('New student registered: %s', _mask_email(email))
            flash('Account created successfully! Please sign in with your new credentials.', 'success')
            return redirect(url_for('login'))

        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    @limiter.limit("5 per minute", methods=["POST"])
    def login():
        if request.method == 'POST':
            email    = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            if not email or not password:
                flash('Please fill in all fields.', 'danger')
                return render_template('login.html')
            cur = mysql.connection.cursor()
            cur.execute(
                "SELECT student_id, name, role, password FROM students WHERE email=%s",
                (email,)
            )
            user = cur.fetchone()
            cur.close()
            if user and check_password_hash(user[3], password):
                session.permanent    = request.form.get('remember_me') == 'on'
                session['logged_in'] = True
                session['user_id']   = user[0]
                session['user_name'] = user[1]
                session['role']      = user[2]
                return redirect(url_for('dashboard'))
            flash('Invalid email or password.', 'danger')
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))

    def _google_configured():
        return bool(app.config.get('GOOGLE_CLIENT_ID') and app.config.get('GOOGLE_CLIENT_SECRET'))

    @app.route('/login/google')
    def login_google():
        if not _google_configured():
            flash('Google sign-in is not set up for this site yet.', 'danger')
            return redirect(url_for('login'))
        redirect_uri = url_for('login_google_callback', _external=True)
        return oauth.google.authorize_redirect(redirect_uri)

    @app.route('/login/google/callback')
    def login_google_callback():
        if not _google_configured():
            flash('Google sign-in is not set up for this site yet.', 'danger')
            return redirect(url_for('login'))
        try:
            token = oauth.google.authorize_access_token()
            userinfo = token.get('userinfo') or {}
            email = userinfo.get('email')
        except Exception:
            email = None
        if not email:
            flash('Google sign-in failed. Please try again or use your email and password.', 'danger')
            return redirect(url_for('login'))

        cur = mysql.connection.cursor()
        cur.execute("SELECT student_id, name, role FROM students WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()
        if not user:
            flash(f'No account found for {email}. Contact your placement cell admin.', 'danger')
            return redirect(url_for('login'))

        session.permanent    = True
        session['logged_in'] = True
        session['user_id']   = user[0]
        session['user_name'] = user[1]
        session['role']      = user[2]
        return redirect(url_for('dashboard'))

    # ── Google Registration flow ────────────────────────────────────────────
    # Separate from login/google so the Register page can link here.
    # Step 1: kick off OAuth (same scopes, different callback URL).
    # Step 2: callback -- if email already has an account, log them in;
    #         if email is new, stash name+email in session and go to step 3.
    # Step 3: collect the fields Google can't supply (branch, CGPA, skills).

    @app.route('/register/google')
    def register_google():
        if 'logged_in' in session:
            return redirect(url_for('dashboard'))
        if not _google_configured():
            flash('Google sign-in is not set up for this site yet.', 'danger')
            return redirect(url_for('register'))
        redirect_uri = url_for('register_google_callback', _external=True)
        return oauth.google.authorize_redirect(redirect_uri)

    @app.route('/register/google/callback')
    def register_google_callback():
        if not _google_configured():
            flash('Google sign-in is not set up for this site yet.', 'danger')
            return redirect(url_for('register'))
        try:
            token    = oauth.google.authorize_access_token()
            userinfo = token.get('userinfo') or {}
            email    = (userinfo.get('email') or '').strip().lower()
            name     = (userinfo.get('name') or '').strip()
        except Exception:
            email = name = ''

        if not email:
            flash('Google sign-in failed. Please try again or use your email and password.', 'danger')
            return redirect(url_for('register'))

        # If there's already an account with this Gmail address, just log in.
        cur = mysql.connection.cursor()
        cur.execute("SELECT student_id, name, role FROM students WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()
        if user:
            session.permanent    = True
            session['logged_in'] = True
            session['user_id']   = user[0]
            session['user_name'] = user[1]
            session['role']      = user[2]
            flash('Welcome back! You\'ve been signed in with your Google account.', 'success')
            return redirect(url_for('dashboard'))

        # New email – stash the Google-supplied fields and collect the rest.
        session['google_pending_email'] = email
        session['google_pending_name']  = name
        logger.info('Google registration pending for %s', _mask_email(email))
        return redirect(url_for('register_google_complete'))

    @app.route('/register/google/complete', methods=['GET', 'POST'])
    def register_google_complete():
        """Step 3: collect branch / CGPA / skills then create the account."""
        email = session.get('google_pending_email')
        name  = session.get('google_pending_name', '')
        if not email:
            # Guard: someone navigated here directly without going through OAuth.
            flash('Please use the "Continue with Google" button to register.', 'danger')
            return redirect(url_for('register'))

        if 'logged_in' in session:
            # Already logged-in; clean up and go to dashboard.
            session.pop('google_pending_email', None)
            session.pop('google_pending_name',  None)
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            branch   = request.form.get('branch', '').strip()
            cgpa_str = request.form.get('cgpa', '').strip()
            skills   = request.form.get('skills', '').strip()

            if not branch or not cgpa_str:
                flash('Branch and CGPA are required.', 'danger')
                return render_template('register_google_complete.html', name=name, email=email)

            try:
                cgpa = float(cgpa_str)
                if not (0.0 <= cgpa <= 10.0):
                    raise ValueError
            except ValueError:
                flash('CGPA must be a number between 0.0 and 10.0.', 'danger')
                return render_template('register_google_complete.html', name=name, email=email)

            # Google-registered accounts have no password; use an unusable hash
            # so the column stays NOT NULL without enabling password login.
            unusable_hash = 'google:' + secrets.token_hex(16)

            cur = mysql.connection.cursor()
            try:
                cur.execute(
                    "INSERT INTO students(name, email, branch, cgpa, skills, password, role)"
                    " VALUES(%s, %s, %s, %s, %s, %s, 'student')",
                    (name, email, branch, cgpa, skills, unusable_hash)
                )
                mysql.connection.commit()
                student_id = cur.lastrowid
            except pymysql.err.IntegrityError:
                mysql.connection.rollback()
                cur.close()
                # Race condition: another tab or request registered the same email.
                flash('That email is already registered. Please sign in instead.', 'danger')
                session.pop('google_pending_email', None)
                session.pop('google_pending_name',  None)
                return redirect(url_for('login'))
            finally:
                cur.close()

            # Clear the pending state and log the user straight in.
            session.pop('google_pending_email', None)
            session.pop('google_pending_name',  None)
            session.permanent    = True
            session['logged_in'] = True
            session['user_id']   = student_id
            session['user_name'] = name
            session['role']      = 'student'
            logger.info('New student registered via Google: %s', _mask_email(email))
            flash(f'Welcome, {name}! Your account has been created.', 'success')
            return redirect(url_for('dashboard'))

        return render_template('register_google_complete.html', name=name, email=email)

    @app.route('/forgot_password', methods=['GET', 'POST'])
    @limiter.limit("3 per minute", methods=["POST"])
    def forgot_password():
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            if not EMAIL_RE.match(email):
                flash('Please enter a valid email address.', 'danger')
                return render_template('forgot_password.html')

            _issue_otp(email)

            session['reset_email']      = email
            session['otp_last_sent_at'] = datetime.now().isoformat()
            session['otp_resend_count'] = 0
            session.pop('otp_verified_at', None)
            return redirect(url_for('verify_otp'))
        return render_template('forgot_password.html')

    @app.route('/verify_otp', methods=['GET', 'POST'])
    @limiter.limit("10 per minute", methods=["POST"])
    def verify_otp():
        email = session.get('reset_email')
        if not email:
            flash('Start the password reset process again.', 'danger')
            return redirect(url_for('forgot_password'))

        if request.method == 'POST':
            code = request.form.get('otp', '').strip()
            cur = mysql.connection.cursor()
            cur.execute(
                "SELECT id, otp_hash, expires_at, attempts FROM password_otps "
                "WHERE email=%s ORDER BY created_at DESC LIMIT 1",
                (email,)
            )
            row = cur.fetchone()

            valid = False
            if row:
                otp_id, otp_hash, expires_at, attempts = row
                if (attempts < OTP_MAX_ATTEMPTS
                        and datetime.now() <= expires_at
                        and check_password_hash(otp_hash, code)):
                    valid = True
                    cur.execute("DELETE FROM password_otps WHERE id=%s", (otp_id,))  # one-time use
                else:
                    cur.execute("UPDATE password_otps SET attempts=attempts+1 WHERE id=%s", (otp_id,))
            mysql.connection.commit()
            cur.close()

            if valid:
                session['otp_verified_at'] = datetime.now().isoformat()
                logger.info('OTP verified for %s', _mask_email(email))
                return redirect(url_for('reset_password'))

            logger.warning('Failed OTP verification attempt for %s', _mask_email(email))
            flash(INVALID_OTP_MESSAGE, 'danger')

        last_sent = session.get('otp_last_sent_at')
        resend_wait_seconds = 0
        if last_sent:
            elapsed = (datetime.now() - datetime.fromisoformat(last_sent)).total_seconds()
            resend_wait_seconds = max(0, int(OTP_RESEND_COOLDOWN_SECONDS - elapsed))
        return render_template(
            'verify_otp.html',
            masked_email=_mask_email(email),
            resend_wait_seconds=resend_wait_seconds,
        )

    @app.route('/resend_otp', methods=['POST'])
    @limiter.limit("5 per 10 minutes")
    def resend_otp():
        email = session.get('reset_email')
        if not email:
            flash('Start the password reset process again.', 'danger')
            return redirect(url_for('forgot_password'))

        last_sent = session.get('otp_last_sent_at')
        if last_sent and (datetime.now() - datetime.fromisoformat(last_sent)).total_seconds() < OTP_RESEND_COOLDOWN_SECONDS:
            flash('Please wait a moment before requesting another code.', 'danger')
            return redirect(url_for('verify_otp'))

        if session.get('otp_resend_count', 0) >= OTP_MAX_RESENDS:
            flash("You've reached the resend limit. Start over with your email.", 'danger')
            session.pop('reset_email', None)
            return redirect(url_for('forgot_password'))

        _issue_otp(email)
        session['otp_last_sent_at'] = datetime.now().isoformat()
        session['otp_resend_count'] = session.get('otp_resend_count', 0) + 1
        flash('A new code has been sent.', 'success')
        return redirect(url_for('verify_otp'))

    @app.route('/reset_password', methods=['GET', 'POST'])
    def reset_password():
        email       = session.get('reset_email')
        verified_at = session.get('otp_verified_at')
        expired = (
            not email or not verified_at
            or (datetime.now() - datetime.fromisoformat(verified_at)).total_seconds() > OTP_VERIFIED_TTL_MINUTES * 60
        )
        if expired:
            session.pop('otp_verified_at', None)
            flash('Your verification has expired. Please start again.', 'danger')
            return redirect(url_for('forgot_password'))

        if request.method == 'POST':
            new_password     = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            if not PASSWORD_RE.match(new_password):
                flash('Password must be at least 8 characters and include a letter and a number.', 'danger')
                return render_template('reset_password.html')
            if new_password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template('reset_password.html')

            hashed = generate_password_hash(new_password)
            cur = mysql.connection.cursor()
            cur.execute("UPDATE students SET password=%s WHERE email=%s", (hashed, email))
            cur.execute("DELETE FROM password_otps WHERE email=%s", (email,))
            mysql.connection.commit()
            cur.close()

            session.pop('reset_email', None)
            session.pop('otp_verified_at', None)
            session.pop('otp_last_sent_at', None)
            session.pop('otp_resend_count', None)
            logger.info('Password reset completed for %s', _mask_email(email))
            flash('Password reset successful! Please login.', 'success')
            return redirect(url_for('login'))
        return render_template('reset_password.html')
