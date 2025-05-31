import threading
from threading import Lock
from flask import (
    Blueprint, flash, g, redirect, render_template,render_template_string, request, url_for,current_app,jsonify
)
 
# from myapp.app import app
import pdfplumber 
import pandas as pd
import re
import json
from datetime import datetime, timedelta
from myapp.auth import login_required
from myapp.db import get_db
import sqlite3
import os
from jinja2 import Template
from PyPDF2 import PdfReader, PdfWriter

from collections import defaultdict 

from flask_mail import Message

import mimetypes
from email.mime.image import MIMEImage
import pprint
from werkzeug.exceptions import abort
bp = Blueprint('attendance', __name__)


# @bp.route('/')
# @login_required
# def index():
#     db = get_db()
#     employees = db.execute('SELECT * FROM employee').fetchall()
#     return render_template('attendance/index.html', employees=employees)


 
from sqlalchemy import create_engine

process_status = {
    'status': 'idle',
    'message': ''
  
}
 
FILE_PATH = os.getenv('FILE_PATH',"myapp/static/")

ALLOWED_EXTENSIONS = {'pdf'}


pdf_generation_lock = Lock()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/get-progress-status')
def get_progress_status():
    return jsonify(process_status)

@bp.route('/', methods=('GET', 'POST'))
@login_required
def index():
    # db = get_db()
    if request.method == 'POST':
        if pdf_generation_lock.locked():
            flash("PDF generation is already in progress. Please wait.", "error")
            process_status['status'] = 'busy'
            process_status['message'] = 'PDF generation is already in progress. Please wait.'
            # return jsonify({'error': 'PDF generation is already in progress. Please wait.'}), 400
            return redirect(url_for('attendance.index'))
         
        
        file = request.files.get('file')
    
        if not file or file.filename == '':
            flash('No file selected', 'error')
            # return jsonify({'error': 'No file uploaded'}), 400 
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('Invalid file format. Please upload .pdf file.', 'error')
            # return jsonify({'error': 'Invalid file format. Please upload .pdf file.'}), 400
            return redirect(request.url)
         
        try:
            file.save(FILE_PATH + "attn.pdf")
            process_status['status'] = 'busy'
            process_status['message'] = 'file uploaded successfully, processing...'
            # extract_attendance_data_from_pdf(FILE_PATH + "attn.pdf")  # Updated to call the function with the saved file path             
            process_attendance_data()  # Call the function to process the attendance data
            
            # flash("PDF generation started. Check your inbox or download section later.", "info")
            # flash('Attendance report sent successfully!', 'success')
        except Exception as e:
            flash(f'Error processing file: {e}', 'error')
        finally:
            pass
        
        # return 'Success', 200
        return redirect(url_for('attendance.index'))

    # If GET, show upload form
    return render_template('attendance/index.html')


