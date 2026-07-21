import os
import json
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid # Used to generate unique random names for files
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'your_super_secret_key' # Required for session management

# Configure File Uploads
UPLOAD_FOLDER = 'static/uploads/evidence'
DOCUMENT_UPLOAD_FOLDER = 'static/uploads/documents'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt', 'csv', 'xlsx', 'xls'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOCUMENT_UPLOAD_FOLDER'] = DOCUMENT_UPLOAD_FOLDER

# Ensure the upload folder exists when the app starts
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOCUMENT_UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database connection configuration
# --- SUPABASE CONNECTION SETUP ---
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_PORT = os.getenv('DB_PORT', '5432')

def get_db_connection():
    missing = [name for name, value in (
        ('DB_HOST', DB_HOST),
        ('DB_NAME', DB_NAME),
        ('DB_USER', DB_USER),
        ('DB_PASSWORD', DB_PASSWORD),
    ) if not value]
    if missing:
        error_message = f"Missing database configuration values: {', '.join(missing)}"
        app.logger.error(error_message)
        raise RuntimeError(error_message)

    try:
        return psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
    except psycopg2.OperationalError as err:
        app.logger.error(f"Database connection failed: {err}")
        raise
    except Exception as err:
        app.logger.error(f"Unexpected error creating database connection: {err}")
        raise

