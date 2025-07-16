from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
import firebase_admin
from firebase_admin import credentials, firestore
import os
from datetime import datetime, timedelta
import csv
from flask import make_response
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Initializing Firebase
cred = credentials.Certificate(os.path.join(os.path.dirname(__file__), 'firebase_key.json'))
firebase_admin.initialize_app(cred)
db = firestore.client()

app.secret_key = 'your_secret_key_here'  # Change this to a secure random value

# Remove in-memory admin_users and related demo code

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password123'

# In-memory admin user store for demo (replace with Firestore for production)
admin_users = {
    'admin': generate_password_hash('password123')
}

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/dashboard')
def index():
    # Get latest 50 attendance records
    attendance_ref = db.collection('attendance').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(50)
    attendance_docs = attendance_ref.stream()
    attendance_records = []
    for doc in attendance_docs:
        data = doc.to_dict()
        # Getting student info
        student_ref = db.collection('students').document(data['student_id'])
        student_doc = student_ref.get()
        student = student_doc.to_dict() if student_doc.exists else {'name': 'Unknown', 'rfid': 'Unknown'}
        attendance_records.append({
            'name': student['name'],
            'rfid': student['rfid'],
            'timestamp': data['timestamp']
        })
    return render_template('index.html', attendance_records=attendance_records)

@app.route('/api/attendance', methods=['POST'])
def log_attendance():
    data = request.get_json()
    rfid = data.get('rfid')
    if not rfid:
        return jsonify({'status': 'error', 'message': 'RFID not provided'}), 400
    # Find student by RFID
    students_ref = db.collection('students').where('rfid', '==', rfid).limit(1)
    students = list(students_ref.stream())
    if not students:
        return jsonify({'status': 'error', 'message': 'Unknown RFID'}), 404
    student = students[0]
    student_id = student.id
    student_data = student.to_dict()
    # Add attendance record
    db.collection('attendance').add({
        'student_id': student_id,
        'timestamp': datetime.utcnow().isoformat()
    })
    return jsonify({'status': 'success', 'student': {'id': student_id, 'name': student_data['name']}}), 200

@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        role = request.form.get('role')
        security_question = request.form.get('security_question')
        security_answer = request.form.get('security_answer')
        username = request.form.get('username')
        password = request.form.get('password')
        if username in admin_users:
            flash('Username already exists', 'danger')
        else:
            admin_users[username] = {
                'password_hash': generate_password_hash(password),
                'full_name': full_name,
                'email': email,
                'phone': phone,
                'role': role,
                'security_question': security_question,
                'security_answer': security_answer
            }
            flash('Account created. Please log in.', 'success')
            return redirect(url_for('admin_login'))
    return render_template('admin_register.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = admin_users.get(username)
        if user and check_password_hash(user['password_hash'], password):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('admin_login.html')

@app.route('/admin/reset', methods=['GET', 'POST'])
def admin_reset():
    if request.method == 'POST':
        username = request.form.get('username')
        new_password = request.form.get('new_password')
        if username in admin_users:
            admin_users[username]['password_hash'] = generate_password_hash(new_password)
            flash('Password reset successful. Please log in.', 'success')
            return redirect(url_for('admin_login'))
        else:
            flash('Username not found', 'danger')
    return render_template('admin_reset.html')

@app.route('/admin/dashboard', methods=['GET'])
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    # Date filter (default: today)
    date_str = request.args.get('date')
    if date_str:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        selected_date = datetime.utcnow().date()

    # Fetch all students
    students = list(db.collection('students').stream())
    student_data = []
    student_id_map = {}
    for student_doc in students:
        student = student_doc.to_dict()
        student_id = student_doc.id
        student['id'] = student_id
        student_data.append(student)
        student_id_map[student_id] = student

    # Fetch all attendance records
    attendance_records = list(db.collection('attendance').stream())
    attendance_by_student = {}
    attendance_by_date = {}
    today_attendance_ids = set()
    for att_doc in attendance_records:
        att = att_doc.to_dict()
        sid = att['student_id']
        ts = att['timestamp']
        try:
            att_date = datetime.fromisoformat(ts).date()
        except Exception:
            att_date = datetime.strptime(ts, '%Y-%m-%d').date()
        # Attendance by student
        attendance_by_student.setdefault(sid, []).append(att_date)
        # Attendance by date
        attendance_by_date.setdefault(att_date, []).append(sid)
        # Today's attendance
        if att_date == selected_date:
            today_attendance_ids.add(sid)

    # Analytics
    total_students = len(student_data)
    total_attendance = len(attendance_records)
    today_attendance_count = len(today_attendance_ids)
    absent_students = [s for s in student_data if s['id'] not in today_attendance_ids]

    # Attendance percentage per student
    attendance_percentages = []
    for s in student_data:
        sid = s['id']
        attended = len(set(attendance_by_student.get(sid, [])))
        percent = (attended / max(1, len(attendance_by_date))) * 100 if attendance_by_date else 0
        attendance_percentages.append({
            'name': s.get('name', 'Unknown'),
            'rfid': s.get('rfid', 'Unknown'),
            'percent': round(percent, 2),
            'attended': attended
        })
    # Most/least attendance
    most_attendance = sorted(attendance_percentages, key=lambda x: -x['attended'])[:5]
    least_attendance = sorted(attendance_percentages, key=lambda x: x['attended'])[:5]

    # Attendance per day (last 7 days)
    last_7_days = [(selected_date - timedelta(days=i)) for i in range(6, -1, -1)]
    attendance_per_day = [
        {
            'date': d.strftime('%Y-%m-%d'),
            'count': len(set(attendance_by_date.get(d, [])))
        } for d in last_7_days
    ]

    # Pie chart data: present vs absent today
    pie_data = {
        'present': today_attendance_count,
        'absent': total_students - today_attendance_count
    }

    return render_template(
        'admin_dashboard.html',
        students=student_data,
        total_students=total_students,
        total_attendance=total_attendance,
        today_attendance_count=today_attendance_count,
        absent_students=absent_students,
        attendance_percentages=attendance_percentages,
        most_attendance=most_attendance,
        least_attendance=least_attendance,
        attendance_per_day=attendance_per_day,
        pie_data=pie_data,
        selected_date=selected_date.strftime('%Y-%m-%d')
    )

@app.route('/admin/export_csv')
def export_csv():
    # Export all attendance records as CSV
    attendance_records = list(db.collection('attendance').stream())
    students = {s.id: s.to_dict() for s in db.collection('students').stream()}
    si = []
    si.append(['Student Name', 'RFID', 'Timestamp'])
    for att_doc in attendance_records:
        att = att_doc.to_dict()
        sid = att['student_id']
        student = students.get(sid, {'name': 'Unknown', 'rfid': 'Unknown'})
        si.append([student.get('name', 'Unknown'), student.get('rfid', 'Unknown'), att['timestamp']])
    output = '\n'.join([','.join(map(str, row)) for row in si])
    response = make_response(output)
    response.headers['Content-Disposition'] = 'attachment; filename=attendance.csv'
    response.headers['Content-type'] = 'text/csv'
    return response

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 