def process_attendance_data():
   
    process_status['status'] = 'busy'
    process_status['message'] = 'Processing attendance data...'

    pdf_path = FILE_PATH+"attn.pdf" 
    # Step 1: Read all text from the PDF
    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

    lines = full_text.splitlines()


    # Step 2: Extract company metadata
    company_name = next((re.search(r'Company Name[:\-]?\s*(.+)', line) for line in lines if 'Company' in line), None)
    location = next((re.search(r'Location[:\-]?\s*(.+)', line) for line in lines if 'Location' in line), None)
    period = next((re.search(r'For Period\s*[:\-]?\s*(\d{1,2}-[A-Za-z]{3}-\d{4})\s*To\s*(\d{1,2}-[A-Za-z]{3}-\d{4})', line) for line in lines if 'Period' in line), None)


    company_name = company_name.group(1).strip() if company_name else "Unknown"
    location = location.group(1).strip() if location else "Unknown"
    start_date, end_date = period.groups() if period else ("Unknown", "Unknown")
    date_range = f"{start_date} to {end_date}"

    # Step 3: Convert start_date to datetime
    start_date_dt = datetime.strptime(start_date, "%d-%b-%Y") if start_date != "Unknown" else None

    # Step 4: Extract employee attendance
    emp_line_pattern = re.compile(r'^(\d+)\s+([A-Za-z. ]+?)(?:\s+\d{2}:\d{2}){1,}')
    employee_entries = []
    i = 0

    while i < len(lines):
        line = lines[i]
        match = emp_line_pattern.match(line)
        if match:
            employee_code = match.group(1)
            name = match.group(2).strip()
            times = []

            i += 1
            while i < len(lines) and not emp_line_pattern.match(lines[i]):
                times += re.findall(r'\b(?:\d{2}:\d{2}|A|WO-I)\b', lines[i])
                i += 1

            employee_entries.append({"employee_code": employee_code, "name": name, "entries": times})
        else:
            i += 1

    # Step 5: Create the DataFrame
    records = []
    for emp in employee_entries:
        employee_code, name, entries = emp["employee_code"], emp["name"], emp["entries"]
        day = 1
        j = 0
        while j < len(entries):
            in_time = entries[j] if j < len(entries) else None
            out_time = entries[j + 1] if j + 1 < len(entries) and re.match(r'\d{2}:\d{2}', entries[j + 1]) else None

            # Get actual date
            record_date = (start_date_dt + timedelta(days=day - 1)).strftime("%Y-%m-%d") if start_date_dt else f"Day {day}"

            # Handle attendance codes
            if in_time in ["A", "WO-I"]:
                records.append({
                    "employee_code": employee_code,
                    "name": name,
                    "date": record_date,
                    "in_time": in_time,
                    "out_time": None,
                    "company": company_name,
                    "location": location,
                    "date_range": date_range
                })
                j += 1
            else:
                records.append({
                    "employee_code": employee_code,
                    "name": name,
                    "date": record_date,
                    "in_time": in_time,
                    "out_time": out_time if out_time not in ["A", "WO-I"] else None,
                    "company": company_name,
                    "location": location,
                    "date_range": date_range
                })
                j += 2 if out_time else 1

            day += 1
    
    # Step 6: Final DataFrame
    attendance_df = pd.DataFrame(records)


    # Optional: save to CSV
    # df.to_csv(FILE_PATH+"attendance_final.csv", index=False)
    #print(df.head())

    
    grouped_df = attendance_df.groupby('employee_code', group_keys=False) \
        .apply(
            lambda g: pd.Series({
                'date_range': g['date_range'].iloc[0],
                'entries': g[['date', 'in_time', 'out_time', 'company', 'location']].to_dict(orient='records')
            }),
            include_groups=False
        ).reset_index() 
    
    employee_df = fetch_employee_data()
    attendance_df_selected = grouped_df[['employee_code', 'date_range', 'entries']]
    employee_df_selected = employee_df[['employee_code', 'name', 'email', 'pdf_password']]
    merged_df = pd.merge(attendance_df_selected, employee_df_selected, on='employee_code', how='left')

    # filter out rows with missing email
    merged_df = merged_df[merged_df['email'].notna()]
    save_to_json(merged_df)
    # flash('pdf preparing!', 'success')

    # flash("Preparing PDF reports. This may take a few minutes.", "info")
    process_status['message'] = 'Preparing PDF reports. This may take a few minutes.'
    process_status['status'] = 'busy'
    if not pdf_generation_lock.locked():
        thread = threading.Thread(target=makepdf,args=(current_app._get_current_object(), merged_df,))
        thread.start()
        flash("Your PDF is being generated. An email notification will arrive shortly", "info")
        # flash("PDF generation started.", "info")
    else:
        # If the lock is already held, notify the user
        print("PDF generation is already in progress.")
        # flash("PDF generation is already in progress. Please wait.", "warning")
    # flash('pdf prepared', 'success')
    # flash("PDF generation started. Check your inbox or download section later.", "success")
    # makepdf(merged_df)



def save_to_json(merged_df):
    # Convert to list of dicts if needed
    employee_data = merged_df.to_dict(orient='records')

    # pprint.pprint(employee_data)
    # print(employee_data)
    # data_to_save = grouped_data.to_dict(orient="records")
    with open(FILE_PATH+"attendance_grid.json", "w") as json_file:
        json.dump(employee_data, json_file, indent=4) 


