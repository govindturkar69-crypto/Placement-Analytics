from flask import render_template, session, jsonify

from ..extensions import mysql
from ..decorators import login_required


def register(app):
    @app.route('/profile')
    @login_required
    def profile():
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM students WHERE student_id=%s", (session['user_id'],))
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

    @app.route('/api/stats')
    @login_required
    def api_stats():
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT (SELECT COUNT(*) FROM students) AS s,
                   (SELECT COUNT(*) FROM placements) AS p,
                   (SELECT AVG(c.package) FROM placements pl JOIN companies c ON pl.company_id=c.company_id) AS a
        """)
        r = cur.fetchone(); cur.close()
        students, placed, avg_pkg = r[0] or 0, r[1] or 0, r[2] or 0
        return jsonify({
            'total_students': students, 'total_placed': placed,
            'placement_rate': round((placed/students)*100,1) if students else 0,
            'avg_package': round(avg_pkg, 2)
        })
