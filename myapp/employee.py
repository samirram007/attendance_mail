from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from myapp.auth import login_required
from myapp.db import get_db
import sqlite3

bp = Blueprint('employee', __name__)


@bp.route('/')
@login_required
def index():
    db = get_db()
    employees = db.execute('SELECT * FROM employee').fetchall()
    return render_template('employee/index.html', employees=employees)


@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        employee_code = request.form['employee_code']
        card_no = request.form['card_no']
        name = request.form['name']
        email = request.form['email']
        pdf_password = request.form['pdf_password']
        error = None

        if not employee_code:
            error = 'Employee Code is required.'
        if not card_no:
            error = 'Card No is required.'
        if not name:
            error = 'Employee Name is required.'
        if not email:
            error = 'Employee Email Id is required.'
        if not pdf_password:
            error = 'Pdf Password is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO employee (employee_code, card_no, name,email,pdf_password)'
                ' VALUES (?, ?, ?, ?, ?)',
                (employee_code, card_no, name, email, pdf_password)
            )
            db.commit()
            return redirect(url_for('employee.index'))

    return render_template('employee/create.html')


def get_post(id):
    employee = get_db().execute(
        'SELECT * FROM employee WHERE id = ?',
        (id,)
    ).fetchone()

    if employee is None:
        abort(404, f"Employee id {id} doesn't exist.")

    

    return employee



@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE post SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('employee.index'))

    return render_template('employee/update.html', post=post)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('employee.index'))

import pandas as pd
from sqlalchemy import create_engine
 


ALLOWED_EXTENSIONS = {'xls', 'xlsx'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/import_data', methods=('GET', 'POST'))
@login_required
def import_data():
    db = get_db()
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('Invalid file format. Please upload .xls or .xlsx file.', 'error')
            return redirect(request.url)

        try:
            ext = file.filename.rsplit('.', 1)[1].lower()
            # df = pd.read_excel(file, engine='xlrd' if ext == 'xls' else 'openpyxl')
            print(f"File extension: {ext}")
            if ext == 'xls':
                df = pd.read_excel(file, engine='xlrd')
            elif ext == 'xlsx':
                df = pd.read_excel(file, engine='openpyxl')
            else:
                flash('Unsupported file extension.', 'error')
                return redirect(request.url)
            # Optional: Rename or normalize columns if needed
            df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]

            required_columns = {'sl_no','employee_code', 'card_no', 'name', 'email', 'pdf_password'}
            if not required_columns.issubset(df.columns):
                flash('Missing required columns in Excel file.', 'error')
                return redirect(request.url)

          
            cursor = db.cursor()

            # Proper truncate for SQLite
            cursor.execute("DELETE FROM employee")  # delete all rows
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='employee'")  # reset autoincrement

            for _, row in df.iterrows():
                try:
                    cursor.execute("""
                        INSERT INTO employee (id,employee_code, card_no, name, email, pdf_password)
                        VALUES (?,?, ?, ?, ?, ?)
                    """, (
                        str(row['sl_no']).strip(),
                        str(row['employee_code']).strip(),
                        str(row['card_no']).strip(),
                        str(row['name']).strip(),
                        str(row['email']).strip() if pd.notna(row['email']) else None,
                        str(row['pdf_password']).strip() if pd.notna(row['pdf_password']) else None
                    ))
                except sqlite3.IntegrityError:
                    # Skip duplicate or conflicting records
                    flash(f"Skipped duplicate or conflicting record: {row['employee_code']}", 'warning')
                    continue

            db.commit()
            flash('Employee data imported successfully!', 'success')
        except Exception as e:
            flash(f'Error processing file: {e}', 'error')
        finally:
            db.close()

        return redirect(url_for('employee.index'))

    # If GET, show upload form
    return render_template('employee/import.html')