def log_action(user_id, action_description):
    """Utility function to easily record system events."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO auditlog (userid, action, logtime) VALUES (%s, %s, %s)",
            (user_id, action_description, current_time)
        )
        conn.commit()
    except Exception as e:
        print(f"Audit log error: {e}")
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'userid' not in session:
            flash('Please log in to access this page.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'userid' not in session:
                flash('Please log in to access this page.')
                return redirect(url_for('login'))

            current_role = session.get('role')
            current_role_id = session.get('roleid')
            allowed_roles = {str(role) for role in roles}

            if current_role in allowed_roles or str(current_role_id) in allowed_roles:
                return f(*args, **kwargs)

            flash('You do not have permission to access this page.')
            return redirect(url_for('dashboard'))
        return decorated_function
    return decorator

@app.route('/view_mlef/<int:case_id>')
@login_required
def view_mlef(case_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT summary FROM medical_report WHERE caseid = %s", (case_id,))
        row = cursor.fetchone()

        if not row or not row.get('summary'):
            flash('No saved MLEF drawing found for this case.')
            return redirect(url_for('dashboard'))

        try:
            summary_data = json.loads(row['summary'])
        except json.JSONDecodeError:
            flash('Saved MLEF data is corrupt or invalid.')
            return redirect(url_for('dashboard'))

        anatomical_drawing = summary_data.get('anatomical_drawing', '')
        exam_date = summary_data.get('exam_date', '')

        return render_template(
            'view_mlef.html',
            case_id=case_id,
            anatomical_drawing=anatomical_drawing,
            exam_date=exam_date
        )
    except psycopg2.Error as err:
        app.logger.error(f"Error loading MLEF view for case {case_id}: {err}")
        flash('Unable to load the saved MLEF drawing.')
        return redirect(url_for('dashboard'))
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

@app.route('/save_mlef', methods=['POST'])
@login_required
def save_mlef():
    payload = request.get_json(silent=True)
    if not payload:
        return {'error': 'Invalid JSON payload.'}, 400

    case_id = payload.get('case_id')
    exam_date = payload.get('exam_date')
    anatomical_drawing = payload.get('anatomical_drawing')

    if not isinstance(case_id, int) or case_id <= 0:
        return {'error': 'Invalid case_id; must be a positive integer.'}, 400

    try:
        datetime.strptime(exam_date, '%Y-%m-%d')
    except (ValueError, TypeError):
        return {'error': 'Invalid exam_date; expected YYYY-MM-DD.'}, 400

    if not isinstance(anatomical_drawing, str) or not anatomical_drawing.startswith('data:image/png;base64,'):
        return {'error': 'Invalid anatomical_drawing; must start with data:image/png;base64,.'}, 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO medical_report (caseid, summary) VALUES (%s, %s) "
            "ON CONFLICT (caseid) DO UPDATE SET summary = EXCLUDED.summary",
            (case_id, json.dumps({'exam_date': exam_date, 'anatomical_drawing': anatomical_drawing}))
        )
        conn.commit()
        return {'success': True, 'case_id': case_id}, 200
    except psycopg2.Error as err:
        if conn is not None:
            conn.rollback()
        app.logger.error(f"Failed to save MLEF for case {case_id}: {err}")
        return {'error': 'Database error saving MLEF.'}, 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

@app.route('/saved_medico_legal_report/<int:case_id>')
@login_required
def saved_medico_legal_report(case_id):
    if session.get('role') not in ['Doctor', 'JMO', 'Admin']:
        flash('Access denied: Saved medico-legal reports are only available to medical staff.')
        return redirect(url_for('dashboard'))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT summary FROM medical_report WHERE caseid = %s", (case_id,))
        row = cursor.fetchone()

        if not row or not row.get('summary'):
            flash('No saved medico-legal report found for this case.')
            return redirect(url_for('view_cases'))

        try:
            summary_data = json.loads(row['summary'])
        except json.JSONDecodeError:
            flash('Saved medico-legal report data is invalid.')
            return redirect(url_for('view_cases'))

        drawing_base64 = summary_data.get('anatomical_drawing', '')
        exam_date = summary_data.get('exam_date', '')

        return render_template(
            'saved_medico_legal_report.html',
            exam_date=exam_date,
            drawing_base64=drawing_base64
        )
    except psycopg2.Error as err:
        app.logger.error(f"Error loading saved medico-legal report for case {case_id}: {err}")
        flash('Unable to load the saved medico-legal report at this time.')
        return redirect(url_for('view_cases'))
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Retrieve the user record by username only, then verify the password hash
        cursor.execute(
            """
            SELECT u.userid, u.username, u.staffid, u.passwordhash, s.fullname, s.roleid, r.rolename
            FROM users u
            JOIN staff s ON u.staffid = s.staffid
            JOIN role r ON s.roleid = r.roleid
            WHERE u.username = %s
            """,
            (username,)
        )
        account = cursor.fetchone()

        cursor.close()
        conn.close()

        if account and check_password_hash(account['passwordhash'], password):
            session['loggedin'] = True
            session['id'] = account['userid']
            session['userid'] = account['userid']
            session['username'] = account['username']
            session['role'] = account['rolename']
            session['roleid'] = account['roleid']
            session['staff_id'] = account['staffid']

            log_action(account['userid'], "User logged into the system.")
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials')

    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if 'loggedin' in session:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Fetch a quick statistic for the dashboard (e.g., Total Open Cases)
        cursor.execute(
            """
            SELECT COUNT(*) AS open_cases
            FROM medicolegalcase m
            JOIN casestatus cs ON m.statusid = cs.statusid
            WHERE cs.statusname = 'Open'
            """
        )
        result = cursor.fetchone()
        open_cases = result['open_cases'] if result else 0

        cursor.execute("""
            SELECT a.logid AS logid, a.action AS action, a.logtime AS logtime,
                   u.username AS username, s.fullname AS fullname, r.rolename AS role
            FROM auditlog a
            LEFT JOIN users u ON a.userid = u.userid
            LEFT JOIN staff s ON u.staffid = s.staffid
            LEFT JOIN role r ON s.roleid = r.roleid
            ORDER BY a.logtime DESC
            LIMIT 5
        """)
        recent_activity = cursor.fetchall()
        
        cursor.close()
        conn.close()

        log_action(session['id'], "Viewed the dashboard.")

        # Render the HTML template and pass the data to it
        return render_template('dashboard.html', 
                               username=session['username'], 
                               role=session['role'], 
                               open_cases=open_cases,
                               recent_activity=recent_activity)
    
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    if session.get('loggedin') and session.get('id'):
        log_action(session['id'], "User logged out of the system.")
    session.clear()
    return redirect(url_for('login'))

@app.route('/register_patient', methods=['GET', 'POST'])
def register_patient():
    # Ensure the user is logged in
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    # Optional Security: Restrict this page to Admin and Clerical staff
    if session['role'] not in ['Admin', 'Clerical']:
        flash("You do not have permission to register patients.")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        full_name = request.form['full_name']
        date_of_birth = request.form['date_of_birth']
        gender = request.form['gender']
        address = request.form['address']
        contact_no = request.form['contact_no']
        next_of_kin_name = request.form['next_of_kin_name']
        next_of_kin_relationship = request.form['next_of_kin_relationship']
        next_of_kin_contact = request.form['next_of_kin_contact']
        condition_details = request.form['condition_details']

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        try:
            cursor.execute(
                "INSERT INTO patient (fullname, dateofbirth, gender, address, contactno) VALUES (%s, %s, %s, %s, %s) RETURNING patientid",
                (full_name, date_of_birth, gender, address, contact_no)
            )
            new_patient_id = cursor.fetchone()['patientid']

            cursor.execute(
                "INSERT INTO nextofkin (patientid, fullname, relationship, contactno) VALUES (%s, %s, %s, %s)",
                (new_patient_id, next_of_kin_name, next_of_kin_relationship, next_of_kin_contact)
            )

            cursor.execute(
                "INSERT INTO patientmedicalhistory (patientid, conditiondetails) VALUES (%s, %s)",
                (new_patient_id, condition_details)
            )

            conn.commit()
            log_action(session['id'], "Registered a new patient.")
            flash('Patient registered successfully!')
        except psycopg2.Error as err:
            conn.rollback()
            flash(f'Database Error: {err}')

        cursor.close()
        conn.close()

        return redirect(url_for('register_patient'))

    return render_template('register_patient.html', role=session['role'])

@app.route('/create_case', methods=['GET', 'POST'])
@login_required
def create_case():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    # Restrict to authorized roles
    if session['role'] not in ['Admin', 'Doctor', 'JMO']:
        flash("You do not have permission to manage cases.")
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        try:
            patient_id = int(request.form['patient_id'])
            case_type_id = int(request.form['casetypeid'])
            status_id = int(request.form['statusid'])
            assigned_doctor = int(request.form['assigneddoctor'])
            officer_id = int(request.form['officerid'])
            location_id = int(request.form.get('locationid', 0))
            incident_date = request.form['incident_date']

            cursor.execute("""
                INSERT INTO medicolegalcase (
                    patientid, casetypeid, statusid, assigneddoctor, officerid, locationid, incidentdate
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (patient_id, case_type_id, status_id, assigned_doctor, officer_id, location_id, incident_date))
            conn.commit()
            log_action(session['id'], "Created a new medico-legal case.")
            flash('Medico-Legal Case created successfully!')
        except (ValueError, psycopg2.Error) as err:
            flash(f'Database Error: {err}')
        
        cursor.close()
        conn.close()
        return redirect(url_for('create_case'))

    # For GET requests: Fetch data for the dropdown menus
    cursor.execute("SELECT patientid, fullname FROM patient")
    patients = cursor.fetchall()

    cursor.execute("""
        SELECT s.staffid, s.fullname
        FROM staff s
        JOIN role r ON s.roleid = r.roleid
        WHERE r.rolename IN ('Doctor', 'JMO')
    """)
    doctors = cursor.fetchall()

    cursor.execute("SELECT casetypeid, casetypename FROM casetype")
    case_types = cursor.fetchall()

    cursor.execute("SELECT statusid, statusname FROM casestatus")
    case_statuses = cursor.fetchall()

    cursor.execute("SELECT officerid, fullname, badgenumber FROM investigatingofficer")
    officers = cursor.fetchall()

    cursor.execute("SELECT stationid, stationname FROM policestation")
    policestations = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template(
        'create_case.html',
        patients=patients,
        doctors=doctors,
        case_types=case_types,
        case_statuses=case_statuses,
        officers=officers,
        policestations=policestations,
        role=session['role']
    )

