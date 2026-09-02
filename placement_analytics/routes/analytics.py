from collections import Counter

from flask import render_template, session

from ..extensions import mysql
from ..decorators import admin_required


def register(app):
    @app.route('/analytics')
    @admin_required
    def analytics():
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT c.company_name, COUNT(*) AS cnt
            FROM placements p JOIN companies c ON p.company_id=c.company_id
            GROUP BY c.company_name ORDER BY cnt DESC LIMIT 10
        """)
        cd = cur.fetchall()
        cur.execute("SELECT year, COUNT(*) AS cnt FROM placements GROUP BY year ORDER BY year")
        yd = cur.fetchall()
        cur.execute("SELECT COUNT(DISTINCT student_id) FROM placements")
        placed_students = cur.fetchone()[0] or 0
        cur.execute("""
            SELECT s.branch, COUNT(*) AS cnt
            FROM placements p JOIN students s ON p.student_id=s.student_id
            GROUP BY s.branch ORDER BY cnt DESC
        """)
        bd = cur.fetchall()
        cur.execute("""
            SELECT c.company_name, c.package
            FROM placements p JOIN companies c ON p.company_id=c.company_id
            ORDER BY c.package DESC LIMIT 10
        """)
        pd = cur.fetchall()
        cur.execute("SELECT required_skills FROM companies")
        all_skills = []
        for row in cur.fetchall():
            if row[0]: all_skills.extend([s.strip() for s in row[0].split(',')])
        sc = Counter(all_skills).most_common(8)
        cur.close()

        company_labels = [r[0] for r in cd]
        company_counts = [r[1] for r in cd]
        year_labels    = [str(r[0]) for r in yd]
        year_counts    = [r[1] for r in yd]
        branch_labels  = [r[0] for r in bd]
        branch_counts  = [r[1] for r in bd]
        pkg_labels     = [r[0] for r in pd]
        pkg_values     = [r[1] for r in pd]
        skill_labels   = [s[0] for s in sc]
        skill_values   = [s[1] for s in sc]

        return render_template('analytics.html',
            company_labels=company_labels,
            company_counts=company_counts,
            year_labels=year_labels,
            year_counts=year_counts,
            branch_labels=branch_labels,
            branch_counts=branch_counts,
            pkg_labels=pkg_labels,
            pkg_values=pkg_values,
            skill_labels=skill_labels,
            skill_values=skill_values,
            kpi_companies=len(company_labels),
            kpi_placed=placed_students,
            kpi_branches=len(branch_labels),
            kpi_skills=len(skill_labels),
            user_name=session['user_name'])
