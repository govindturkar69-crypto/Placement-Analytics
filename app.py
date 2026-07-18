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
import gzip
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year cache for static
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

# ── PERFORMANCE: Gzip compression ──────────────────────────────────────────
@app.after_request
def compress_response(response):
    if response.status_code < 200 or response.status_code >= 300:
        return response
    if 'Content-Encoding' in response.headers:
        return response
    if len(response.get_data()) < 500:
        return response
    accept_encoding = request.headers.get('Accept-Encoding', '')
    if 'gzip' not in accept_encoding:
        return response
    try:
        gzip_buffer = io.BytesIO()
        with gzip.GzipFile(mode='wb', fileobj=gzip_buffer) as f:
            f.write(response.get_data())
        response.set_data(gzip_buffer.getvalue())
        response.headers['Content-Encoding'] = 'gzip'
        response.headers['Content-Length'] = len(response.get_data())
    except Exception:
        pass
    return response

# ── PERFORMANCE: Cache headers ──────────────────────────────────────────────
@app.after_request
def add_cache_headers(response):
    if request.endpoint == 'static':
        response.headers['Cache-Control'] = 'public, max-age=31536000'
    else:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    return response

# ── AUTH DECORATOR ──────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Access denied!', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

# ── AUTH ────────────────────────────────────────────────────────────────────

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
        # PERFORMANCE: only fetch needed columns
        cur.execute("SELECT student_id, name, role, password FROM students WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()
        if user and check_password_hash(user[3], password):
            session.permanent = True
            session['logged_in'] = True
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['role'] = user[2]
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
        cur.execute("SELECT student_id, name FROM students WHERE email=%s", (email,))
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


# ── DASHBOARD ───────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    cur = mysql.connection.cursor()

    # PERFORMANCE: 5 queries → 1 query
    cur.execute("""
        SELECT
            (SELECT COUNT(*) FROM students) as total_students,
            (SELECT COUNT(*) FROM companies) as total_companies,
            (SELECT COUNT(*) FROM placements) as total_placements,
            (SELECT AVG(c.package) FROM placements p JOIN companies c ON p.company_id=c.company_id) as avg_package,
            (SELECT MAX(c.package) FROM placements p JOIN companies c ON p.company_id=c.company_id) as max_package
    """)
    stats = cur.fetchone()
    total_students   = stats[0] or 0
    total_companies  = stats[1] or 0
    total_placements = stats[2] or 0
    avg_package      = stats[3] or 0
    max_package      = stats[4] or 0

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
        for p in cur.fetchall():
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


# ── STUDENTS ────────────────────────────────────────────────────────────────

@app.route('/students')
@login_required
def students():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    cur = mysql.connection.cursor()
    # PERFORMANCE: pagination — don't load all students at once
    cur.execute("SELECT COUNT(*) FROM students")
    total = cur.fetchone()[0]
    cur.execute("""
        SELECT student_id, name, email, branch, cgpa, skills
        FROM students
        ORDER BY student_id DESC
        LIMIT %s OFFSET %s
    """, (per_page, offset))
    all_students = cur.fetchall()
    cur.close()
    total_pages = (total + per_page - 1) // per_page
    return render_template('students.html',
        students=all_students,
        user_name=session['user_name'],
        page=page,
        total_pages=total_pages,
        total=total)


@app.route('/add_student', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':
        name     = request.form['name']
        email    = request.form['email']
        branch   = request.form['branch']
        cgpa     = request.form['cgpa']
        skills   = request.form['skills']
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
@admin_required
def edit_student(student_id):
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        cur.execute("""
            UPDATE students SET name=%s, email=%s, branch=%s, cgpa=%s, skills=%s
            WHERE student_id=%s
        """, (request.form['name'], request.form['email'], request.form['branch'],
              request.form['cgpa'], request.form['skills'], student_id))
        mysql.connection.commit()
        cur.close()
        flash('Student updated successfully!', 'success')
        return redirect(url_for('students'))
    cur.execute("SELECT * FROM students WHERE student_id=%s", (student_id,))
    student = cur.fetchone()
    cur.close()
    return render_template('edit_student.html', student=student, user_name=session['user_name'])


@app.route('/delete_student/<int:student_id>')
@admin_required
def delete_student(student_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM students WHERE student_id=%s", (student_id,))
    mysql.connection.commit()
    cur.close()
    flash('Student deleted successfully!', 'success')
    return redirect(url_for('students'))


@app.route('/upload_csv', methods=['GET', 'POST'])
@admin_required
def upload_csv():
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
            success = errors = 0
            for row in rows:
                try:
                    cur.execute("""
                        INSERT INTO students(name,email,branch,cgpa,skills,password,role)
                        VALUES(%s,%s,%s,%s,%s,%s,'student')
                    """, (str(row['name']), str(row['email']), str(row['branch']),
                          float(row['cgpa']), str(row['skills']),
                          generate_password_hash(str(row['password']))))
                    mysql.connection.commit()
                    success += 1
                except Exception:
                    errors += 1
            cur.close()
            flash(f'✅ {success} students added! ❌ {errors} errors skipped.', 'success')
            return redirect(url_for('students'))
        except Exception as e:
            flash(f'Error reading CSV: {str(e)}', 'danger')
            return redirect(url_for('upload_csv'))
    return render_template('upload_csv.html', user_name=session['user_name'])


# ── COMPANIES ───────────────────────────────────────────────────────────────

@app.route('/companies')
@login_required
def companies():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM companies ORDER BY visit_date DESC")
    all_companies = cur.fetchall()
    cur.close()
    return render_template('companies.html', companies=all_companies, user_name=session['user_name'])


@app.route('/add_company', methods=['GET', 'POST'])
@admin_required
def add_company():
    if request.method == 'POST':
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO companies(company_name,package,required_skills,visit_date) VALUES(%s,%s,%s,%s)",
            (request.form['company_name'], request.form['package'],
             request.form['required_skills'], request.form['visit_date'])
        )
        mysql.connection.commit()
        cur.close()
        flash('Company added successfully!', 'success')
        return redirect(url_for('companies'))
    return render_template('add_company.html', user_name=session['user_name'])


@app.route('/edit_company/<int:company_id>', methods=['GET', 'POST'])
@admin_required
def edit_company(company_id):
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        cur.execute("""
            UPDATE companies SET company_name=%s, package=%s, required_skills=%s, visit_date=%s
            WHERE company_id=%s
        """, (request.form['company_name'], request.form['package'],
              request.form['required_skills'], request.form['visit_date'], company_id))
        mysql.connection.commit()
        cur.close()
        flash('Company updated successfully!', 'success')
        return redirect(url_for('companies'))
    cur.execute("SELECT * FROM companies WHERE company_id=%s", (company_id,))
    company = cur.fetchone()
    cur.close()
    return render_template('edit_company.html', company=company, user_name=session['user_name'])


@app.route('/delete_company/<int:company_id>')
@admin_required
def delete_company(company_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM companies WHERE company_id=%s", (company_id,))
    mysql.connection.commit()
    cur.close()
    flash('Company deleted successfully!', 'success')
    return redirect(url_for('companies'))


# ── PLACEMENTS ──────────────────────────────────────────────────────────────

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
@admin_required
def add_placement():
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        student_id = request.form['student_id']
        company_id = request.form['company_id']
        year       = request.form['year']
        status     = request.form['status']
        cur.execute(
            "INSERT INTO placements(student_id,company_id,year,status) VALUES(%s,%s,%s,%s)",
            (student_id, company_id, year, status)
        )
        mysql.connection.commit()
        cur.execute("SELECT name, email FROM students WHERE student_id=%s", (student_id,))
        student = cur.fetchone()
        cur.execute("SELECT company_name, package FROM companies WHERE company_id=%s", (company_id,))
        company = cur.fetchone()
        cur.close()
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

Best Regards,
Placement Analytics Team'''
                mail.send(msg)
            except Exception:
                pass
        flash('Placement recorded successfully!', 'success')
        return redirect(url_for('placements'))
    # PERFORMANCE: only fetch needed columns
    cur.execute("SELECT student_id, name FROM students ORDER BY name")
    students = cur.fetchall()
    cur.execute("SELECT company_id, company_name FROM companies ORDER BY company_name")
    companies = cur.fetchall()
    cur.close()
    return render_template('add_placement.html',
        students=students, companies=companies, user_name=session['user_name'])


@app.route('/delete_placement/<int:placement_id>')
@admin_required
def delete_placement(placement_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM placements WHERE placement_id=%s", (placement_id,))
    mysql.connection.commit()
    cur.close()
    flash('Placement deleted successfully!', 'success')
    return redirect(url_for('placements'))


# ── ANALYTICS ───────────────────────────────────────────────────────────────

@app.route('/analytics')
@login_required
def analytics():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.company_name, COUNT(*) as count
        FROM placements p JOIN companies c ON p.company_id=c.company_id
        GROUP BY c.company_name ORDER BY count DESC LIMIT 10
    """)
    company_data   = cur.fetchall()
    company_labels = [r[0] for r in company_data]
    company_counts = [r[1] for r in company_data]

    cur.execute("SELECT year, COUNT(*) as count FROM placements GROUP BY year ORDER BY year")
    year_data   = cur.fetchall()
    year_labels = [str(r[0]) for r in year_data]
    year_counts = [r[1] for r in year_data]

    cur.execute("""
        SELECT s.branch, COUNT(*) as count
        FROM placements p JOIN students s ON p.student_id=s.student_id
        GROUP BY s.branch ORDER BY count DESC
    """)
    branch_data   = cur.fetchall()
    branch_labels = [r[0] for r in branch_data]
    branch_counts = [r[1] for r in branch_data]

    cur.execute("""
        SELECT c.company_name, c.package
        FROM placements p JOIN companies c ON p.company_id=c.company_id
        ORDER BY c.package DESC LIMIT 10
    """)
    pkg_data   = cur.fetchall()
    pkg_labels = [r[0] for r in pkg_data]
    pkg_values = [r[1] for r in pkg_data]

    cur.execute("SELECT required_skills FROM companies")
    all_skills = []
    for row in cur.fetchall():
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


# ── ML PREDICTOR ────────────────────────────────────────────────────────────

@app.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    result = None
    if request.method == 'POST':
        try:
            cgpa       = float(request.form['cgpa'])
            skills     = request.form['skills']
            branch     = request.form.get('branch', 'CSE')
            backlogs   = int(request.form.get('backlogs', 0))
            internship = request.form.get('internship', 'no')
            projects   = int(request.form.get('projects', 0))

            skill_list    = [s.strip().lower() for s in skills.split(',') if s.strip()]
            skill_count   = len(skill_list)
            high_demand   = ['python','java','react','node','sql','mysql','javascript',
                             'dsa','c++','machine learning','ml','django','flask',
                             'spring','aws','docker','git']
            matched_skills = sum(1 for s in skill_list if any(h in s for h in high_demand))

            if cgpa >= 9.5:   cgpa_score = 100
            elif cgpa >= 9.0: cgpa_score = 95
            elif cgpa >= 8.5: cgpa_score = 88
            elif cgpa >= 8.0: cgpa_score = 80
            elif cgpa >= 7.5: cgpa_score = 70
            elif cgpa >= 7.0: cgpa_score = 58
            elif cgpa >= 6.5: cgpa_score = 45
            elif cgpa >= 6.0: cgpa_score = 32
            else:             cgpa_score = 15

            skill_score  = min(100, (skill_count * 12) + (matched_skills * 8))
            branch_score = {'CSE':95,'IT':88,'ECE':75,'EEE':65,'Mechanical':55,'Civil':45}.get(branch, 60)

            if backlogs == 0:       backlog_score = 100
            elif backlogs == 1:     backlog_score = 70
            elif backlogs == 2:     backlog_score = 45
            elif backlogs <= 4:     backlog_score = 20
            else:                   backlog_score = 5

            internship_score = 100 if internship == 'yes' else 30
            project_score    = min(100, projects * 25)

            chance = round(
                cgpa_score       * 0.30 +
                skill_score      * 0.25 +
                branch_score     * 0.15 +
                backlog_score    * 0.15 +
                internship_score * 0.10 +
                project_score    * 0.05
            )

            if chance >= 85:
                company_matches = [
                    {'name':'Google / Amazon','icon':'🚀','color':'#10b981'},
                    {'name':'Microsoft / Adobe','icon':'⭐','color':'#2563eb'},
                    {'name':'TCS / Infosys','icon':'✅','color':'#10b981'},
                ]
            elif chance >= 70:
                company_matches = [
                    {'name':'Wipro / HCL','icon':'✅','color':'#10b981'},
                    {'name':'Capgemini / Accenture','icon':'⚡','color':'#f59e0b'},
                    {'name':'TCS / Infosys','icon':'✅','color':'#10b981'},
                ]
            elif chance >= 50:
                company_matches = [
                    {'name':'TCS / Infosys','icon':'✅','color':'#10b981'},
                    {'name':'Wipro / Tech Mahindra','icon':'⚡','color':'#f59e0b'},
                ]
            else:
                company_matches = [
                    {'name':'Focus on improving skills first','icon':'📚','color':'#ef4444'},
                ]

            tips = []
            if cgpa_score < 70:       tips.append('📈 Improve your CGPA — target 7.5+')
            if skill_count < 4:       tips.append('💻 Learn more in-demand skills (Python, DSA, SQL)')
            if matched_skills < 3:    tips.append('🎯 Focus on: Python, Java, React, DSA')
            if backlogs > 0:          tips.append('📋 Clear all backlogs — they reduce chances significantly')
            if internship == 'no':    tips.append('🏢 Try to get an internship — boosts chances by 10%')
            if projects < 2:          tips.append('🚀 Build at least 2-3 real projects')
            if not tips:              tips.append('🌟 You are well prepared — keep practicing DSA!')

            if chance >= 80:   level, color, emoji = 'High',      'green',  '🔥'
            elif chance >= 60: level, color, emoji = 'Medium',    'orange', '⚡'
            elif chance >= 40: level, color, emoji = 'Low',       'red',    '📚'
            else:              level, color, emoji = 'Very Low',  'red',    '😟'

            result = {
                'chance': chance, 'level': level, 'color': color, 'emoji': emoji,
                'cgpa': cgpa, 'skills': skill_count, 'matched_skills': matched_skills,
                'branch': branch, 'backlogs': backlogs, 'internship': internship,
                'projects': projects,
                'scores': {
                    'cgpa': round(cgpa_score), 'skills': round(skill_score),
                    'branch': round(branch_score), 'backlog': round(backlog_score),
                    'internship': round(internship_score), 'projects': round(project_score),
                },
                'company_matches': company_matches,
                'tips': tips
            }
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
    return render_template('predict.html', result=result, user_name=session['user_name'])


# ── PDF REPORT ──────────────────────────────────────────────────────────────

@app.route('/download_report')
@admin_required
def download_report():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT s.name, c.company_name, c.package, p.year, p.status, s.branch
        FROM placements p
        JOIN students s ON p.student_id=s.student_id
        JOIN companies c ON p.company_id=c.company_id
        ORDER BY p.year DESC
    """)
    placements = cur.fetchall()
    # PERFORMANCE: single query for stats
    cur.execute("""
        SELECT
            (SELECT COUNT(*) FROM students) as ts,
            (SELECT COUNT(*) FROM placements) as tp,
            (SELECT AVG(c.package) FROM placements p JOIN companies c ON p.company_id=c.company_id) as avg_p,
            (SELECT MAX(c.package) FROM placements p JOIN companies c ON p.company_id=c.company_id) as max_p
    """)
    s = cur.fetchone()
    cur.close()
    total_students, total_placed = s[0] or 0, s[1] or 0
    avg_pkg, max_pkg = s[2] or 0, s[3] or 0

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
        ['Average Package', f'{round(avg_pkg,2)} LPA'],
        ['Highest Package', f'{round(max_pkg,2)} LPA'],
        ['Placement Rate', f'{round((total_placed/total_students)*100,1) if total_students else 0}%'],
    ]
    t = Table(summary_data, colWidths=[250, 250])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#2563eb')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTSIZE',(0,0),(-1,0),12),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('GRID',(0,0),(-1,-1),1,colors.grey),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f0f4ff')]),
        ('FONTNAME',(0,1),(-1,-1),'Helvetica'),
        ('FONTSIZE',(0,1),(-1,-1),11),
        ('PADDING',(0,0),(-1,-1),8),
    ]))
    elements.extend([t, Spacer(1,30), Paragraph('Placement Records', styles['Heading2']), Spacer(1,10)])
    if placements:
        pd = [['Student','Company','Package (LPA)','Year','Branch','Status']]
        for p in placements:
            pd.append([str(p[0]),str(p[1]),str(p[2]),str(p[3]),str(p[5]),str(p[4])])
        pt = Table(pd, colWidths=[110,100,80,50,70,80])
        pt.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1e293b')),
            ('TEXTCOLOR',(0,0),(-1,0),colors.white),
            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
            ('FONTSIZE',(0,0),(-1,0),10),
            ('ALIGN',(0,0),(-1,-1),'CENTER'),
            ('GRID',(0,0),(-1,-1),0.5,colors.grey),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f8fafc')]),
            ('FONTNAME',(0,1),(-1,-1),'Helvetica'),
            ('FONTSIZE',(0,1),(-1,-1),9),
            ('PADDING',(0,0),(-1,-1),6),
        ]))
        elements.append(pt)
    else:
        elements.append(Paragraph('No placement records found.', styles['Normal']))
    doc.build(elements)
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=placement_report.pdf'
    return response


# ── EXCEL EXPORT ────────────────────────────────────────────────────────────

@app.route('/export_excel')
@admin_required
def export_excel():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT s.name, s.email, s.branch, s.cgpa, s.skills,
               c.company_name, c.package, p.year, p.status
        FROM placements p
        JOIN students s ON p.student_id=s.student_id
        JOIN companies c ON p.company_id=c.company_id
        ORDER BY p.year DESC
    """)
    placements = cur.fetchall()
    cur.execute("SELECT name, email, branch, cgpa, skills FROM students ORDER BY name")
    all_students = cur.fetchall()
    cur.execute("SELECT company_name, package, required_skills, visit_date FROM companies ORDER BY company_name")
    all_companies = cur.fetchall()
    cur.close()

    wb = openpyxl.Workbook()
    center = Alignment(horizontal='center', vertical='center')

    def make_header(ws, headers, fill_color):
        fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type='solid')
        font = Font(color='FFFFFF', bold=True, size=11)
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.fill = fill; cell.font = font; cell.alignment = center

    ws1 = wb.active; ws1.title = 'Placements'
    h1 = ['Student','Email','Branch','CGPA','Skills','Company','Package (LPA)','Year','Status']
    make_header(ws1, h1, '2563EB')
    for ri, row in enumerate(placements, 2):
        for ci, val in enumerate(row, 1):
            cell = ws1.cell(row=ri, column=ci, value=val)
            cell.alignment = center
            if ri % 2 == 0:
                cell.fill = PatternFill(start_color='EFF6FF', end_color='EFF6FF', fill_type='solid')
    for col in range(1, len(h1)+1): ws1.column_dimensions[get_column_letter(col)].width = 18

    ws2 = wb.create_sheet('Students')
    h2 = ['Name','Email','Branch','CGPA','Skills']
    make_header(ws2, h2, '1E293B')
    for ri, row in enumerate(all_students, 2):
        for ci, val in enumerate(row, 1):
            ws2.cell(row=ri, column=ci, value=val).alignment = center
    for col in range(1, len(h2)+1): ws2.column_dimensions[get_column_letter(col)].width = 20

    ws3 = wb.create_sheet('Companies')
    h3 = ['Company Name','Package (LPA)','Required Skills','Visit Date']
    make_header(ws3, h3, '10B981')
    for ri, row in enumerate(all_companies, 2):
        for ci, val in enumerate(row, 1):
            ws3.cell(row=ri, column=ci, value=str(val) if val else '').alignment = center
    for col in range(1, len(h3)+1): ws3.column_dimensions[get_column_letter(col)].width = 22

    output = BytesIO()
    wb.save(output); output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename=placement_data.xlsx'
    return response


# ── PROFILE ─────────────────────────────────────────────────────────────────

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


# ── API ─────────────────────────────────────────────────────────────────────

@app.route('/api/stats')
@login_required
def api_stats():
    cur = mysql.connection.cursor()
    # PERFORMANCE: single query
    cur.execute("""
        SELECT
            (SELECT COUNT(*) FROM students) as students,
            (SELECT COUNT(*) FROM placements) as placed,
            (SELECT AVG(c.package) FROM placements p JOIN companies c ON p.company_id=c.company_id) as avg_pkg
    """)
    s = cur.fetchone()
    cur.close()
    students, placed, avg_pkg = s[0] or 0, s[1] or 0, s[2] or 0
    return jsonify({
        'total_students': students,
        'total_placed': placed,
        'placement_rate': round((placed/students)*100,1) if students else 0,
        'avg_package': round(avg_pkg, 2)
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)