import csv
import io
import math

import pymysql
from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash

from ..extensions import mysql
from ..decorators import admin_required
from ..utils import any_blank
from .auth import EMAIL_RE, PASSWORD_RE


def register(app):
    @app.route('/students')
    @admin_required
    def students():
        page     = max(1, request.args.get('page', 1, type=int))
        per_page = 20
        offset   = (page - 1) * per_page
        cur      = mysql.connection.cursor()
        cur.execute("SELECT COUNT(*) FROM students")
        total = cur.fetchone()[0]
        cur.execute("""
            SELECT student_id, name, email, branch, cgpa, skills
            FROM students ORDER BY student_id DESC LIMIT %s OFFSET %s
        """, (per_page, offset))
        all_students = cur.fetchall()
        cur.close()
        total_pages = (total + per_page - 1) // per_page
        return render_template('students.html',
            students=all_students, user_name=session['user_name'],
            page=page, total_pages=total_pages, total=total)

    @app.route('/add_student', methods=['GET', 'POST'])
    @admin_required
    def add_student():
        if request.method == 'POST':
            try:
                cgpa = float(request.form['cgpa'])
                if not math.isfinite(cgpa) or not 0.0 <= cgpa <= 10.0:
                    raise ValueError
            except ValueError:
                flash('CGPA must be a number between 0.0 and 10.0.', 'danger')
                return render_template('add_student.html', user_name=session['user_name'])
            if any_blank(request.form.get('name'), request.form.get('email'), request.form.get('branch')):
                flash('Name, email, and branch are required.', 'danger')
                return render_template('add_student.html', user_name=session['user_name'])
            if not EMAIL_RE.match(request.form['email'].strip().lower()):
                flash('Please enter a valid email address.', 'danger')
                return render_template('add_student.html', user_name=session['user_name'])
            if not PASSWORD_RE.match(request.form.get('password', '')):
                flash('Password must be at least 8 characters and include a letter and a number.', 'danger')
                return render_template('add_student.html', user_name=session['user_name'])
            password = generate_password_hash(request.form['password'])
            cur = mysql.connection.cursor()
            try:
                cur.execute(
                    "INSERT INTO students(name,email,branch,cgpa,skills,password) VALUES(%s,%s,%s,%s,%s,%s)",
                    (request.form['name'], request.form['email'].strip().lower(), request.form['branch'],
                     cgpa, request.form['skills'], password)
                )
                mysql.connection.commit()
                flash('Student added successfully!', 'success')
                return redirect(url_for('students'))
            except pymysql.err.IntegrityError:
                mysql.connection.rollback()
                flash('That email is already registered to another student.', 'danger')
                return render_template('add_student.html', user_name=session['user_name'])
            finally:
                cur.close()
        return render_template('add_student.html', user_name=session['user_name'])

    @app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
    @admin_required
    def edit_student(student_id):
        cur = mysql.connection.cursor()
        if request.method == 'POST':
            try:
                cgpa = float(request.form['cgpa'])
                if not math.isfinite(cgpa) or not 0.0 <= cgpa <= 10.0:
                    raise ValueError
            except ValueError:
                cur.close()
                flash('CGPA must be a number between 0.0 and 10.0.', 'danger')
                return redirect(url_for('edit_student', student_id=student_id))
            if any_blank(request.form.get('name'), request.form.get('email'), request.form.get('branch')):
                cur.close()
                flash('Name, email, and branch are required.', 'danger')
                return redirect(url_for('edit_student', student_id=student_id))
            if not EMAIL_RE.match(request.form['email'].strip().lower()):
                cur.close()
                flash('Please enter a valid email address.', 'danger')
                return redirect(url_for('edit_student', student_id=student_id))
            try:
                cur.execute("SELECT 1 FROM students WHERE student_id=%s", (student_id,))
                if not cur.fetchone():
                    flash('Student not found — they may have already been deleted.', 'danger')
                    return redirect(url_for('students'))
                cur.execute("""
                    UPDATE students SET name=%s, email=%s, branch=%s, cgpa=%s, skills=%s
                    WHERE student_id=%s
                """, (request.form['name'], request.form['email'].strip().lower(), request.form['branch'],
                      cgpa, request.form['skills'], student_id))
                mysql.connection.commit()
                flash('Student updated successfully!', 'success')
                return redirect(url_for('students'))
            except pymysql.err.IntegrityError:
                mysql.connection.rollback()
                flash('That email is already registered to another student.', 'danger')
                return redirect(url_for('edit_student', student_id=student_id))
            finally:
                cur.close()
        cur.execute("SELECT * FROM students WHERE student_id=%s", (student_id,))
        student = cur.fetchone()
        cur.close()
        if not student:
            flash('Student not found.', 'danger')
            return redirect(url_for('students'))
        return render_template('edit_student.html', student=student, user_name=session['user_name'])

    @app.route('/delete_student/<int:student_id>', methods=['POST'])
    @admin_required
    def delete_student(student_id):
        cur = mysql.connection.cursor()
        try:
            cur.execute("DELETE FROM students WHERE student_id=%s", (student_id,))
            mysql.connection.commit()
            flash('Student deleted successfully!', 'success')
        except pymysql.err.IntegrityError:
            mysql.connection.rollback()
            flash('Cannot delete this student — they have placement records. Delete those placements first.', 'danger')
        finally:
            cur.close()
        return redirect(url_for('students'))

    @app.route('/upload_csv', methods=['GET', 'POST'])
    @admin_required
    def upload_csv():
        if request.method == 'POST':
            if 'csv_file' not in request.files:
                flash('No file selected!', 'danger')
                return redirect(url_for('upload_csv'))
            file = request.files['csv_file']
            if file.filename == '' or not file.filename.endswith('.csv'):
                flash('Only CSV files allowed!', 'danger')
                return redirect(url_for('upload_csv'))
            try:
                stream  = io.StringIO(file.stream.read().decode('utf-8'))
                rows    = list(csv.DictReader(stream))
                if not rows:
                    flash('CSV file is empty!', 'danger')
                    return redirect(url_for('upload_csv'))
                required = ['name', 'email', 'branch', 'cgpa', 'skills', 'password']
                missing  = [c for c in required if c not in rows[0].keys()]
                if missing:
                    flash(f'Missing columns: {", ".join(missing)}', 'danger')
                    return redirect(url_for('upload_csv'))
                cur = mysql.connection.cursor()
                success = errors = 0
                # One commit for the whole batch instead of one per row -- MySQL/InnoDB
                # only rolls back the failed statement itself, not the rows already
                # inserted earlier in the same transaction, so batching this is safe
                # and turns a 500-row upload from 500 round-trips into 1.
                for row in rows:
                    try:
                        name = str(row['name'] or '').strip()
                        email = str(row['email'] or '').strip().lower()
                        branch = str(row['branch'] or '').strip()
                        skills = str(row['skills'] or '').strip()
                        raw_password = str(row['password'] or '')
                        cgpa = float(row['cgpa'])
                        if (any_blank(name, email, branch)
                                or not EMAIL_RE.match(email)
                                or not PASSWORD_RE.match(raw_password)
                                or not math.isfinite(cgpa)
                                or not 0.0 <= cgpa <= 10.0):
                            raise ValueError
                        cur.execute("""
                            INSERT INTO students(name,email,branch,cgpa,skills,password,role)
                            VALUES(%s,%s,%s,%s,%s,%s,'student')
                        """, (name, email, branch, cgpa, skills,
                              generate_password_hash(raw_password)))
                        success += 1
                    except Exception:
                        errors += 1
                mysql.connection.commit()
                cur.close()
                flash(f'✅ {success} students added! ❌ {errors} errors skipped.', 'success')
                return redirect(url_for('students'))
            except Exception as e:
                flash(f'Error reading CSV: {str(e)}', 'danger')
                return redirect(url_for('upload_csv'))
        return render_template('upload_csv.html', user_name=session['user_name'])
