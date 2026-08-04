from flask import render_template, session

from ..extensions import mysql
from ..decorators import login_required


def register(app):
    @app.route('/dashboard')
    @login_required
    def dashboard():
        cur = mysql.connection.cursor()
        # Single optimized query
        cur.execute("""
            SELECT
                (SELECT COUNT(*) FROM students)   AS ts,
                (SELECT COUNT(*) FROM companies)  AS tc,
                (SELECT COUNT(*) FROM placements) AS tp,
                (SELECT AVG(c.package) FROM placements p JOIN companies c ON p.company_id=c.company_id) AS avg_p,
                (SELECT MAX(c.package) FROM placements p JOIN companies c ON p.company_id=c.company_id) AS max_p
        """)
        s = cur.fetchone()
        total_students   = s[0] or 0
        total_companies  = s[1] or 0
        total_placements = s[2] or 0
        avg_package      = s[3] or 0
        max_package      = s[4] or 0

        cur.execute("""
            SELECT s.name, c.company_name, c.package, p.year, p.status
            FROM placements p
            JOIN students s ON p.student_id=s.student_id
            JOIN companies c ON p.company_id=c.company_id
            ORDER BY p.placement_id DESC LIMIT 5
        """)
        recent = cur.fetchall()

        notifications = []
        if session.get('role') == 'admin':
            cur.execute("""
                SELECT s.name, c.company_name, c.package, p.status
                FROM placements p
                JOIN students s ON p.student_id=s.student_id
                JOIN companies c ON p.company_id=c.company_id
                ORDER BY p.placement_id DESC LIMIT 3
            """)
            for p in cur.fetchall():
                notifications.append({'icon':'🎉', 'message':f'{p[0]} placed at {p[1]} — {p[2]} LPA', 'type':'success'})
            cur.execute("SELECT COUNT(*) FROM students WHERE role='student'")
            ns = cur.fetchone()[0]
            if ns:
                notifications.append({'icon':'👨‍🎓', 'message':f'Total {ns} student(s) registered', 'type':'info'})

        if session.get('role') == 'student':
            cur.execute("""
                SELECT c.company_name, c.package, p.status
                FROM placements p JOIN companies c ON p.company_id=c.company_id
                WHERE p.student_id=%s ORDER BY p.placement_id DESC LIMIT 1
            """, (session['user_id'],))
            mp = cur.fetchone()
            if mp:
                notifications.append({'icon':'🎉', 'message':f'You are placed at {mp[0]} — {mp[1]} LPA!', 'type':'success'})
            else:
                notifications.append({'icon':'💡', 'message':'Check ML Predictor to know your placement chances!', 'type':'info'})

        cur.close()
        return render_template('dashboard.html',
            total_students=total_students, total_companies=total_companies,
            total_placements=total_placements,
            avg_package=round(avg_package, 2), max_package=round(max_package, 2),
            recent=recent, notifications=notifications, user_name=session['user_name'])