@app.route('/mlef_form')
@login_required
def mlef_form():
    if session.get('role') not in ['Doctor', 'JMO', 'Admin']:
        flash('Access denied: MLEF form is only available to medical staff.')
        return redirect(url_for('dashboard'))
    return render_template('mlef_form.html')

@app.route('/view_cases', methods=['GET'])
@login_required
def view_cases():
    search_query = request.args.get('search', '')
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    query = """
        SELECT c.caseid, p.fullname AS patientname, s.fullname AS jmoname,
               ct.casetypename AS casetype, c.incidentdate, ps.stationname AS policestation, cs.statusname AS casestatus,
               c.assigneddoctor AS assignedjmo
        FROM medicolegalcase c
        LEFT JOIN patient p ON c.patientid = p.patientid
        LEFT JOIN staff s ON c.assigneddoctor = s.staffid
        LEFT JOIN casetype ct ON c.casetypeid = ct.casetypeid
        LEFT JOIN policestation ps ON c.locationid = ps.stationid
        LEFT JOIN casestatus cs ON c.statusid = cs.statusid
        WHERE 1=1
    """
    params = []

    is_admin = session.get('role') == 'Admin' or str(session.get('roleid')) == '1'
    if not is_admin:
        query += " AND c.assigneddoctor = %s"
        params.append(session.get('staff_id') or session.get('userid'))
        
    if search_query:
        query += " AND (CAST(c.caseid AS TEXT) LIKE %s OR p.fullname ILIKE %s OR cs.statusname ILIKE %s)"
        like_pattern = f"%{search_query}%"
        params.extend([like_pattern, like_pattern, like_pattern])
        
    cursor.execute(query, tuple(params))
    cases = cursor.fetchall()

    log_action(session['id'], "Viewed the cases list.")
    
    cursor.close()
    conn.close()
    
    return render_template('view_cases.html', cases=cases, search_query=search_query, current_user_id=session.get('staff_id') or session.get('userid'), role=session['role'])

@app.route('/doctor_dashboard')
@login_required
def doctor_dashboard():
    if session.get('role') not in ['Doctor', 'JMO', 'Admin']:
        flash('Access denied: Doctor dashboard is reserved for medical staff.')
        return redirect(url_for('dashboard'))
    return redirect(url_for('view_cases'))

@app.route('/update_case_status', methods=['POST'])
def update_case_status():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
        
    case_id = request.form['case_id']
    new_status = request.form['case_status']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE MedicoLegalCase SET CaseStatus = %s WHERE CaseID = %s", (new_status, case_id))
    conn.commit()
    
    # Optional: Log this action using our helper function!
    log_action(session['id'], f"Updated case status for {case_id} to {new_status}")
    
    cursor.close()
    conn.close()
    
    flash(f"Case {case_id} status updated to {new_status}!")
    return redirect(url_for('view_cases'))

