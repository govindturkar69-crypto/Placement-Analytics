from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, make_response
import os
import pymysql
pymysql.install_as_MySQLdb()
from flask_mysqldb import MySQL
import json
from collections import Counter
from functools import wraps
from flask_mail import Mail, Message
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from io import BytesIO
import csv
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['PERMANENT_SESSION_LIFETIME'] = 1800
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())

app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD')
app.config['MYSQL_PORT'] = int(os.environ.get('MYSQL_PORT', 3306))
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB')

mysql = MySQL(app)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
mail = Mail(app)

reset_tokens = {}


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM students WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()
        if user and check_password_hash(user[6], password):
            session.permanent = True
            session['logged_in'] = True
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['role'] = user[7]
            return redirect(url_for('dashboard'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM students WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()
        if user:
            token = secrets.token_urlsafe(32)
            reset_tokens[token] = email
            reset_link = url_for('reset_password', token=token, _external=True)
            try:
                msg = Message(
                    'Password Reset - Placement Analytics',
                    sender=os.environ.get('MAIL_USERNAME'),
                    recipients=[email]
                )
                msg.body = f'''Hello {user[1]},

Click the link below to reset your password:
{reset_link}

This link will work only once.

If you did not request this, ignore this email.

Regards,
Placement Analytics Team'''
                mail.send(msg)
                flash('Password reset link sent to your email!', 'success')
            except Exception:
                flash('Error sending email. Please try again.', 'danger')
        else:
            flash('Email not found!', 'danger')
    return render_template('forgot_password.html')


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if token not in reset_tokens:
        flash('Invalid or expired link!', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        new_password = request.form['password']
        email = reset_tokens[token]
        hashed = generate_password_hash(new_password)
        cur = mysql.connection.cursor()
        cur.execute("UPDATE students SET password=%s WHERE email=%s", (hashed, email))
        mysql.connection.commit()
        cur.close()
        del reset_tokens[token]
        flash('Password reset successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html', token=token)

@app.route('/dashboard')
@login_required
def dashboard():
    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) FROM students")
    total_students = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM companies")
    total_companies = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM placements")
    total_placements = cur.fetchone()[0]

    cur.execute("""
        SELECT AVG(c.package) FROM placements p
        JOIN companies c ON p.company_id = c.company_id
    """)
    avg_package = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT MAX(c.package) FROM placements p
        JOIN companies c ON p.company_id = c.company_id
    """)
    max_package = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT s.name, c.company_name, c.package, p.year, p.status
        FROM placements p
        JOIN students s ON p.student_id = s.student_id
        JOIN companies c ON p.company_id = c.company_id
        ORDER BY p.placement_id DESC LIMIT 5
    """)
    recent = cur.fetchall()

    notifications = []
    if session.get('role') == 'admin':
        cur.execute("""
            SELECT s.name, c.company_name, c.package, p.status
            FROM placements p
            JOIN students s ON p.student_id = s.student_id
            JOIN companies c ON p.company_id = c.company_id
            ORDER BY p.placement_id DESC LIMIT 3
        """)
        recent_placements = cur.fetchall()
        for p in recent_placements:
            notifications.append({
                'icon': '🎉',
                'message': f'{p[0]} placed at {p[1]} — {p[2]} LPA',
                'type': 'success'
            })

        cur.execute("SELECT COUNT(*) FROM students WHERE role='student'")
        new_students = cur.fetchone()[0]
        if new_students:
            notifications.append({
                'icon': '👨‍🎓',
                'message': f'Total {new_students} student(s) registered',
                'type': 'info'
            })

    if session.get('role') == 'student':
        cur.execute("""
            SELECT c.company_name, c.package, p.status
            FROM placements p
            JOIN companies c ON p.company_id = c.company_id
            WHERE p.student_id = %s
            ORDER BY p.placement_id DESC LIMIT 1
        """, (session['user_id'],))
        my_placement = cur.fetchone()
        if my_placement:
            notifications.append({
                'icon': '🎉',
                'message': f'You are placed at {my_placement[0]} — {my_placement[1]} LPA!',
                'type': 'success'
            })
        else:
            notifications.append({
                'icon': '💡',
                'message': 'Check ML Predictor to know your placement chances!',
                'type': 'info'
            })

    cur.close()

    return render_template('dashboard.html',
        total_students=total_students,
        total_companies=total_companies,
        total_placements=total_placements,
        avg_package=round(avg_package, 2),
        max_package=round(max_package, 2),
        recent=recent,
        notifications=notifications,
        user_name=session['user_name']
    )

@app.route('/students')
@login_required
def students():
    cur = mysql.connection.cursor()
    cur.execute("SELECT student_id, name, email, branch, cgpa, skills FROM students")
    all_students = cur.fetchall()
    cur.close()
    return render_template('students.html', students=all_students, user_name=session['user_name'])


@app.route('/add_student', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        branch = request.form['branch']
        cgpa = request.form['cgpa']
        skills = request.form['skills']
        password = generate_password_hash(request.form['password'])
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO students(name,email,branch,cgpa,skills,password) VALUES(%s,%s,%s,%s,%s,%s)",
            (name, email, branch, cgpa, skills, password)
        )
        mysql.connection.commit()
        cur.close()
        flash('Student added successfully!', 'success')
        return redirect(url_for('students'))
    return render_template('add_student.html', user_name=session['user_name'])


@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    if session.get('role') != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        branch = request.form['branch']
        cgpa = request.form['cgpa']
        skills = request.form['skills']
        cur.execute("""
            UPDATE students
            SET name=%s, email=%s, branch=%s, cgpa=%s, skills=%s
            WHERE student_id=%s
        """, (name, email, branch, cgpa, skills, student_id))
        mysql.connection.commit()
        cur.close()
        flash('Student updated successfully!', 'success')
        return redirect(url_for('students'))
    cur.execute("SELECT * FROM students WHERE student_id=%s", (student_id,))
    student = cur.fetchone()
    cur.close()
    return render_template('edit_student.html', student=student, user_name=session['user_name'])


@app.route('/delete_student/<int:student_id>')
@login_required
def delete_student(student_id):
    if session.get('role') != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM students WHERE student_id=%s", (student_id,))
    mysql.connection.commit()
    cur.close()
    flash('Student deleted successfully!', 'success')
    return redirect(url_for('students'))


@app.route('/upload_csv', methods=['GET', 'POST'])
@login_required
def upload_csv():
    if session.get('role') != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file selected!', 'danger')
            return redirect(url_for('upload_csv'))
        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected!', 'danger')
            return redirect(url_for('upload_csv'))
        if not file.filename.endswith('.csv'):
            flash('Only CSV files allowed!', 'danger')
            return redirect(url_for('upload_csv'))
        try:
            stream = io.StringIO(file.stream.read().decode('utf-8'))
            reader = csv.DictReader(stream)
            required_columns = ['name', 'email', 'branch', 'cgpa', 'skills', 'password']
            rows = list(reader)
            if not rows:
                flash('CSV file is empty!', 'danger')
                return redirect(url_for('upload_csv'))
            missing = [col for col in required_columns if col not in rows[0].keys()]
            if missing:
                flash(f'Missing columns: {", ".join(missing)}', 'danger')
                return redirect(url_for('upload_csv'))
            cur = mysql.connection.cursor()
            success = 0
            errors = 0
            for row in rows:
                try:
                    hashed_password = generate_password_hash(str(row['password']))
                    cur.execute("""
                        INSERT INTO students
                        (name, email, branch, cgpa, skills, password, role)
                        VALUES (%s, %s, %s, %s, %s, %s, 'student')
                    """, (
                        str(row['name']),
                        str(row['email']),
                        str(row['branch']),
                        float(row['cgpa']),
                        str(row['skills']),
                        hashed_password
                    ))
                    mysql.connection.commit()
                    success += 1
                except Exception:
                    errors += 1
                    continue
            cur.close()
            flash(f'✅ {success} students added successfully! ❌ {errors} errors skipped.', 'success')
            return redirect(url_for('students'))
        except Exception as e:
            flash(f'Error reading CSV: {str(e)}', 'danger')
            return redirect(url_for('upload_csv'))
    return render_template('upload_csv.html', user_name=session['user_name'])

@app.route('/companies')
@login_required
def companies():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM companies ORDER BY visit_date DESC")
    all_companies = cur.fetchall()
    cur.close()
    return render_template('companies.html', companies=all_companies, user_name=session['user_name'])


@app.route('/add_company', methods=['GET', 'POST'])
@login_required
def add_company():
    if request.method == 'POST':
        name = request.form['company_name']
        package = request.form['package']
        skills = request.form['required_skills']
        visit_date = request.form['visit_date']
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO companies(company_name,package,required_skills,visit_date) VALUES(%s,%s,%s,%s)",
            (name, package, skills, visit_date)
        )
        mysql.connection.commit()
        cur.close()
        flash('Company added successfully!', 'success')
        return redirect(url_for('companies'))
    return render_template('add_company.html', user_name=session['user_name'])


