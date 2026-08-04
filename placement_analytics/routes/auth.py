import os
import secrets
from datetime import datetime, timedelta

from flask import render_template, request, redirect, url_for, session, flash
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash

from ..extensions import mysql, mail, limiter


def register(app):
    @app.route('/')
    def index():
        if 'logged_in' in session:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

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

    @app.route('/forgot_password', methods=['GET', 'POST'])
    @limiter.limit("3 per minute", methods=["POST"])
    def forgot_password():
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            cur   = mysql.connection.cursor()
            cur.execute("SELECT student_id, name FROM students WHERE email=%s", (email,))
            user  = cur.fetchone()
            if user:
                # Opportunistic cleanup so this table doesn't grow unbounded.
                cur.execute("DELETE FROM password_resets WHERE expires_at < %s", (datetime.now(),))
                token = secrets.token_urlsafe(32)
                expires_at = datetime.now() + timedelta(hours=1)
                cur.execute(
                    "INSERT INTO password_resets(token, email, expires_at) VALUES(%s, %s, %s)",
                    (token, email, expires_at)
                )
                mysql.connection.commit()
                reset_link = url_for('reset_password', token=token, _external=True)
                try:
                    msg = Message(
                        'Password Reset – Placement Analytics',
                        sender=os.environ.get('MAIL_USERNAME'),
                        recipients=[email]
                    )
                    msg.body = f'''Hello {user[1]},

Click the link below to reset your password (valid 1 hour):
{reset_link}

This link works only once.
If you did not request this, ignore this email.

Regards, Placement Analytics Team'''
                    mail.send(msg)
                except Exception:
                    pass
            cur.close()
            # Don't reveal whether email exists (security best practice)
            flash('If that email exists, a reset link has been sent.', 'success')
        return render_template('forgot_password.html')

    @app.route('/reset_password/<token>', methods=['GET', 'POST'])
    def reset_password(token):
        cur = mysql.connection.cursor()
        cur.execute("SELECT email, expires_at FROM password_resets WHERE token=%s", (token,))
        row = cur.fetchone()
        if not row:
            cur.close()
            flash('Invalid or expired link!', 'danger')
            return redirect(url_for('login'))
        email, expires_at = row
        if datetime.now() > expires_at:
            cur.execute("DELETE FROM password_resets WHERE token=%s", (token,))
            mysql.connection.commit()
            cur.close()
            flash('Reset link expired! Please request a new one.', 'danger')
            return redirect(url_for('forgot_password'))
        if request.method == 'POST':
            new_password = request.form.get('password', '')
            if len(new_password) < 6:
                cur.close()
                flash('Password must be at least 6 characters.', 'danger')
                return render_template('reset_password.html', token=token)
            hashed = generate_password_hash(new_password)
            cur.execute("UPDATE students SET password=%s WHERE email=%s", (hashed, email))
            cur.execute("DELETE FROM password_resets WHERE token=%s", (token,))
            mysql.connection.commit()
            cur.close()
            flash('Password reset successful! Please login.', 'success')
            return redirect(url_for('login'))
        cur.close()
        return render_template('reset_password.html', token=token)