@app.route('/postmortem', methods=['GET', 'POST'])
def postmortem():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    # Restrict access to medical personnel
    if session['role'] not in ['Admin', 'Doctor', 'JMO']:
        flash("You do not have permission to enter postmortem findings.")
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        case_id = request.form['case_id']
        doctor_id = request.form['doctor_id']
        icd10_code = request.form['icd10code']
        date_of_exam = request.form['date_of_exam']
        findings = request.form['findings']

        try:
            cursor.execute(
                """
                INSERT INTO postmortem (caseid, doctorid, icd10code, dateofexam, findings)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (case_id, doctor_id, icd10_code, date_of_exam, findings)
            )
            conn.commit()
            log_action(session['id'], "Recorded a postmortem report.")
            flash('Postmortem report saved securely!')
        except psycopg2.Error as err:
            conn.rollback()
            flash(f'Database Error: {err}')

        cursor.close()
        conn.close()
        return redirect(url_for('postmortem'))

    cursor.execute("""
        SELECT m.caseid, m.patientid, m.incidentdate
        FROM medicolegalcase m
        JOIN casestatus c ON m.statusid = c.statusid
        WHERE c.statusname != 'Closed'
        ORDER BY m.caseid
    """)
    cases = cursor.fetchall()

    cursor.execute("SELECT staffid, fullname FROM staff WHERE roleid IN (SELECT roleid FROM role WHERE rolename IN ('Doctor', 'JMO'))")
    doctors = cursor.fetchall()

    cursor.execute("SELECT icd10code, description FROM causeofdeath ORDER BY icd10code")
    cause_of_death_codes = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('postmortem.html', cases=cases, doctors=doctors, cause_of_death_codes=cause_of_death_codes)

@app.route('/medical_findings', methods=['GET', 'POST'])
def medical_findings():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    if session['role'] not in ['Admin', 'Doctor', 'JMO']:
        flash("You do not have permission to manage medical findings.")
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        submission_type = request.form.get('submission_type')
        case_id = request.form['case_id']
        doctor_id = request.form['doctor_id']
        findings = request.form['findings']

        try:
            if submission_type == 'clinical':
                examination_date = request.form['examination_date']
                cursor.execute(
                    """
                    INSERT INTO clinicalexamination (caseid, doctorid, examinationdate, findings)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (case_id, doctor_id, examination_date, findings)
                )
                flash('Clinical examination saved successfully!')
            elif submission_type == 'postmortem':
                icd10_code = request.form['icd10code']
                date_of_exam = request.form['date_of_exam']
                cursor.execute(
                    """
                    INSERT INTO postmortem (caseid, doctorid, icd10code, dateofexam, findings)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (case_id, doctor_id, icd10_code, date_of_exam, findings)
                )
                flash('Postmortem report saved successfully!')
            else:
                flash('Invalid submission type.')

            conn.commit()
            log_action(session['id'], "Recorded medical findings.")
        except psycopg2.Error as err:
            conn.rollback()
            flash(f'Database Error: {err}')

        cursor.close()
        conn.close()
        return redirect(url_for('medical_findings'))

    cursor.execute("""
        SELECT m.caseid
        FROM medicolegalcase m
        JOIN casestatus cs ON m.statusid = cs.statusid
        WHERE cs.statusname != 'Closed'
        ORDER BY m.caseid
    """)
    cases = cursor.fetchall()

    cursor.execute("SELECT staffid, fullname FROM staff WHERE roleid IN (SELECT roleid FROM role WHERE rolename IN ('Doctor', 'JMO')) ORDER BY fullname")
    doctors = cursor.fetchall()

    cursor.execute("SELECT icd10code, description FROM causeofdeath ORDER BY icd10code")
    cause_of_death_codes = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('medical_findings.html', cases=cases, doctors=doctors, cause_of_death_codes=cause_of_death_codes)

@app.route('/manage_evidence', methods=['GET', 'POST'])
def manage_evidence():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    if session['role'] not in ['Admin', 'Lab', 'Doctor', 'JMO']:
        flash("You do not have permission to manage evidence.")
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        case_id = request.form['case_id']
        category_id = int(request.form['categoryid'])
        locker_id = int(request.form['lockerid'])
        collected_by = int(request.form['collected_by'])
        received_by = int(request.form['received_by'])
        collection_date = request.form['collection_date']
        status = request.form['status']

        filename = None
        if 'evidence_image' in request.files:
            file = request.files['evidence_image']
            if file and file.filename != '' and allowed_file(file.filename):
                original_filename = secure_filename(file.filename)
                unique_id = str(uuid.uuid4())[:8]
                filename = f"{case_id}_{unique_id}_{original_filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

        try:
            cursor.execute(
                """
                INSERT INTO evidence (caseid, categoryid, lockerid, collectedby, collectiondate, status)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING evidenceid
                """,
                (case_id, category_id, locker_id, collected_by, collection_date, status)
            )
            new_evidence_id = cursor.fetchone()['evidenceid']

            if filename:
                cursor.execute(
                    "INSERT INTO evidenceimage (evidenceid, imagepath) VALUES (%s, %s)",
                    (new_evidence_id, filename)
                )

            cursor.execute(
                """
                INSERT INTO chainofcustody (evidenceid, releasedby, receivedby, transfertime, purpose)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (new_evidence_id, collected_by, received_by, collection_date, 'Initial Evidence Logging')
            )

            conn.commit()
            log_action(session['id'], f"Logged evidence for case {case_id}")
            flash('Evidence and chain of custody logged securely!')
        except (ValueError, psycopg2.Error) as err:
            conn.rollback()
            flash(f'Database Error: {err}')

        cursor.close()
        conn.close()
        return redirect(url_for('manage_evidence'))

    cursor.execute("SELECT caseid FROM medicolegalcase ORDER BY caseid")
    cases = cursor.fetchall()

    cursor.execute("SELECT categoryid, categoryname FROM evidencecategory ORDER BY categoryname")
    categories = cursor.fetchall()

    cursor.execute("SELECT lockerid, roomname, temperaturezone FROM storagelocker ORDER BY roomname")
    lockers = cursor.fetchall()

    cursor.execute("SELECT staffid, fullname FROM staff ORDER BY fullname")
    staff = cursor.fetchall()

    cursor.execute("""
        SELECT e.evidenceid, e.caseid, e.collectiondate, e.status,
               c.categoryname, l.roomname AS lockername,
               collected.fullname AS collectedby_name,
               received.fullname AS receivedby_name,
               i.imagepath
        FROM evidence e
        LEFT JOIN evidencecategory c ON e.categoryid = c.categoryid
        LEFT JOIN storagelocker l ON e.lockerid = l.lockerid
        LEFT JOIN staff collected ON e.collectedby = collected.staffid
        LEFT JOIN chainofcustody coc ON e.evidenceid = coc.evidenceid
        LEFT JOIN staff received ON coc.receivedby = received.staffid
        LEFT JOIN evidenceimage i ON e.evidenceid = i.evidenceid
        ORDER BY e.evidenceid DESC
    """)
    evidence_list = cursor.fetchall()

    log_action(session['id'], "Viewed evidence management.")

    cursor.close()
    conn.close()

    return render_template(
        'manage_evidence.html',
        cases=cases,
        categories=categories,
        lockers=lockers,
        staff=staff,
        evidence_list=evidence_list
    )

