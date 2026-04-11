from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import hashlib
import os
import base64

app = Flask(__name__, static_folder='static')
CORS(app)

DB = 'csa.db'
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sid TEXT UNIQUE NOT NULL,
        email TEXT NOT NULL,
        status TEXT DEFAULT 'Pending',
        applied TEXT NOT NULL,
        report TEXT DEFAULT 'Missing',
        report_date TEXT,
        term TEXT,
        cover_letter TEXT,
        resume TEXT,
        work_term_grade TEXT DEFAULT 'Pending'
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS student_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sid TEXT UNIQUE NOT NULL,
        email TEXT NOT NULL,
        password TEXT NOT NULL,
        name TEXT NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS supervisor_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        company TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        student_sid TEXT NOT NULL,
        password TEXT NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_sid TEXT NOT NULL,
        student_name TEXT,
        supervisor_name TEXT,
        company TEXT,
        term TEXT,
        status TEXT DEFAULT 'Submitted',
        comments TEXT,
        ratings TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS rejections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sid TEXT NOT NULL,
        company TEXT NOT NULL,
        reason TEXT NOT NULL,
        date TEXT NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS placements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sid TEXT NOT NULL,
        student_name TEXT,
        company TEXT NOT NULL,
        position TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        status TEXT DEFAULT 'Pending Approval',
        submitted_date TEXT NOT NULL
    )''')

    try:
        from datetime import date
        samples = [
            ('Alice Chen', '501100001', 'alice@torontomu.ca', 'Provisionally Accepted', '2026-01-15', 'Submitted', '2026-03-10', 'Winter 2026 (Jan – Apr)', None, None, 'Pending'),
            ('Bob Tremblay', '501100002', 'bob@torontomu.ca', 'Pending', '2026-01-18', 'Missing', None, None, None, None, 'Pending'),
            ('Sara Patel', '501100003', 'sara@torontomu.ca', 'Finally Accepted', '2026-01-10', 'Submitted', '2026-02-05', 'Fall 2025 (Sep – Dec)', None, None, 'Pass'),
            ('James Wu', '501100004', 'james@torontomu.ca', 'Provisionally Rejected', '2026-01-20', 'Missing', None, None, None, None, 'Pending'),
            ('Maria Santos', '501100005', 'maria@torontomu.ca', 'Pending', '2026-01-22', 'Missing', None, None, None, None, 'Pending'),
        ]
        for s in samples:
            c.execute('INSERT OR IGNORE INTO applications (name,sid,email,status,applied,report,report_date,term,cover_letter,resume,work_term_grade) VALUES (?,?,?,?,?,?,?,?,?,?,?)', s)

        hashed = hash_pw('pass123')
        c.execute('INSERT OR IGNORE INTO student_accounts (sid,email,password,name) VALUES (?,?,?,?)',
                  ('501100001','alice@torontomu.ca', hashed, 'Alice Chen'))
        c.execute('INSERT OR IGNORE INTO student_accounts (sid,email,password,name) VALUES (?,?,?,?)',
                  ('501100003','sara@torontomu.ca', hashed, 'Sara Patel'))

        c.execute('INSERT OR IGNORE INTO evaluations (student_sid,student_name,supervisor_name,company,term,status,comments,ratings) VALUES (?,?,?,?,?,?,?,?)',
                  ('501100001','Alice Chen','Dr. Raj Kumar','TechCorp Inc.','Winter 2026 (Jan – Apr)','Submitted','Great communication skills.',
                   "{'Technical Skills': 4, 'Communication': 5, 'Teamwork': 4, 'Initiative': 3, 'Professionalism': 5, 'Overall Performance': 4}"))
        c.execute('INSERT OR IGNORE INTO evaluations (student_sid,student_name,supervisor_name,company,term,status,comments,ratings) VALUES (?,?,?,?,?,?,?,?)',
                  ('501100003','Sara Patel','Jane Miller','Innovate Co.','Fall 2025 (Sep – Dec)','Submitted','Excellent work overall.',
                   "{'Technical Skills': 5, 'Communication': 4, 'Teamwork': 5, 'Initiative': 5, 'Professionalism': 4, 'Overall Performance': 5}"))

        c.execute('INSERT OR IGNORE INTO placements (sid,student_name,company,position,start_date,end_date,status,submitted_date) VALUES (?,?,?,?,?,?,?,?)',
                  ('501100001','Alice Chen','TechCorp Inc.','Software Developer Intern','2026-01-06','2026-04-24','Approved','2025-12-01'))
        c.execute('INSERT OR IGNORE INTO placements (sid,student_name,company,position,start_date,end_date,status,submitted_date) VALUES (?,?,?,?,?,?,?,?)',
                  ('501100003','Sara Patel','Innovate Co.','Data Analyst Intern','2025-09-02','2025-12-19','Approved','2025-08-15'))
    except Exception as e:
        print('Seed skipped:', e)

    conn.commit()
    conn.close()

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

# ── APPLICATIONS ──────────────────────────────────
@app.route('/api/applications', methods=['GET'])
def get_applications():
    status = request.args.get('status', '')
    conn = get_db()
    rows = conn.execute('SELECT * FROM applications WHERE status=?', (status,)).fetchall() if status else conn.execute('SELECT * FROM applications').fetchall()
    conn.close()
    # Don't send file data in list view
    result = []
    for r in rows:
        d = dict(r)
        d.pop('cover_letter', None)
        d.pop('resume', None)
        result.append(d)
    return jsonify(result)

@app.route('/api/applications', methods=['POST'])
def submit_application():
    data = request.json
    name = data.get('name','').strip()
    sid = data.get('sid','').strip()
    email = data.get('email','').strip()
    cover_letter = data.get('coverLetter', None)  # base64 or None
    resume = data.get('resume', None)

    if not name or not sid or not email:
        return jsonify({'error': 'All fields are required.'}), 400
    if not sid.isdigit() or len(sid) != 9:
        return jsonify({'error': 'Student ID must be exactly 9 digits.'}), 400
    if '@' not in email:
        return jsonify({'error': 'Please enter a valid email address.'}), 400

    from datetime import date
    try:
        conn = get_db()
        conn.execute('INSERT INTO applications (name,sid,email,applied,cover_letter,resume) VALUES (?,?,?,?,?,?)',
                     (name, sid, email, date.today().isoformat(), cover_letter, resume))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'An application with this Student ID already exists.'}), 400

@app.route('/api/applications/<int:app_id>/status', methods=['PUT'])
def update_status(app_id):
    data = request.json
    status = data.get('status')
    allowed = ['Pending','Provisionally Accepted','Provisionally Rejected','Finally Accepted','Finally Rejected']
    if status not in allowed:
        return jsonify({'error': 'Invalid status.'}), 400
    conn = get_db()
    conn.execute('UPDATE applications SET status=? WHERE id=?', (status, app_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/applications/<int:app_id>/grade', methods=['PUT'])
def grade_student(app_id):
    data = request.json
    grade = data.get('grade')
    if grade not in ('Pass', 'Fail'):
        return jsonify({'error': 'Grade must be Pass or Fail.'}), 400
    conn = get_db()
    # Check report and evaluation are both submitted
    app_row = conn.execute('SELECT * FROM applications WHERE id=?', (app_id,)).fetchone()
    if not app_row:
        conn.close()
        return jsonify({'error': 'Application not found.'}), 404
    if app_row['report'] != 'Submitted':
        conn.close()
        return jsonify({'error': 'Cannot grade: work term report not yet submitted.'}), 400
    ev = conn.execute('SELECT id FROM evaluations WHERE student_sid=?', (app_row['sid'],)).fetchone()
    if not ev:
        conn.close()
        return jsonify({'error': 'Cannot grade: supervisor evaluation not yet submitted.'}), 400
    conn.execute('UPDATE applications SET work_term_grade=? WHERE id=?', (grade, app_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/applications/<int:app_id>/documents', methods=['GET'])
def get_documents(app_id):
    conn = get_db()
    row = conn.execute('SELECT cover_letter, resume, name, sid FROM applications WHERE id=?', (app_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'name': row['name'], 'sid': row['sid'],
        'cover_letter': row['cover_letter'],
        'resume': row['resume']
    })

@app.route('/api/applications/<string:sid>/report', methods=['PUT'])
def submit_report(sid):
    data = request.json
    term = data.get('term','')
    from datetime import date
    conn = get_db()
    app_row = conn.execute('SELECT status FROM applications WHERE sid=?', (sid,)).fetchone()
    if not app_row or app_row['status'] != 'Finally Accepted':
        conn.close()
        return jsonify({'error': 'Only finally accepted students can submit reports.'}), 403
    conn.execute('UPDATE applications SET report=?, report_date=?, term=? WHERE sid=?',
                 ('Submitted', date.today().isoformat(), term, sid))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ── STUDENT AUTH ──────────────────────────────────
@app.route('/api/student/register', methods=['POST'])
def student_register():
    data = request.json
    sid = data.get('sid','').strip()
    email = data.get('email','').strip()
    pw = data.get('password','')
    pw2 = data.get('password2','')
    if not sid or not email or not pw or not pw2:
        return jsonify({'error': 'All fields are required.'}), 400
    if pw != pw2:
        return jsonify({'error': 'Passwords do not match.'}), 400
    if not sid.isdigit() or len(sid) != 9:
        return jsonify({'error': 'Student ID must be 9 digits.'}), 400
    conn = get_db()
    app_row = conn.execute('SELECT * FROM applications WHERE sid=?', (sid,)).fetchone()
    if not app_row:
        conn.close()
        return jsonify({'error': 'No application found with this Student ID.'}), 400
    if app_row['status'] not in ('Provisionally Accepted','Finally Accepted'):
        conn.close()
        return jsonify({'error': 'Your application has not been provisionally accepted yet.'}), 400
    try:
        conn.execute('INSERT INTO student_accounts (sid,email,password,name) VALUES (?,?,?,?)',
                     (sid, email, hash_pw(pw), app_row['name']))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'An account for this Student ID already exists.'}), 400

@app.route('/api/student/login', methods=['POST'])
def student_login():
    data = request.json
    id_ = data.get('id','').strip()
    pw = data.get('password','')
    conn = get_db()
    row = conn.execute('SELECT * FROM student_accounts WHERE (sid=? OR email=?) AND password=?',
                       (id_, id_, hash_pw(pw))).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Invalid credentials.'}), 401
    return jsonify({'success': True, 'sid': row['sid'], 'name': row['name']})

@app.route('/api/student/<string:sid>', methods=['GET'])
def get_student_info(sid):
    conn = get_db()
    app_row = conn.execute('SELECT id,name,sid,email,status,applied,report,report_date,term,work_term_grade FROM applications WHERE sid=?', (sid,)).fetchone()
    conn.close()
    if not app_row:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(app_row))

# ── PLACEMENTS ────────────────────────────────────
@app.route('/api/placements', methods=['GET'])
def get_placements():
    conn = get_db()
    rows = conn.execute('SELECT * FROM placements').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/placements/student/<string:sid>', methods=['GET'])
def get_student_placement(sid):
    conn = get_db()
    row = conn.execute('SELECT * FROM placements WHERE sid=?', (sid,)).fetchone()
    conn.close()
    return jsonify(dict(row) if row else {})

@app.route('/api/placements', methods=['POST'])
def submit_placement():
    data = request.json
    sid = data.get('sid','').strip()
    company = data.get('company','').strip()
    position = data.get('position','').strip()
    start_date = data.get('startDate','').strip()
    end_date = data.get('endDate','').strip()
    if not sid or not company or not position or not start_date or not end_date:
        return jsonify({'error': 'All fields are required.'}), 400
    from datetime import date
    conn = get_db()
    app_row = conn.execute('SELECT name, status FROM applications WHERE sid=?', (sid,)).fetchone()
    if not app_row or app_row['status'] not in ('Provisionally Accepted','Finally Accepted'):
        conn.close()
        return jsonify({'error': 'Only accepted students can submit placements.'}), 403
    existing = conn.execute('SELECT id FROM placements WHERE sid=?', (sid,)).fetchone()
    if existing:
        conn.execute('UPDATE placements SET company=?,position=?,start_date=?,end_date=?,status=?,submitted_date=? WHERE sid=?',
                     (company, position, start_date, end_date, 'Pending Approval', date.today().isoformat(), sid))
    else:
        conn.execute('INSERT INTO placements (sid,student_name,company,position,start_date,end_date,status,submitted_date) VALUES (?,?,?,?,?,?,?,?)',
                     (sid, app_row['name'], company, position, start_date, end_date, 'Pending Approval', date.today().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/placements/<int:placement_id>/status', methods=['PUT'])
def update_placement_status(placement_id):
    data = request.json
    status = data.get('status')
    reason = data.get('reason','')
    if status not in ('Approved', 'Rejected'):
        return jsonify({'error': 'Invalid status.'}), 400
    from datetime import date
    conn = get_db()
    placement = conn.execute('SELECT * FROM placements WHERE id=?', (placement_id,)).fetchone()
    if not placement:
        conn.close()
        return jsonify({'error': 'Placement not found.'}), 404
    conn.execute('UPDATE placements SET status=? WHERE id=?', (status, placement_id))
    if status == 'Rejected':
        conn.execute('INSERT INTO rejections (sid,company,reason,date) VALUES (?,?,?,?)',
                     (placement['sid'], placement['company'], reason or 'Placement rejected by coordinator', date.today().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ── SUPERVISOR AUTH ───────────────────────────────
@app.route('/api/supervisor/register', methods=['POST'])
def supervisor_register():
    data = request.json
    name = data.get('name','').strip()
    company = data.get('company','').strip()
    email = data.get('email','').strip()
    student_sid = data.get('studentSid','').strip()
    pw = data.get('password','')
    if not name or not company or not email or not student_sid or not pw:
        return jsonify({'error': 'All fields are required.'}), 400
    try:
        conn = get_db()
        conn.execute('INSERT INTO supervisor_accounts (name,company,email,student_sid,password) VALUES (?,?,?,?,?)',
                     (name, company, email, student_sid, hash_pw(pw)))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'An account with this email already exists.'}), 400

@app.route('/api/supervisor/login', methods=['POST'])
def supervisor_login():
    data = request.json
    email = data.get('email','').strip()
    pw = data.get('password','')
    conn = get_db()
    row = conn.execute('SELECT * FROM supervisor_accounts WHERE email=? AND password=?',
                       (email, hash_pw(pw))).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Invalid credentials.'}), 401
    return jsonify({'success': True, 'name': row['name'], 'company': row['company'], 'studentSid': row['student_sid']})

# ── EVALUATIONS ───────────────────────────────────
@app.route('/api/evaluations', methods=['GET'])
def get_evaluations():
    conn = get_db()
    rows = conn.execute('SELECT * FROM evaluations').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/evaluations/student/<string:sid>', methods=['GET'])
def get_evaluation_by_student(sid):
    conn = get_db()
    row = conn.execute('SELECT * FROM evaluations WHERE student_sid=? ORDER BY id DESC LIMIT 1', (sid,)).fetchone()
    conn.close()
    return jsonify(dict(row) if row else {})

@app.route('/api/evaluations', methods=['POST'])
def submit_evaluation():
    data = request.json
    conn = get_db()
    app_row = conn.execute('SELECT name FROM applications WHERE sid=?', (data.get('studentSid'),)).fetchone()
    student_name = app_row['name'] if app_row else data.get('studentSid')
    conn.execute('INSERT INTO evaluations (student_sid,student_name,supervisor_name,company,term,status,comments,ratings) VALUES (?,?,?,?,?,?,?,?)',
                 (data.get('studentSid'), student_name, data.get('supervisorName'), data.get('company'),
                  data.get('term'), 'Submitted', data.get('comments',''), str(data.get('ratings',{}))))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ── REJECTIONS ────────────────────────────────────
@app.route('/api/rejections', methods=['GET'])
def get_rejections():
    conn = get_db()
    rows = conn.execute('SELECT * FROM rejections').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/rejections', methods=['POST'])
def add_rejection():
    data = request.json
    sid = data.get('sid','').strip()
    company = data.get('company','').strip()
    reason = data.get('reason','').strip()
    if not sid or not company or not reason:
        return jsonify({'error': 'All fields are required.'}), 400
    from datetime import date
    conn = get_db()
    conn.execute('INSERT INTO rejections (sid,company,reason,date) VALUES (?,?,?,?)',
                 (sid, company, reason, date.today().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

if __name__ == '__main__':
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
