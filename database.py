import sqlite3
import json
from datetime import datetime
import config

def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with all required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Teachers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            roll_number TEXT NOT NULL,
            department TEXT NOT NULL,
            phone_number TEXT,
            email TEXT,
            parent_name TEXT NOT NULL,
            parent_email TEXT NOT NULL,
            parent_phone TEXT,
            face_images_path TEXT,
            registered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Subjects table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_code TEXT UNIQUE NOT NULL,
            subject_name TEXT NOT NULL,
            department TEXT NOT NULL,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES teachers (id)
        )
    ''')
    
    # Attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            date DATE NOT NULL,
            time TIME NOT NULL,
            status TEXT NOT NULL,
            marked_by INTEGER,
            confidence_score REAL,
            attendance_method TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students (id),
            FOREIGN KEY (subject_id) REFERENCES subjects (id),
            FOREIGN KEY (marked_by) REFERENCES teachers (id),
            UNIQUE(student_id, subject_id, date)
        )
    ''')
    
    # Face embeddings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS face_embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            embedding_data TEXT NOT NULL,
            image_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    ''')
    
    # Absence notifications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS absence_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            date DATE NOT NULL,
            parent_email TEXT NOT NULL,
            notification_sent INTEGER DEFAULT 0,
            sent_at TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students (id),
            FOREIGN KEY (subject_id) REFERENCES subjects (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

# ============== Teacher Operations ==============

def add_teacher(username, email, password_hash, full_name):
    """Add a new teacher"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO teachers (username, email, password_hash, full_name)
            VALUES (?, ?, ?, ?)
        ''', (username, email, password_hash, full_name))
        conn.commit()
        teacher_id = cursor.lastrowid
        conn.close()
        return True, teacher_id
    except sqlite3.IntegrityError:
        return False, "Username or email already exists"
    except Exception as e:
        return False, str(e)

def get_teacher_by_username(username):
    """Get teacher by username"""
    conn = get_db_connection()
    teacher = conn.execute('SELECT * FROM teachers WHERE username = ?', (username,)).fetchone()
    conn.close()
    return teacher

def get_teacher_by_id(teacher_id):
    """Get teacher by ID"""
    conn = get_db_connection()
    teacher = conn.execute('SELECT * FROM teachers WHERE id = ?', (teacher_id,)).fetchone()
    conn.close()
    return teacher

# ============== Student Operations ==============

def add_student(student_id, full_name, roll_number, department, phone_number, 
                email, parent_name, parent_email, parent_phone, face_images_path):
    """Add a new student"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO students (student_id, full_name, roll_number, department,
                                phone_number, email, parent_name, parent_email,
                                parent_phone, face_images_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (student_id, full_name, roll_number, department, phone_number,
              email, parent_name, parent_email, parent_phone, json.dumps(face_images_path)))
        conn.commit()
        db_student_id = cursor.lastrowid
        conn.close()
        return True, db_student_id
    except sqlite3.IntegrityError:
        return False, "Student ID already exists"
    except Exception as e:
        return False, str(e)

def get_student_by_id(student_id):
    """Get student by database ID"""
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    conn.close()
    return student

def get_student_by_student_id(student_id):
    """Get student by student ID"""
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE student_id = ?', (student_id,)).fetchone()
    conn.close()
    return student

def get_all_students(active_only=True):
    """Get all students"""
    conn = get_db_connection()
    if active_only:
        students = conn.execute('SELECT * FROM students WHERE is_active = 1 ORDER BY full_name').fetchall()
    else:
        students = conn.execute('SELECT * FROM students ORDER BY full_name').fetchall()
    conn.close()
    return students

def update_student(student_id, full_name, roll_number, department, phone_number,
                  email, parent_name, parent_email, parent_phone):
    """Update student information"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE students 
            SET full_name = ?, roll_number = ?, department = ?,
                phone_number = ?, email = ?, parent_name = ?,
                parent_email = ?, parent_phone = ?
            WHERE id = ?
        ''', (full_name, roll_number, department, phone_number, email,
              parent_name, parent_email, parent_phone, student_id))
        conn.commit()
        conn.close()
        return True, "Student updated successfully"
    except Exception as e:
        return False, str(e)

def delete_student(student_id):
    """Soft delete a student (set is_active to 0)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE students SET is_active = 0 WHERE id = ?', (student_id,))
        conn.commit()
        conn.close()
        return True, "Student deleted successfully"
    except Exception as e:
        return False, str(e)

def get_students_count():
    """Get total number of active students"""
    conn = get_db_connection()
    count = conn.execute('SELECT COUNT(*) FROM students WHERE is_active = 1').fetchone()[0]
    conn.close()
    return count

# ============== Subject Operations ==============

def add_subject(subject_code, subject_name, department, created_by):
    """Add a new subject"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO subjects (subject_code, subject_name, department, created_by)
            VALUES (?, ?, ?, ?)
        ''', (subject_code, subject_name, department, created_by))
        conn.commit()
        subject_id = cursor.lastrowid
        conn.close()
        return True, subject_id
    except sqlite3.IntegrityError:
        return False, "Subject code already exists"
    except Exception as e:
        return False, str(e)

def get_all_subjects():
    """Get all subjects"""
    conn = get_db_connection()
    subjects = conn.execute('SELECT * FROM subjects ORDER BY subject_name').fetchall()
    conn.close()
    return subjects

def get_subject_by_id(subject_id):
    """Get subject by ID"""
    conn = get_db_connection()
    subject = conn.execute('SELECT * FROM subjects WHERE id = ?', (subject_id,)).fetchone()
    conn.close()
    return subject