@app.route('/lab_test', methods=['GET', 'POST'])
def lab_test():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    # Restrict to lab staff and admins
    if session['role'] not in ['Admin', 'Lab']:
        flash("You do not have permission to record laboratory tests.")
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        evidence_id = request.form['evidence_id']
        lab_staff_id = request.form['lab_staff_id']
        test_type = request.form['test_type']
        result = request.form['result']
        test_date = request.form['test_date']

        cursor.execute(
            '''INSERT INTO LaboratoryTest (EvidenceID, LabStaffID, TestType, Result, TestDate) 
               VALUES (%s, %s, %s, %s, %s)''',
            (evidence_id, lab_staff_id, test_type, result, test_date)
        )
        conn.commit()
        log_action(session['id'], "Recorded laboratory test results.")
        flash('Laboratory test results saved successfully!')
        return redirect(url_for('lab_test'))

    # Fetch data for the dropdowns
    cursor.execute("""
        SELECT e.evidenceid, ec.categoryname AS evidencetype, e.caseid
        FROM evidence e
        JOIN evidencecategory ec ON e.categoryid = ec.categoryid
        WHERE e.status IN ('Stored', 'In Lab')
    """)
    evidence_items = cursor.fetchall()

    cursor.execute("""
        SELECT s.staffid, s.fullname
        FROM staff s
        JOIN role r ON s.roleid = r.roleid
        WHERE r.rolename IN ('Lab', 'Admin')
    """)
    lab_staff = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('lab_test.html', evidence_items=evidence_items, lab_staff=lab_staff)