def makepdf(app,merged_df):
    process_status['message'] = 'Generating PDF reports...'
    process_status['status'] = 'busy'
    employee_data = merged_df.to_dict(orient='records')
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Attendance Report - {{ name }}</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                padding: 30px;
            }
            h1, h2 {
                color: #333;
            }
            table {
                border-collapse: collapse;
                width: 100%;
                margin-top: 20px;
            }
            th, td {
                text-align: left;
                border: 1px solid #ccc;
                padding: 8px;
            }
            th {
                background-color: #f2f2f2;
            }
            .header {
                margin-bottom: 30px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Attendance Report</h1>
            <h2>Employee: {{ name }} ({{ employee_code }})</h2>
            {% if email %}<p>Email: {{ email }}</p>{% endif %}
            <p>Date Range: {{ date_range }}</p>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>In Time</th>
                    <th>Out Time</th>
                    <th>Company</th>
                    <th>Location</th>
                </tr>
            </thead>
            <tbody>
                {% for entry in entries %}
                <tr>
                    <td>{{ entry.date }}</td>
                    <td>{{ entry.in_time }}</td>
                    <td>{{ entry.out_time or '...' }}</td>
                    <td>{{ entry.company }}</td>
                    <td>{{ entry.location }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </body>
    </html>
    """
    
    import pdfkit

    config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")
    # Setup wkhtmltopdf path
    # config = pdfkit.configuration(wkhtmltopdf=r'/usr/bin/wkhtmltopdf')
    with pdf_generation_lock:
        with app.app_context():
            # Create PDFs for each employee
            for employee in employee_data:
                # template = Template(html_template)
                # rendered_html = template.render(
                #     name=employee["name"],
                #     employee_code=employee["employee_code"],
                #     email=employee.get("email"),
                #     pdf_password=employee.get("pdf_password", "123456"),
                #     date_range=employee.get("date_range", ""),
                #     entries=employee["entries"]
                # )
                rendered_html = render_template_string(
                    html_template,
                    name=employee["name"],
                    employee_code=employee["employee_code"],
                    email=employee.get("email", ""),
                    date_range=employee.get("date_range", ""),
                    entries=employee["entries"]
                )

                # File paths
                temp_pdf_path = os.path.join(FILE_PATH, "temp", f"{employee['employee_code']}_{employee['name'].replace(' ', '_')}.pdf")
                protected_pdf_path = os.path.join(FILE_PATH, "pdf", f"{employee['employee_code']}_{employee['name'].replace(' ', '_')}_protected.pdf")

                # Ensure directories exist
                os.makedirs(os.path.dirname(temp_pdf_path), exist_ok=True)
                os.makedirs(os.path.dirname(protected_pdf_path), exist_ok=True)

                # Generate PDF from HTML
                pdfkit.from_string(rendered_html, temp_pdf_path, configuration=config)

                # print(rendered_html)
                reader = PdfReader(temp_pdf_path)
                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)

                password = employee.get("pdf_password") or employee.get("employee_code") # fallback to employee_code
                writer.encrypt(password)

                with open(protected_pdf_path, "wb") as f:
                    writer.write(f)

                # Optional: Remove the temporary unprotected file
                # os.remove(temp_pdf_path) 

                body= render_template('mail/attendance_email_body.html', image_cid='logo_cid', name=employee["name"], employee_code=employee["employee_code"], date_range=employee.get("date_range", ""), entries=employee["entries"])

                if os.path.exists(protected_pdf_path):
                    process_status['message'] = 'PDF generated successfully. Sending email to ' + employee["name"]
                    process_status['status'] = 'sending_email'
                    send_email_with_attachment(
                        app,
                        subject="Attendance Report for " + employee["name"]+" (" + employee["employee_code"] + ") Period:  " + employee["date_range"],
                        body=body,
                        recipient=employee.get("email"),
                        attachment_path=protected_pdf_path
                    )
                else:
                    print(f"Failed to create PDF for {employee['name']}")
                
                
                # print(f"PDF generated and sent to {employee.get('email')}: {protected_pdf_path}")
                # add delay
                
            # flash(f'Mail sent to: {len(employee_data)} employees', 'success')
            #print("PDFs generated with attendance tables.")
    
    process_status['message'] = 'PDF generation completed successfully.'
    process_status['status'] = 'completed'





def send_email_with_attachment(app,subject, body, recipient, attachment_path):
    msg = Message(subject, recipients=[recipient])
    msg.html = body

    print("Root Path"+ app.root_path)
    image_abs_path = os.path.join(app.root_path, 'static', 'images', 'image001.jpg')
    image_rel_path = os.path.relpath(image_abs_path, start=app.root_path)

    with app.open_resource(image_rel_path) as img:
        msg.attach(
            filename="image001.jpg",
            content_type="image/jpeg",
            data=img.read(),
            disposition="inline",
            headers={'Content-ID': '<logo_cid>'}  # ✅ FIXED
        )
        
    if attachment_path:
        # Convert absolute path to relative path for open_resource
        try:
            rel_path = os.path.relpath(attachment_path, start=app.root_path)
            # print(f"Relative path: {rel_path}")
            # print(f"Attachment path: {os.path.basename(rel_path)}")
            with app.open_resource(rel_path) as fp:
                msg.attach(os.path.basename(attachment_path), "application/pdf", fp.read())

            app.extensions.get('mail').send(msg)
        except Exception as e:
            print(f"Error sending email to {recipient}: {e}")

def make_entries(group):
    return group[['date', 'in_time', 'out_time', 'company', 'location']] \
        .to_dict(orient='records')

def fetch_employee_data():
    db_path = os.path.join(os.getcwd(), 'instance', 'attendance.sqlite')
    conn = sqlite3.connect(db_path)

    employee_df = pd.read_sql_query("SELECT * FROM employee", conn)

    conn.close()
    return employee_df






def extract_attendance_data_from_pdf(file_with_path):
    pdf_path = file_with_path

    # Step 1: Read all text from the PDF
    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

    lines = full_text.splitlines()

    

    # Step 2: Extract company metadata
    company_name = next((re.search(r'Company Name[:\-]?\s*(.+)', line) for line in lines if 'Company' in line), None)
    location = next((re.search(r'Location[:\-]?\s*(.+)', line) for line in lines if 'Location' in line), None)
    period = next((re.search(r'For Period\s*[:\-]?\s*(\d{1,2}-[A-Za-z]{3}-\d{4})\s*To\s*(\d{1,2}-[A-Za-z]{3}-\d{4})', line) for line in lines if 'Period' in line), None)


    company_name = company_name.group(1).strip() if company_name else "Unknown"
    location = location.group(1).strip() if location else "Unknown"
    start_date, end_date = period.groups() if period else ("Unknown", "Unknown")
    date_range = f"{start_date} to {end_date}"

    # Step 3: Convert start_date to datetime
    start_date_dt = datetime.strptime(start_date, "%d-%b-%Y") if start_date != "Unknown" else None

    # Step 4: Extract employee attendance
    emp_line_pattern = re.compile(r'^(\d+)\s+([A-Za-z. ]+?)(?:\s+\d{2}:\d{2}){1,}')
    employee_entries = []
    i = 0

    while i < len(lines):
        line = lines[i]
        match = emp_line_pattern.match(line)
        if match:
            emp_id = match.group(1)
            name = match.group(2).strip()
            times = []

            i += 1
            while i < len(lines) and not emp_line_pattern.match(lines[i]):
                times += re.findall(r'\b(?:\d{2}:\d{2}|A|WO-I)\b', lines[i])
                i += 1

            employee_entries.append({"emp_id": emp_id, "name": name, "entries": times})
        else:
            i += 1

    # Step 5: Create the DataFrame
    records = []
    for emp in employee_entries:
        emp_id, name, entries = emp["emp_id"], emp["name"], emp["entries"]
        day = 1
        j = 0
        while j < len(entries):
            in_time = entries[j] if j < len(entries) else None
            out_time = entries[j + 1] if j + 1 < len(entries) and re.match(r'\d{2}:\d{2}', entries[j + 1]) else None

            # Get actual date
            record_date = (start_date_dt + timedelta(days=day - 1)).strftime("%Y-%m-%d") if start_date_dt else f"Day {day}"

            # Handle attendance codes
            if in_time in ["A", "WO-I"]:
                records.append({
                    "emp_id": emp_id,
                    "name": name,
                    "date": record_date,
                    "in_time": in_time,
                    "out_time": None,
                    "company": company_name,
                    "location": location,
                    "date_range": date_range
                })
                j += 1
            else:
                records.append({
                    "emp_id": emp_id,
                    "name": name,
                    "date": record_date,
                    "in_time": in_time,
                    "out_time": out_time if out_time not in ["A", "WO-I"] else None,
                    "company": company_name,
                    "location": location,
                    "date_range": date_range
                })
                j += 2 if out_time else 1

            day += 1

    # Step 6: Final DataFrame
    df = pd.DataFrame(records)

    # Optional: save to CSV
    df.to_csv(FILE_PATH + "attendance_final.csv", index=False)
    # print(df.head())

    

    # Save the records as a JSON file
    with open(FILE_PATH + "attendance_grid.json", "w") as json_file:
        json.dump(records, json_file, indent=4)

    # print("File saved as " + FILE_PATH + "attendance_grid.json")