@app.route('/edit_company/<int:company_id>', methods=['GET', 'POST'])
@login_required
def edit_company(company_id):
    if session.get('role') != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        name = request.form['company_name']
        package = request.form['package']
        skills = request.form['required_skills']
        visit_date = request.form['visit_date']
        cur.execute("""
            UPDATE companies
            SET company_name=%s, package=%s, required_skills=%s, visit_date=%s
            WHERE company_id=%s
        """, (name, package, skills, visit_date, company_id))
        mysql.connection.commit()
        cur.close()
        flash('Company updated successfully!', 'success')
        return redirect(url_for('companies'))
    cur.execute("SELECT * FROM companies WHERE company_id=%s", (company_id,))
    company = cur.fetchone()
    cur.close()
    return render_template('edit_company.html', company=company, user_name=session['user_name'])


@app.route('/delete_company/<int:company_id>')
@login_required
def delete_company(company_id):
    if session.get('role') != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM companies WHERE company_id=%s", (company_id,))
    mysql.connection.commit()
    cur.close()
    flash('Company deleted successfully!', 'success')
    return redirect(url_for('companies'))

@app.route('/placements')
@login_required
def placements():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.placement_id, s.name, c.company_name, c.package, p.year, p.status
        FROM placements p
        JOIN students s ON p.student_id = s.student_id
        JOIN companies c ON p.company_id = c.company_id
        ORDER BY p.year DESC
    """)
    all_placements = cur.fetchall()
    cur.close()
    return render_template('placements.html', placements=all_placements, user_name=session['user_name'])


@app.route('/add_placement', methods=['GET', 'POST'])
@login_required
def add_placement():
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        student_id = request.form['student_id']
        company_id = request.form['company_id']
        year = request.form['year']
        status = request.form['status']
        cur.execute(
            "INSERT INTO placements(student_id,company_id,year,status) VALUES(%s,%s,%s,%s)",
            (student_id, company_id, year, status)
        )
        mysql.connection.commit()
        # Fetch student and company for email — cursor still open
        cur.execute("SELECT name, email FROM students WHERE student_id=%s", (student_id,))
        student = cur.fetchone()
        cur.execute("SELECT company_name, package FROM companies WHERE company_id=%s", (company_id,))
        company = cur.fetchone()
        cur.close()
        # Send congratulations email
        if student and company and os.environ.get('MAIL_USERNAME'):
            try:
                msg = Message(
                    '🎉 Congratulations! Placement Confirmed',
                    sender=os.environ.get('MAIL_USERNAME'),
                    recipients=[student[1]]
                )
                msg.body = f'''Dear {student[0]},

🎉 Congratulations! You have been placed at {company[0]}!

📋 Placement Details:
   Company  : {company[0]}
   Package  : {company[1]} LPA
   Year     : {year}
   Status   : {status}

Keep up the great work!

Best Regards,
Placement Analytics Team'''
                mail.send(msg)
            except Exception:
                pass
        flash('Placement recorded successfully!', 'success')
        return redirect(url_for('placements'))
    cur.execute("SELECT student_id, name FROM students")
    students = cur.fetchall()
    cur.execute("SELECT company_id, company_name FROM companies")
    companies = cur.fetchall()
    cur.close()
    return render_template('add_placement.html',
        students=students, companies=companies, user_name=session['user_name'])


@app.route('/delete_placement/<int:placement_id>')
@login_required
def delete_placement(placement_id):
    if session.get('role') != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM placements WHERE placement_id=%s", (placement_id,))
    mysql.connection.commit()
    cur.close()
    flash('Placement deleted successfully!', 'success')
    return redirect(url_for('placements'))

@app.route('/analytics')
@login_required
def analytics():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.company_name, COUNT(*) as count
        FROM placements p
        JOIN companies c ON p.company_id = c.company_id
        GROUP BY c.company_name ORDER BY count DESC
    """)
    company_data = cur.fetchall()
    company_labels = [r[0] for r in company_data]
    company_counts = [r[1] for r in company_data]
    cur.execute("SELECT year, COUNT(*) as count FROM placements GROUP BY year ORDER BY year")
    year_data = cur.fetchall()
    year_labels = [str(r[0]) for r in year_data]
    year_counts = [r[1] for r in year_data]
    cur.execute("""
        SELECT s.branch, COUNT(*) as count
        FROM placements p
        JOIN students s ON p.student_id = s.student_id
        GROUP BY s.branch
    """)
    branch_data = cur.fetchall()
    branch_labels = [r[0] for r in branch_data]
    branch_counts = [r[1] for r in branch_data]
    cur.execute("""
        SELECT c.company_name, c.package
        FROM placements p
        JOIN companies c ON p.company_id = c.company_id
        ORDER BY c.package DESC
    """)
    pkg_data = cur.fetchall()
    pkg_labels = [r[0] for r in pkg_data]
    pkg_values = [r[1] for r in pkg_data]
    cur.execute("SELECT required_skills FROM companies")
    all_skills_raw = cur.fetchall()
    all_skills = []
    for row in all_skills_raw:
        if row[0]:
            all_skills.extend([s.strip() for s in row[0].split(',')])
    skill_counts = Counter(all_skills).most_common(8)
    skill_labels = [s[0] for s in skill_counts]
    skill_values = [s[1] for s in skill_counts]
    cur.close()
    return render_template('analytics.html',
        company_labels=json.dumps(company_labels),
        company_counts=json.dumps(company_counts),
        year_labels=json.dumps(year_labels),
        year_counts=json.dumps(year_counts),
        branch_labels=json.dumps(branch_labels),
        branch_counts=json.dumps(branch_counts),
        pkg_labels=json.dumps(pkg_labels),
        pkg_values=json.dumps(pkg_values),
        skill_labels=json.dumps(skill_labels),
        skill_values=json.dumps(skill_values),
        user_name=session['user_name']
    )