@app.route('/manage_documents', methods=['GET', 'POST'])
def manage_documents():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    if session['role'] not in ['Admin', 'Doctor', 'JMO', 'Lab']:
        flash("You do not have permission to manage documents.")
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        case_id = request.form['case_id']
        document_type = request.form['document_type']
        uploaded_file = request.files.get('document_file')

        if not uploaded_file or uploaded_file.filename == '':
            flash('Please select a file to upload.')
            cursor.close()
            conn.close()
            return redirect(url_for('manage_documents'))

        if not allowed_file(uploaded_file.filename):
            flash('Unsupported file type.')
            cursor.close()
            conn.close()
            return redirect(url_for('manage_documents'))

        filename = secure_filename(uploaded_file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        save_path = os.path.join(app.config['DOCUMENT_UPLOAD_FOLDER'], unique_filename)
        uploaded_file.save(save_path)
        relative_path = os.path.join('uploads', 'documents', unique_filename).replace('\\', '/')

        try:
            cursor.execute(
                """
                INSERT INTO document (caseid, documenttype, filepath)
                VALUES (%s, %s, %s)
                """,
                (case_id, document_type, relative_path)
            )
            conn.commit()
            log_action(session['id'], f"Uploaded a document for case {case_id}.")
            flash('Document uploaded successfully!')
        except psycopg2.Error as err:
            conn.rollback()
            flash(f'Database Error: {err}')

        cursor.close()
        conn.close()
        return redirect(url_for('manage_documents'))

    cursor.execute("""
        SELECT m.caseid
        FROM medicolegalcase m
        JOIN casestatus c ON m.statusid = c.statusid
        WHERE c.statusname != 'Closed'
        ORDER BY m.caseid
    """)
    cases = cursor.fetchall()

    cursor.execute("""
        SELECT d.documentid, d.caseid, d.documenttype, d.filepath, m.caseid AS case_number
        FROM document d
        JOIN medicolegalcase m ON d.caseid = m.caseid
        ORDER BY d.documentid DESC
    """)
    documents = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('documents.html', cases=cases, documents=documents, role=session['role'])

@app.route('/download_document/<int:documentid>')
def download_document(documentid):
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT filepath FROM document WHERE documentid = %s", (documentid,))
    document_row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not document_row or not document_row.get('filepath'):
        flash('Document not found.')
        return redirect(url_for('manage_documents'))

    filepath = document_row['filepath']
    filename = os.path.basename(filepath)
    return send_from_directory(directory='static/uploads/documents', path=filename, as_attachment=True)


@app.route('/manage_staff', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def manage_staff():
    # Strict security check: Kick out anyone who isn't logged in or isn't an Admin
    if 'loggedin' not in session or session.get('role') != 'Admin':
        flash("Access Denied: You must be an Administrator to view this page.")
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        full_name = request.form['full_name']
        dept_id = int(request.form['deptid'])
        role_id = int(request.form['roleid'])
        contact_no = request.form['contact_no']
        username = request.form['username']
        password = request.form['password']

        try:
            cursor.execute(
                "INSERT INTO staff (fullname, contactno, deptid, roleid) VALUES (%s, %s, %s, %s) RETURNING staffid",
                (full_name, contact_no, dept_id, role_id)
            )
            new_staff_id = cursor.fetchone()['staffid']
            hashed_pw = generate_password_hash(password)

            cursor.execute(
                "INSERT INTO users (staffid, username, passwordhash) VALUES (%s, %s, %s)",
                (new_staff_id, username, hashed_pw)
            )
            conn.commit()
            log_action(session['id'], "Created a new staff account.")
            flash('Staff account created successfully!')

        except (ValueError, psycopg2.Error) as err:
            conn.rollback()
            flash(f'Database Error: {err}')

        cursor.close()
        conn.close()
        return redirect(url_for('manage_staff'))

    cursor.execute("""
        SELECT s.staffid, s.fullname, s.contactno, d.deptname, r.rolename, u.username
        FROM staff s
        LEFT JOIN department d ON s.deptid = d.deptid
        LEFT JOIN role r ON s.roleid = r.roleid
        LEFT JOIN users u ON s.staffid = u.staffid
        ORDER BY s.staffid
    """)
    staff_list = cursor.fetchall()

    cursor.execute("SELECT deptid, deptname FROM department ORDER BY deptname")
    departments = cursor.fetchall()

    cursor.execute("SELECT roleid, rolename, accesslevel FROM role ORDER BY rolename")
    roles = cursor.fetchall()

    log_action(session['id'], "Viewed staff management page.")

    cursor.close()
    conn.close()

    return render_template('manage_staff.html', staff_list=staff_list, departments=departments, roles=roles)

@app.route('/edit_staff/<int:staff_id>', methods=['GET', 'POST'])
def edit_staff(staff_id):
    if 'loggedin' not in session or session.get('role') != 'Admin':
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        dept_id = int(request.form['deptid'])
        role_id = int(request.form['roleid'])

        try:
            cursor.execute(
                "UPDATE staff SET deptid = %s, roleid = %s WHERE staffid = %s",
                (dept_id, role_id, staff_id)
            )
            conn.commit()
            log_action(session['id'], "Updated a staff role.")
            flash('Staff details updated successfully!')
        except psycopg2.Error as err:
            conn.rollback()
            flash(f'Database Error: {err}')

        cursor.close()
        conn.close()
        return redirect(url_for('manage_staff'))

    cursor.execute("""
        SELECT s.staffid, s.fullname, s.deptid, s.roleid, d.deptname, r.rolename
        FROM staff s
        LEFT JOIN department d ON s.deptid = d.deptid
        LEFT JOIN role r ON s.roleid = r.roleid
        WHERE s.staffid = %s
    """, (staff_id,))
    staff_member = cursor.fetchone()

    cursor.execute("SELECT deptid, deptname FROM department ORDER BY deptname")
    departments = cursor.fetchall()

    cursor.execute("SELECT roleid, rolename FROM role ORDER BY rolename")
    roles = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('edit_staff.html', staff=staff_member, departments=departments, roles=roles)

@app.route('/delete_staff/<int:staff_id>', methods=['POST'])
def delete_staff(staff_id):
    if 'loggedin' not in session or session.get('role') != 'Admin':
        return redirect(url_for('dashboard'))
    
    # Security: Prevent the Admin from accidentally deleting their own logged-in account
    if staff_id == session.get('staff_id'):
        flash('Error: You cannot delete your own active administrator account.')
        return redirect(url_for('manage_staff'))

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Deleting the staff member automatically cascades to delete their login user account
    cursor.execute("DELETE FROM Staff WHERE StaffID = %s", (staff_id,))
    conn.commit()
    log_action(session['id'], "Deleted a staff account from the system.")
    
    cursor.close()
    conn.close()
    
    flash('Staff account securely removed from the system.')
    return redirect(url_for('manage_staff'))

@app.route('/audit_logs')
def audit_logs():
    # Strict Security Check
    if 'loggedin' not in session or session.get('role') != 'Admin':
        flash("Access Denied: You must be an Administrator to view system logs.")
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Join tables to get readable names instead of just User IDs
    # ORDER BY LogTime DESC ensures the newest actions are at the top
    query = """
        SELECT a.logid AS logid, a.action AS action, a.logtime AS logtime,
               u.username AS username, s.fullname AS fullname, r.rolename AS role
        FROM auditlog a
        LEFT JOIN users u ON a.userid = u.userid
        LEFT JOIN staff s ON u.staffid = s.staffid
        LEFT JOIN role r ON s.roleid = r.roleid
        ORDER BY a.logtime DESC
        LIMIT 200
    """
    cursor.execute(query)
    logs = cursor.fetchall()

    print("AUDIT LOGS DEBUG:", logs)
    if logs:
        print("AUDIT LOG KEYS:", list(logs[0].keys()))

    log_action(session['id'], "Viewed audit logs.")
    
    cursor.close()
    conn.close()

    return render_template('audit_logs.html', logs=logs)

@app.route('/manage_patients')
def manage_patients():
    if 'loggedin' not in session or session['role'] not in ['Admin', 'Clerical']:
        flash("Access Denied: Only Clerical staff can manage patient records.")
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM Patient ORDER BY PatientID DESC")
    patients = cursor.fetchall()

    log_action(session['id'], "Viewed patient management page.")

    cursor.close()
    conn.close()

    return render_template('manage_patients.html', patients=patients)

@app.route('/edit_patient/<int:patient_id>', methods=['GET', 'POST'])
def edit_patient(patient_id):
    if 'loggedin' not in session or session['role'] not in ['Admin', 'Clerical']:
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if request.method == 'POST':
        full_name = request.form['full_name']
        age = request.form['age']
        gender = request.form['gender']
        contact_info = request.form['contact_info']
        address = request.form['address']

        cursor.execute(
            "UPDATE Patient SET FullName=%s, Age=%s, Gender=%s, ContactInfo=%s, Address=%s WHERE PatientID=%s",
            (full_name, age, gender, contact_info, address, patient_id)
        )
        conn.commit()
        log_action(session['id'], f"Updated patient record for PatientID: {patient_id}")
        flash('Patient details updated successfully!')
        return redirect(url_for('manage_patients'))

    # GET: Fetch current details for the form
    cursor.execute("SELECT * FROM Patient WHERE PatientID = %s", (patient_id,))
    patient = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('edit_patient.html', patient=patient)

@app.route('/reports')
def reports():
    # Security: Restrict reports to medical directors and admins
    if 'loggedin' not in session or session.get('role') not in ['Admin', 'Doctor', 'JMO']:
        flash("Access Denied: Only authorized medical staff can view system analytics.")
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # 1. Case Status Breakdown (Open vs Pending vs Closed)
    cursor.execute("SELECT CaseStatus, COUNT(*) as count FROM MedicoLegalCase GROUP BY CaseStatus")
    case_status_data = cursor.fetchall()

    # 2. Incident Type Breakdown (Assault, Accident, etc.)
    cursor.execute("SELECT CaseType, COUNT(*) as count FROM MedicoLegalCase GROUP BY CaseType")
    case_type_data = cursor.fetchall()

    # 3. Monthly Statistics (Grouping by Year-Month)
    cursor.execute("""
        SELECT TO_CHAR(incidentdate, 'YYYY-MM') as monthlabel, COUNT(*) as casecount
        FROM medicolegalcase
        GROUP BY monthlabel
        ORDER BY monthlabel DESC
        LIMIT 6
    """)
    monthly_data = cursor.fetchall()

    # 4. Pending Action Items
    cursor.execute("SELECT COUNT(*) as pending_cases FROM MedicoLegalCase WHERE CaseStatus != 'Closed'")
    pending_cases = cursor.fetchone()['pending_cases']

    cursor.execute("SELECT COUNT(*) as pending_reports FROM CourtReport WHERE Status != 'Submitted'")
    pending_reports = cursor.fetchone()['pending_reports']

    log_action(session['id'], "Viewed reports dashboard.")

    cursor.close()
    conn.close()

    # Pass the data to the frontend
    return render_template('reports.html', 
                           case_status_data=case_status_data, 
                           case_type_data=case_type_data,
                           monthly_data=monthly_data,
                           pending_cases=pending_cases,
                           pending_reports=pending_reports)

@app.route('/')
def index():
    # If the user is already logged in, send them straight to the dashboard
    if 'loggedin' in session:
        return redirect(url_for('dashboard'))
    # Otherwise, show the beautiful animated landing page
    return render_template('index.html')

@app.route('/patient_report/<int:patient_id>')
def patient_report(patient_id):
    # 1. Security Check: Only allow authorized roles
    if not session.get('loggedin'):
        return redirect(url_for('login'))
        
    user_role = session.get('role')
    if user_role not in ['Admin', 'Doctor', 'JMO']:
        flash('You do not have permission to view or generate patient reports.')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 2. Fetch Patient Demographics (Changed 'patients' to 'patient')
        cursor.execute("SELECT * FROM patient WHERE patientid = %s", (patient_id,))
        patient = cursor.fetchone()

        if not patient:
            flash('Patient record not found.')
            return redirect(url_for('dashboard'))

        # 3. Fetch Associated Medico-Legal Case Details (Changed 'medicolegalcases' to 'medicolegalcase')
        cursor.execute("SELECT * FROM medicolegalcase WHERE patientid = %s", (patient_id,))
        cases = cursor.fetchall()

        # 4. Fetch All Evidence Items linked to this patient's cases
        evidence_items = []
        if cases:
            case_ids = [str(c['caseid']) for c in cases]
            format_strings = ','.join(['%s'] * len(case_ids))
            query = f"SELECT * FROM evidence WHERE caseid IN ({format_strings})"
            cursor.execute(query, tuple(case_ids))
            evidence_items = cursor.fetchall()

    except Exception as e:
        print(f"Error generating report: {e}") # This prints the exact error to your terminal!
        flash('An error occurred while compiling the report.')
        return redirect(url_for('dashboard'))
    
    finally:
        cursor.close()
        conn.close()

    log_action(session['id'], f"Generated patient report for patient {patient_id}.")

    # 5. Render the dedicated print/report view
    return render_template('patient_report.html', patient=patient, cases=cases, evidence=evidence_items)

@app.route('/court_report/<int:case_id>')
@login_required
def court_report(case_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        is_admin = session.get('role') == 'Admin' or str(session.get('roleid')) == '1'
        if is_admin:
            cursor.execute("""
                SELECT c.caseid, c.casetype, c.incidentdate, c.policestation, c.casestatus, c.assignedjmo, 
                       s.fullname AS jmoname, s.role AS jmorole
                FROM medicolegalcase c
                LEFT JOIN staff s ON c.assignedjmo = s.staffid
                WHERE c.caseid = %s
            """, (case_id,))
        else:
            cursor.execute("""
                SELECT c.caseid, c.casetype, c.incidentdate, c.policestation, c.casestatus, c.assignedjmo, 
                       s.fullname AS jmoname, s.role AS jmorole
                FROM medicolegalcase c
                LEFT JOIN staff s ON c.assignedjmo = s.staffid
                WHERE c.caseid = %s AND c.assigneddoctor = %s
            """, (case_id, session.get('staff_id') or session.get('userid')))
        case = cursor.fetchone()
        
        if not case:
            flash('Unauthorized access to this case.')
            return redirect(url_for('dashboard'))

        # 2. Fetch the associated Patient/Victim Demographics
        # We need another query to get patient info using the case's patientid
        cursor.execute("""
            SELECT p.* FROM patient p
            JOIN medicolegalcase c ON p.patientid = c.patientid
            WHERE c.caseid = %s
        """, (case_id,))
        patient = cursor.fetchone()

        # 3. Fetch all Evidence linked to this specific case
        cursor.execute("SELECT * FROM evidence WHERE caseid = %s", (case_id,))
        evidence_items = cursor.fetchall()
        
    except Exception as e:
        print(f"Error generating court report: {e}")
        flash('Database error while compiling the court report.')
        return redirect(url_for('view_cases'))
    finally:
        cursor.close()
        conn.close()

    log_action(session['id'], f"Generated court report for case {case_id}.")

    # Import datetime to timestamp the report
    from datetime import datetime
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return render_template('court_report.html', case=case, patient=patient, evidence=evidence_items, current_time=current_time)

if __name__ == '__main__':
    app.run(debug=True)