from flask import render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import mysql, limiter
from ..decorators import login_required
from .auth import PASSWORD_RE


def register(app):
    @app.route('/profile')
    @login_required
    def profile():
        cur = mysql.connection.cursor()
        cur.execute("SELECT student_id, name, email, branch, cgpa, skills FROM students WHERE student_id=%s", (session['user_id'],))
        student = cur.fetchone()
        cur.execute("""
            SELECT c.company_name, c.package, p.year, p.status
            FROM placements p JOIN companies c ON p.company_id=c.company_id
            WHERE p.student_id=%s ORDER BY p.year DESC
        """, (session['user_id'],))
        my_placements = cur.fetchall()
        cur.close()
        return render_template('profile.html',
            student=student, my_placements=my_placements, user_name=session['user_name'])

    @app.route('/change_password', methods=['GET', 'POST'])
    @login_required
    @limiter.limit("5 per minute", methods=["POST"])
    def change_password():
        if request.method == 'POST':
            current_password = request.form.get('current_password', '')
            new_password     = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            cur = mysql.connection.cursor()
            cur.execute("SELECT password FROM students WHERE student_id=%s", (session['user_id'],))
            row = cur.fetchone()

            if not row or not check_password_hash(row[0], current_password):
                cur.close()
                flash('Current password is incorrect.', 'danger')
                return render_template('change_password.html', user_name=session['user_name'])

            if not PASSWORD_RE.match(new_password):
                cur.close()
                flash('New password must be at least 8 characters and include a letter and a number.', 'danger')
                return render_template('change_password.html', user_name=session['user_name'])

            if new_password != confirm_password:
                cur.close()
                flash('New passwords do not match.', 'danger')
                return render_template('change_password.html', user_name=session['user_name'])

            hashed = generate_password_hash(new_password)
            cur.execute("UPDATE students SET password=%s WHERE student_id=%s", (hashed, session['user_id']))
            mysql.connection.commit()
            cur.close()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('profile'))
        return render_template('change_password.html', user_name=session['user_name'])

    @app.route('/api/stats')
    @login_required
    def api_stats():
        cur = mysql.connection.cursor()
        if session.get('role') == 'admin':
            cur.execute("""
                SELECT (SELECT COUNT(*) FROM students) AS s,
                       (SELECT COUNT(*) FROM placements) AS p,
                       (SELECT AVG(c.package) FROM placements pl JOIN companies c ON pl.company_id=c.company_id) AS a
            """)
        else:
            cur.execute("""
                SELECT 1 AS s,
                       (SELECT COUNT(*) FROM placements WHERE student_id=%s) AS p,
                       (SELECT AVG(c.package) FROM placements pl JOIN companies c ON pl.company_id=c.company_id WHERE pl.student_id=%s) AS a
            """, (session['user_id'], session['user_id']))
        r = cur.fetchone(); cur.close()
        students, placed, avg_pkg = r[0] or 0, r[1] or 0, r[2] or 0
        return jsonify({
            'total_students': students, 'total_placed': placed,
            'placement_rate': round((placed/students)*100,1) if students else 0,
            'avg_package': round(avg_pkg, 2)
        })
