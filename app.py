from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_mysqldb import MySQL
import pandas as pd
import json
from collections import Counter
from functools import wraps

app = Flask(__name__)
app.secret_key = 'placement_secret_key_2024'

app.config['MYSQL_HOST'] = 'cela.proxy.rlwy.net'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'lRpebRiRevyVIuZgAOMYLsbiJoevRPRa' 
app.config['MYSQL_PORT'] = 17708  
app.config['MYSQL_DB'] = 'railway'

mysql = MySQL(app)

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
        cur.execute("SELECT * FROM students WHERE email=%s AND password=%s", (email, password))
        user = cur.fetchone()
        cur.close()
        if user:
            session['logged_in'] = True
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            return redirect(url_for('dashboard'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

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
        ORDER BY p.created_at DESC LIMIT 5
    """)
    recent = cur.fetchall()
    cur.close()

    return render_template('dashboard.html',
        total_students=total_students,
        total_companies=total_companies,
        total_placements=total_placements,
        avg_package=round(avg_package, 2),
        max_package=round(max_package, 2),
        recent=recent,
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
        password = request.form['password']
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
        cur.close()
        flash('Placement recorded successfully!', 'success')
        return redirect(url_for('placements'))
    cur.execute("SELECT student_id, name FROM students")
    students = cur.fetchall()
    cur.execute("SELECT company_id, company_name FROM companies")
    companies = cur.fetchall()
    cur.close()
    return render_template('add_placement.html',
        students=students, companies=companies, user_name=session['user_name'])

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

    cur.execute("""
        SELECT year, COUNT(*) as count FROM placements
        GROUP BY year ORDER BY year
    """)
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

    # Skill demand analysis
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
    app.run(debug=True)