def delete_subject(subject_id):
    """Delete a subject"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM subjects WHERE id = ?', (subject_id,))
        conn.commit()
        conn.close()
        return True, "Subject deleted successfully"
    except Exception as e:
        return False, str(e)

def get_subjects_count():
    """Get total number of subjects"""
    conn = get_db_connection()
    count = conn.execute('SELECT COUNT(*) FROM subjects').fetchone()[0]
    conn.close()
    return count

# ============== Attendance Operations ==============

def mark_attendance(student_id, subject_id, date, time, status, marked_by,
                   confidence_score=None, attendance_method='webcam'):
    """Mark attendance for a student"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO attendance (student_id, subject_id, date, time, status,
                                  marked_by, confidence_score, attendance_method)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (student_id, subject_id, date, time, status, marked_by,
              confidence_score, attendance_method))
        conn.commit()
        attendance_id = cursor.lastrowid
        conn.close()
        return True, attendance_id
    except sqlite3.IntegrityError:
        return False, "Attendance already marked for this student in this subject today"
    except Exception as e:
        return False, str(e)

def check_duplicate_attendance(student_id, subject_id, date):
    """Check if attendance already marked"""
    conn = get_db_connection()
    result = conn.execute('''
        SELECT id FROM attendance 
        WHERE student_id = ? AND subject_id = ? AND date = ?
    ''', (student_id, subject_id, date)).fetchone()
    conn.close()
    return result is not None

def get_attendance_records(subject_id=None, date=None, student_id=None, department=None):
    """Get attendance records with filters"""
    conn = get_db_connection()
    
    query = '''
        SELECT a.*, s.full_name, s.roll_number, s.department, s.student_id as stu_id,
               sub.subject_name, sub.subject_code, t.full_name as teacher_name
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN subjects sub ON a.subject_id = sub.id
        JOIN teachers t ON a.marked_by = t.id
        WHERE 1=1
    '''
    params = []
    
    if subject_id:
        query += ' AND a.subject_id = ?'
        params.append(subject_id)
    
    if date:
        query += ' AND a.date = ?'
        params.append(date)
    
    if student_id:
        query += ' AND a.student_id = ?'
        params.append(student_id)
    
    if department:
        query += ' AND s.department = ?'
        params.append(department)
    
    query += ' ORDER BY a.date DESC, a.time DESC'
    
    records = conn.execute(query, params).fetchall()
    conn.close()
    return records

def get_today_attendance_count(subject_id=None):
    """Get today's attendance count"""
    today = datetime.now().strftime('%Y-%m-%d')
    conn = get_db_connection()
    
    if subject_id:
        count = conn.execute('''
            SELECT COUNT(*) FROM attendance 
            WHERE date = ? AND subject_id = ? AND status = 'Present'
        ''', (today, subject_id)).fetchone()[0]
    else:
        count = conn.execute('''
            SELECT COUNT(DISTINCT student_id) FROM attendance 
            WHERE date = ? AND status = 'Present'
        ''', (today,)).fetchone()[0]
    
    conn.close()
    return count

def get_absent_students(subject_id, date):
    """Get list of absent students for a subject on a date"""
    conn = get_db_connection()
    
    # Get all active students
    all_students = conn.execute('SELECT * FROM students WHERE is_active = 1').fetchall()
    
    # Get students who marked attendance
    present_students = conn.execute('''
        SELECT student_id FROM attendance 
        WHERE subject_id = ? AND date = ?
    ''', (subject_id, date)).fetchall()
    
    present_ids = [row['student_id'] for row in present_students]
    
    # Find absent students
    absent_students = [s for s in all_students if s['id'] not in present_ids]
    
    conn.close()
    return absent_students

# ============== Face Embeddings Operations ==============

def save_face_embedding(student_id, embedding_data, image_path):
    """Save face embedding for a student"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO face_embeddings (student_id, embedding_data, image_path)
            VALUES (?, ?, ?)
        ''', (student_id, json.dumps(embedding_data), image_path))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving embedding: {str(e)}")
        return False

def get_all_face_embeddings():
    """Get all face embeddings"""
    conn = get_db_connection()
    embeddings = conn.execute('''
        SELECT fe.*, s.student_id, s.full_name 
        FROM face_embeddings fe
        JOIN students s ON fe.student_id = s.id
        WHERE s.is_active = 1
    ''').fetchall()
    conn.close()
    return embeddings

def delete_student_embeddings(student_id):
    """Delete all embeddings for a student"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM face_embeddings WHERE student_id = ?', (student_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting embeddings: {str(e)}")
        return False

# ============== Absence Notifications Operations ==============

def log_absence_notification(student_id, subject_id, date, parent_email, sent=False):
    """Log absence notification"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO absence_notifications (student_id, subject_id, date, 
                                              parent_email, notification_sent, sent_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (student_id, subject_id, date, parent_email, 1 if sent else 0,
              datetime.now() if sent else None))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error logging notification: {str(e)}")
        return False

def get_notification_logs(date=None):
    """Get notification logs"""
    conn = get_db_connection()
    
    query = '''
        SELECT an.*, s.full_name, s.student_id, sub.subject_name
        FROM absence_notifications an
        JOIN students s ON an.student_id = s.id
        JOIN subjects sub ON an.subject_id = sub.id
        WHERE 1=1
    '''
    params = []
    
    if date:
        query += ' AND an.date = ?'
        params.append(date)
    
    query += ' ORDER BY an.sent_at DESC'
    
    logs = conn.execute(query, params).fetchall()
    conn.close()
    return logs
