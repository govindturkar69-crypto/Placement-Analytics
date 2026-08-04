import os

import pymysql
from flask import render_template, request, redirect, url_for, session, flash
from flask_mail import Message

from ..extensions import mysql, mail
from ..decorators import login_required, admin_required


def register(app):
    @app.route('/placements')
    @login_required
    def placements():
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT p.placement_id, s.name, c.company_name, c.package, p.year, p.status
            FROM placements p
            JOIN students s ON p.student_id=s.student_id
            JOIN companies c ON p.company_id=c.company_id
            ORDER BY p.year DESC
        """)
        all_placements = cur.fetchall()
        cur.close()
        return render_template('placements.html', placements=all_placements, user_name=session['user_name'])

    @app.route('/add_placement', methods=['GET', 'POST'])
    @admin_required
    def add_placement():
        cur = mysql.connection.cursor()
        if request.method == 'POST':
            try:
                student_id = int(request.form['student_id'])
                company_id = int(request.form['company_id'])
                year       = int(request.form['year'])
            except ValueError:
                cur.close()
                flash('Please select a valid student, company, and year.', 'danger')
                return redirect(url_for('add_placement'))
            status = request.form['status']
            try:
                cur.execute(
                    "INSERT INTO placements(student_id,company_id,year,status) VALUES(%s,%s,%s,%s)",
                    (student_id, company_id, year, status)
                )
                mysql.connection.commit()
            except pymysql.err.IntegrityError:
                mysql.connection.rollback()
                cur.close()
                flash('That student or company no longer exists.', 'danger')
                return redirect(url_for('add_placement'))
            cur.execute("SELECT name, email FROM students WHERE student_id=%s", (student_id,))
            student = cur.fetchone()
            cur.execute("SELECT company_name, package FROM companies WHERE company_id=%s", (company_id,))
            company = cur.fetchone()
            cur.close()
            if student and company and os.environ.get('MAIL_USERNAME'):
                try:
                    msg = Message('🎉 Congratulations! Placement Confirmed',
                        sender=os.environ.get('MAIL_USERNAME'), recipients=[student[1]])
                    msg.body = f'''Dear {student[0]},

🎉 You have been placed at {company[0]}!

Company : {company[0]}
Package : {company[1]} LPA
Year    : {year}
Status  : {status}

Best Regards, Placement Analytics Team'''
                    mail.send(msg)
                except Exception:
                    pass
            flash('Placement recorded successfully!', 'success')
            return redirect(url_for('placements'))
        cur.execute("SELECT student_id, name FROM students ORDER BY name")
        students = cur.fetchall()
        cur.execute("SELECT company_id, company_name FROM companies ORDER BY company_name")
        companies = cur.fetchall()
        cur.close()
        return render_template('add_placement.html',
            students=students, companies=companies, user_name=session['user_name'])

    @app.route('/delete_placement/<int:placement_id>', methods=['POST'])
    @admin_required
    def delete_placement(placement_id):
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM placements WHERE placement_id=%s", (placement_id,))
        mysql.connection.commit()
        deleted = cur.rowcount
        cur.close()
        if deleted:
            flash('Placement deleted successfully!', 'success')
        else:
            flash('Placement not found — it may have already been deleted.', 'danger')
        return redirect(url_for('placements'))
