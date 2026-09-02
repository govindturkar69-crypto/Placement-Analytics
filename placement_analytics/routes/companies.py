import pymysql
from flask import render_template, request, redirect, url_for, session, flash

from ..extensions import mysql
from ..decorators import login_required, admin_required
from ..utils import any_blank


def register(app):
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
            try:
                package = float(request.form['package'])
            except ValueError:
                flash('Package must be a number.', 'danger')
                return render_template('add_company.html', user_name=session['user_name'])
            if any_blank(request.form.get('company_name')):
                flash('Company name is required.', 'danger')
                return render_template('add_company.html', user_name=session['user_name'])
            cur = mysql.connection.cursor()
            cur.execute(
                "INSERT INTO companies(company_name,package,required_skills,visit_date) VALUES(%s,%s,%s,%s)",
                (request.form['company_name'], package,
                 request.form['required_skills'], request.form.get('visit_date') or None)
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
            try:
                package = float(request.form['package'])
            except ValueError:
                cur.close()
                flash('Package must be a number.', 'danger')
                return redirect(url_for('edit_company', company_id=company_id))
            if any_blank(request.form.get('company_name')):
                cur.close()
                flash('Company name is required.', 'danger')
                return redirect(url_for('edit_company', company_id=company_id))
            cur.execute("SELECT 1 FROM companies WHERE company_id=%s", (company_id,))
            if not cur.fetchone():
                cur.close()
                flash('Company not found — it may have already been deleted.', 'danger')
                return redirect(url_for('companies'))
            cur.execute("""
                UPDATE companies SET company_name=%s, package=%s, required_skills=%s, visit_date=%s
                WHERE company_id=%s
            """, (request.form['company_name'], package,
                  request.form['required_skills'], request.form.get('visit_date') or None, company_id))
            mysql.connection.commit()
            cur.close()
            flash('Company updated successfully!', 'success')
            return redirect(url_for('companies'))
        cur.execute("SELECT * FROM companies WHERE company_id=%s", (company_id,))
        company = cur.fetchone()
        cur.close()
        if not company:
            flash('Company not found.', 'danger')
            return redirect(url_for('companies'))
        return render_template('edit_company.html', company=company, user_name=session['user_name'])

    @app.route('/delete_company/<int:company_id>', methods=['POST'])
    @admin_required
    def delete_company(company_id):
        cur = mysql.connection.cursor()
        try:
            cur.execute("DELETE FROM companies WHERE company_id=%s", (company_id,))
            mysql.connection.commit()
            flash('Company deleted successfully!', 'success')
        except pymysql.err.IntegrityError:
            mysql.connection.rollback()
            flash('Cannot delete this company — it has placement records. Delete those placements first.', 'danger')
        finally:
            cur.close()
        return redirect(url_for('companies'))