@app.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    result = None
    if request.method == 'POST':
        cgpa = float(request.form['cgpa'])
        skills = request.form['skills']
        skill_count = len([s.strip() for s in skills.split(',')])
        if cgpa >= 9.0 and skill_count >= 5:
            chance = 95
        elif cgpa >= 8.5 and skill_count >= 4:
            chance = 85
        elif cgpa >= 8.0 and skill_count >= 3:
            chance = 75
        elif cgpa >= 7.5 and skill_count >= 2:
            chance = 65
        elif cgpa >= 7.0 and skill_count >= 1:
            chance = 50
        else:
            chance = 30
        if chance >= 80:
            level, color, emoji = 'High', 'green', '🔥'
        elif chance >= 60:
            level, color, emoji = 'Medium', 'orange', '⚡'
        else:
            level, color, emoji = 'Low', 'red', '📚'
        result = {'chance': chance, 'level': level, 'color': color,
                  'emoji': emoji, 'cgpa': cgpa, 'skills': skill_count}
    return render_template('predict.html', result=result, user_name=session['user_name'])

@app.route('/download_report')
@login_required
def download_report():
    if session.get('role') != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT s.name, c.company_name, c.package, p.year, p.status, s.branch
        FROM placements p
        JOIN students s ON p.student_id = s.student_id
        JOIN companies c ON p.company_id = c.company_id
        ORDER BY p.year DESC
    """)
    placements = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM students")
    total_students = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM placements")
    total_placed = cur.fetchone()[0]
    cur.execute("SELECT AVG(c.package) FROM placements p JOIN companies c ON p.company_id=c.company_id")
    avg_pkg = cur.fetchone()[0] or 0
    cur.execute("SELECT MAX(c.package) FROM placements p JOIN companies c ON p.company_id=c.company_id")
    max_pkg = cur.fetchone()[0] or 0
    cur.close()
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    elements.append(Paragraph('Smart Placement Analytics Report', styles['Title']))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph('Summary Statistics', styles['Heading2']))
    elements.append(Spacer(1, 10))
    summary_data = [
        ['Metric', 'Value'],
        ['Total Students', str(total_students)],
        ['Students Placed', str(total_placed)],
        ['Average Package', f'{round(avg_pkg, 2)} LPA'],
        ['Highest Package', f'{round(max_pkg, 2)} LPA'],
        ['Placement Rate', f'{round((total_placed/total_students)*100, 1) if total_students else 0}%'],
    ]
    summary_table = Table(summary_data, colWidths=[250, 250])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f4ff')]),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    elements.append(Paragraph('Placement Records', styles['Heading2']))
    elements.append(Spacer(1, 10))
    if placements:
        placement_data = [['Student Name', 'Company', 'Package (LPA)', 'Year', 'Branch', 'Status']]
        for p in placements:
            placement_data.append([str(p[0]), str(p[1]), str(p[2]), str(p[3]), str(p[5]), str(p[4])])
        placement_table = Table(placement_data, colWidths=[110, 100, 80, 50, 70, 80])
        placement_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(placement_table)
    else:
        elements.append(Paragraph('No placement records found.', styles['Normal']))
    doc.build(elements)
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=placement_report.pdf'
    return response

@app.route('/export_excel')
@login_required
def export_excel():
    if session.get('role') != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT s.name, s.email, s.branch, s.cgpa, s.skills,
               c.company_name, c.package, p.year, p.status
        FROM placements p
        JOIN students s ON p.student_id = s.student_id
        JOIN companies c ON p.company_id = c.company_id
        ORDER BY p.year DESC
    """)
    placements = cur.fetchall()
    cur.execute("SELECT name, email, branch, cgpa, skills FROM students")
    all_students = cur.fetchall()
    cur.execute("SELECT company_name, package, required_skills, visit_date FROM companies")
    all_companies = cur.fetchall()
    cur.close()
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "Placements"
    header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=11)
    center = Alignment(horizontal='center', vertical='center')
    headers1 = ['Student Name', 'Email', 'Branch', 'CGPA', 'Skills',
                'Company', 'Package (LPA)', 'Year', 'Status']
    for col, header in enumerate(headers1, 1):
        cell = ws1.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
    for row_idx, row in enumerate(placements, 2):
        for col_idx, value in enumerate(row, 1):
            cell = ws1.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = center
            if row_idx % 2 == 0:
                cell.fill = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")
    for col in range(1, len(headers1) + 1):
        ws1.column_dimensions[get_column_letter(col)].width = 18
    ws2 = wb.create_sheet("Students")
    headers2 = ['Name', 'Email', 'Branch', 'CGPA', 'Skills']
    for col, header in enumerate(headers2, 1):
        cell = ws2.cell(row=1, column=col, value=header)
        cell.fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = center
    for row_idx, row in enumerate(all_students, 2):
        for col_idx, value in enumerate(row, 1):
            cell = ws2.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = center
    for col in range(1, len(headers2) + 1):
        ws2.column_dimensions[get_column_letter(col)].width = 20
    ws3 = wb.create_sheet("Companies")
    headers3 = ['Company Name', 'Package (LPA)', 'Required Skills', 'Visit Date']
    for col, header in enumerate(headers3, 1):
        cell = ws3.cell(row=1, column=col, value=header)
        cell.fill = PatternFill(start_color="10B981", end_color="10B981", fill_type="solid")
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = center
    for row_idx, row in enumerate(all_companies, 2):
        for col_idx, value in enumerate(row, 1):
            cell = ws3.cell(row=row_idx, column=col_idx, value=str(value) if value else '')
            cell.alignment = center
    for col in range(1, len(headers3) + 1):
        ws3.column_dimensions[get_column_letter(col)].width = 22
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename=placement_data.xlsx'
    return response

@app.route('/profile')
@login_required
def profile():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM students WHERE student_id=%s", (session['user_id'],))
    student = cur.fetchone()
    cur.execute("""
        SELECT c.company_name, c.package, p.year, p.status
        FROM placements p
        JOIN companies c ON p.company_id = c.company_id
        WHERE p.student_id = %s
        ORDER BY p.year DESC
    """, (session['user_id'],))
    my_placements = cur.fetchall()
    cur.close()
    return render_template('profile.html',
        student=student,
        my_placements=my_placements,
        user_name=session['user_name'])

@app.route('/api/stats')
@login_required
def api_stats():
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM students")
    students = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM placements")
    placed = cur.fetchone()[0]
    cur.execute("SELECT AVG(c.package) FROM placements p JOIN companies c ON p.company_id=c.company_id")
    avg_pkg = cur.fetchone()[0] or 0
    cur.close()
    return jsonify({
        'total_students': students,
        'total_placed': placed,
        'placement_rate': round((placed / students) * 100, 1) if students else 0,
        'avg_package': round(avg_pkg, 2)
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)