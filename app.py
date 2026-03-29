from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
import os
import json
import cv2
import base64
import numpy as np
from datetime import datetime, timedelta
import config
import database
import utils
from face_recognition import face_recognition_system
import email_service

app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config.MAX_FILE_SIZE
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=config.PERMANENT_SESSION_LIFETIME)
app.config['STUDENT_FACES_FOLDER'] = config.STUDENT_FACES_FOLDER

# Initialize database
database.init_db()

# ============== Authentication Routes ==============

@app.route('/')
def index():
    """Home page - redirect to dashboard if logged in, else to login"""
    if 'teacher_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Teacher login page"""
    if 'teacher_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember')
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('login.html', now=datetime.now())
        
        teacher = database.get_teacher_by_username(username)
        
        if teacher and utils.verify_password(password, teacher['password_hash']):
            session['teacher_id'] = teacher['id']
            session['teacher_name'] = teacher['full_name']
            session['teacher_email'] = teacher['email']
            
            if remember:
                session.permanent = True
            
            flash(f'Welcome back, {teacher["full_name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html', now=datetime.now())

@app.route('/logout')
def logout():
    """Logout teacher"""
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/register_teacher', methods=['GET', 'POST'])
def register_teacher():
    """Register new teacher (for initial setup)"""
    # Check if any teacher exists
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        
        if not all([username, email, password, confirm_password, full_name]):
            flash('All fields are required', 'error')
            return render_template('register_teacher.html', now=datetime.now())
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register_teacher.html', now=datetime.now())
        
        password_hash = utils.hash_password(password)
        success, result = database.add_teacher(username, email, password_hash, full_name)
        
        if success:
            flash('Teacher registered successfully! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash(f'Registration failed: {result}', 'error')
    
    return render_template('register_teacher.html', now=datetime.now())

# ============== Dashboard ==============

@app.route('/dashboard')
@utils.login_required
def dashboard():
    """Main dashboard"""
    # Get statistics
    total_students = database.get_students_count()
    total_subjects = database.get_subjects_count()
    today_attendance = database.get_today_attendance_count()
    
    # Get today's date
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Get recent attendance records (last 10)
    recent_records = database.get_attendance_records()[:10]
    
    # Check if model is trained
    model_trained = face_recognition_system.is_model_trained()
    
    return render_template('dashboard.html',
                         total_students=total_students,
                         total_subjects=total_subjects,
                         today_attendance=today_attendance,
                         recent_records=recent_records,
                         model_trained=model_trained,
                         today=today,
                         now=datetime.now())

# ============== Student Registration ==============

@app.route('/register_student', methods=['GET', 'POST'])
@utils.login_required
def register_student():
    """Register new student with face capture"""
    if request.method == 'POST':
        # Get form data
        full_name = request.form.get('full_name')
        roll_number = request.form.get('roll_number')
        department = request.form.get('department')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        parent_name = request.form.get('parent_name')
        parent_email = request.form.get('parent_email')
        parent_phone = request.form.get('parent_phone')
        
        # Get captured images data (base64)
        images_data = request.form.get('images_data')
        
        if not all([full_name, roll_number, department, parent_name, parent_email]):
            flash('Please fill all required fields', 'error')
            return redirect(url_for('register_student'))
        
        if not images_data:
            flash('Please capture at least one face image', 'error')
            return redirect(url_for('register_student'))
        
        try:
            # Parse images data
            images_list = json.loads(images_data)
            
            if len(images_list) < 5:
                flash('Please capture at least 5 face images', 'error')
                return redirect(url_for('register_student'))
            
            # Generate student ID
            student_id = utils.generate_student_id()
            
            # Create student directory
            student_dir = utils.create_student_directory(student_id)
            
            # Save images - only the face regions
            image_paths = []
            for i, img_data in enumerate(images_list):
                # Remove data URL prefix
                img_data = img_data.split(',')[1] if ',' in img_data else img_data
                
                # Decode base64
                img_bytes = base64.b64decode(img_data)
                img_array = np.frombuffer(img_bytes, dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                
                # Detect face in the image
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                
                if len(faces) > 0:
                    # Get the largest face
                    largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
                    x, y, w, h = largest_face
                    
                    # Add some margin around the face (20%)
                    margin_x = int(w * 0.2)
                    margin_y = int(h * 0.2)
                    
                    # Calculate new coordinates with margins
                    x1 = max(0, x - margin_x)
                    y1 = max(0, y - margin_y)
                    x2 = min(img.shape[1], x + w + margin_x)
                    y2 = min(img.shape[0], y + h + margin_y)
                    
                    # Extract face region with margin
                    face_img = img[y1:y2, x1:x2]
                    
                    # Save only the face image
                    img_filename = f"{i+1}.jpg"
                    img_path = os.path.join(student_dir, img_filename)
                    cv2.imwrite(img_path, face_img)
                    image_paths.append(img_path)
                else:
                    # If no face detected, save the original image
                    img_filename = f"{i+1}.jpg"
                    img_path = os.path.join(student_dir, img_filename)
                    cv2.imwrite(img_path, img)
                    image_paths.append(img_path)
            
            # Add student to database
            success, result = database.add_student(
                student_id, full_name, roll_number, department,
                phone_number, email, parent_name, parent_email,
                parent_phone, image_paths
            )
            
            if success:
                flash(f'Student registered successfully! Student ID: {student_id}', 'success')
                flash('Please train the model to include this student in face recognition', 'info')
                return redirect(url_for('student_management'))
            else:
                flash(f'Registration failed: {result}', 'error')
                
        except Exception as e:
            flash(f'Error during registration: {str(e)}', 'error')
    
    return render_template('register_student.html', now=datetime.now())

# ============== Student Management ==============

@app.route('/student_management')
@utils.login_required
def student_management():
    """View and manage all students"""
    students = [dict(student) for student in database.get_all_students()]
    for student in students:
        student_id = student['student_id']
        student_image_folder = os.path.join(app.config['STUDENT_FACES_FOLDER'], student_id)
        
        # Get all image files for the student
        image_files = [f for f in os.listdir(student_image_folder) if os.path.isfile(os.path.join(student_image_folder, f))]
        
        # Convert absolute paths to relative URLs for web display
        student['images'] = [url_for('static', filename=f'student_faces/{student_id}/{img_file}') for img_file in image_files]
        student['image_count'] = len(student['images'])
    
    return render_template('student_management.html', students=students, now=datetime.now())

@app.route('/delete_student/<int:student_id>', methods=['POST'])
@utils.login_required
def delete_student(student_id):
    """Delete a student"""
    success, message = database.delete_student(student_id)
    
    if success:
        flash('Student deleted successfully', 'success')
    else:
        flash(f'Delete failed: {message}', 'error')
    
    return redirect(url_for('student_management'))

# ============== Subject Management ==============

@app.route('/subjects', methods=['GET', 'POST'])
@utils.login_required
def subjects():
    """Manage subjects"""
    if request.method == 'POST':
        subject_code = request.form.get('subject_code')
        subject_name = request.form.get('subject_name')
        department = request.form.get('department')
        
        if not all([subject_code, subject_name, department]):
            flash('All fields are required', 'error')
        else:
            success, result = database.add_subject(
                subject_code, subject_name, department, session['teacher_id']
            )
            
            if success:
                flash('Subject added successfully', 'success')
            else:
                flash(f'Failed to add subject: {result}', 'error')
        
        return redirect(url_for('subjects'))
    
    all_subjects = database.get_all_subjects()
    return render_template('subject_management.html', subjects=all_subjects, now=datetime.now())

@app.route('/delete_subject/<int:subject_id>', methods=['POST'])
@utils.login_required
def delete_subject(subject_id):
    """Delete a subject"""
    success, message = database.delete_subject(subject_id)
    
    if success:
        flash('Subject deleted successfully', 'success')
    else:
        flash(f'Delete failed: {message}', 'error')
    
    return redirect(url_for('subjects'))

# ============== Take Attendance ==============

@app.route('/take_attendance', methods=['GET', 'POST'])
@utils.login_required
def take_attendance():
    """Take attendance using image/video/webcam"""
    subjects = database.get_all_subjects()
    now = datetime.now()
    
    if request.method == 'POST':
        subject_id = request.form.get('subject_id')
        attendance_date = request.form.get('attendance_date')
        method = request.form.get('method')
        
        if not subject_id or not attendance_date:
            flash('Please select subject and date', 'error')
            return redirect(url_for('take_attendance'))
        
        # Get subject info
        subject = database.get_subject_by_id(subject_id)
        
        recognized_students = []
        
        try:
            if method == 'image':
                # Handle image upload
                file = request.files.get('attendance_image')
                
                if file and utils.allowed_file(file.filename, 'image'):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(config.TEMP_IMAGES_FOLDER, filename)
                    file.save(filepath)
                    
                    # Recognize faces
                    recognized_students = face_recognition_system.recognize_faces_in_image(filepath)
                    
                    # Clean up
                    os.remove(filepath)
                else:
                    flash('Invalid image file', 'error')
                    return redirect(url_for('take_attendance'))
            
            elif method == 'video':
                # Handle video upload
                file = request.files.get('attendance_video')
                
                if file and utils.allowed_file(file.filename, 'video'):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(config.TEMP_VIDEOS_FOLDER, filename)
                    
                    try:
                        # Make sure the directories exist
                        os.makedirs(config.TEMP_VIDEOS_FOLDER, exist_ok=True)
                        os.makedirs(config.TEMP_IMAGES_FOLDER, exist_ok=True)
                        
                        # Save the uploaded file
                        file.save(filepath)
                        
                        # Process video frames directly
                        cap = cv2.VideoCapture(filepath)
                        frame_count = 0
                        frame_skip = 10  # Process every 10th frame
                        recognized_students_dict = {}
                        
                        # Face detector
                        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                        
                        while cap.isOpened():
                            ret, frame = cap.read()
                            if not ret:
                                break
                                
                            # Process every nth frame
                            if frame_count % frame_skip == 0:
                                # Detect faces in the frame
                                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                                faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                                
                                # Process each detected face
                                for (x, y, w, h) in faces:
                                    # Add margin around the face
                                    margin_x = int(w * 0.2)
                                    margin_y = int(h * 0.2)
                                    
                                    # Calculate new coordinates with margins
                                    x1 = max(0, x - margin_x)
                                    y1 = max(0, y - margin_y)
                                    x2 = min(frame.shape[1], x + w + margin_x)
                                    y2 = min(frame.shape[0], y + h + margin_y)
                                    
                                    # Extract face region with margin
                                    face_img = frame[y1:y2, x1:x2]
                                    
                                    # Save the face image temporarily
                                    temp_face_path = os.path.join(config.TEMP_IMAGES_FOLDER, f'video_face_{frame_count}_{x}_{y}.jpg')
                                    cv2.imwrite(temp_face_path, face_img)
                                    
                                    # Recognize the face
                                    student_id, confidence, message = face_recognition_system.recognize_face(temp_face_path)
                                    
                                    # If recognized, add to the dictionary with highest confidence
                                    if student_id:
                                        if student_id in recognized_students_dict:
                                            if confidence > recognized_students_dict[student_id]:
                                                recognized_students_dict[student_id] = confidence
                                        else:
                                            recognized_students_dict[student_id] = confidence
                                    
                                    # Clean up
                                    try:
                                        os.remove(temp_face_path)
                                    except:
                                        pass
                            
                            frame_count += 1
                            
                            # Limit processing to 100 frames to avoid excessive processing time
                            if frame_count > 100:
                                break
                        
                        cap.release()
                        
                        # Convert dictionary to list format
                        recognized_students = [
                            {'student_id': sid, 'confidence': conf}
                            for sid, conf in recognized_students_dict.items()
                        ]
                        
                        # If no students recognized, try with a smaller frame skip
                        if not recognized_students:
                            flash('No students recognized in the video. Try using a clearer video or better lighting.', 'warning')
                            
                        # Clean up
                        os.remove(filepath)
                    except Exception as e:
                        flash(f'Error processing video: {str(e)}', 'error')
                        return redirect(url_for('take_attendance'))
                else:
                    flash('Invalid video file', 'error')
                    return redirect(url_for('take_attendance'))
            
            elif method == 'webcam':
                # Handle webcam data
                webcam_data = request.form.get('webcam_data')
                
                if webcam_data:
                    # Process the webcam frame directly instead of just parsing JSON
                    try:
                        # Make sure the temp directory exists
                        os.makedirs(config.TEMP_IMAGES_FOLDER, exist_ok=True)
                        
                        # Decode the base64 image
                        img_data = webcam_data.split(',')[1] if ',' in webcam_data else webcam_data
                        img_bytes = base64.b64decode(img_data)
                        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
                        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                        
                        # Detect faces in the frame
                        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                        
                        recognized_students = []
                        
                        # Process each detected face
                        for (x, y, w, h) in faces:
                            # Add some margin around the face (20%)
                            margin_x = int(w * 0.2)
                            margin_y = int(h * 0.2)
                            
                            # Calculate new coordinates with margins
                            x1 = max(0, x - margin_x)
                            y1 = max(0, y - margin_y)
                            x2 = min(frame.shape[1], x + w + margin_x)
                            y2 = min(frame.shape[0], y + h + margin_y)
                            
                            # Extract face region with margin
                            face_img = frame[y1:y2, x1:x2]
                            
                            # Save the face image temporarily
                            temp_face_path = os.path.join(config.TEMP_IMAGES_FOLDER, f'webcam_face_{x}_{y}.jpg')
                            cv2.imwrite(temp_face_path, face_img)
                            
                            # Recognize the face
                            student_id, confidence, message = face_recognition_system.recognize_face(temp_face_path)
                            
                            # If recognized, add to the list
                            if student_id:
                                recognized_students.append({
                                    'student_id': student_id,
                                    'confidence': confidence
                                })
                            
                            # Clean up
                            try:
                                os.remove(temp_face_path)
                            except:
                                pass
                        
                        # If no faces were detected or recognized
                        if not faces or not recognized_students:
                            flash('No faces detected or recognized in the webcam frame', 'warning')
                            
                    except Exception as e:
                        flash(f'Error processing webcam data: {str(e)}', 'error')
                        return redirect(url_for('take_attendance'))
                else:
                    flash('No webcam data received', 'error')
                    return redirect(url_for('take_attendance'))
            
            # Mark attendance for recognized students
            marked_count = 0
            duplicate_count = 0
            current_time = datetime.now().strftime('%H:%M:%S')
            
            for student_data in recognized_students:
                student_db_id = student_data['student_id']
                confidence = student_data['confidence']
                
                # Check for duplicate
                if database.check_duplicate_attendance(student_db_id, subject_id, attendance_date):
                    duplicate_count += 1
                    continue
                
                # Mark attendance
                success, _ = database.mark_attendance(
                    student_db_id, subject_id, attendance_date, current_time,
                    'Present', session['teacher_id'], confidence, method
                )
                
                if success:
                    marked_count += 1
            
            flash(f'Attendance marked for {marked_count} students', 'success')
            
            if duplicate_count > 0:
                flash(f'{duplicate_count} students already had attendance marked', 'info')
            
            # Get absent students and send notifications
            absent_students = database.get_absent_students(subject_id, attendance_date)
            
            if absent_students:
                # Prepare notification data
                notification_data = []
                for student in absent_students:
                    notification_data.append({
                        'student_name': student['full_name'],
                        'student_id': student['student_id'],
                        'roll_number': student['roll_number'],
                        'subject_name': subject['subject_name'],
                        'date': attendance_date,
                        'parent_email': student['parent_email'],
                        'parent_name': student['parent_name']
                    })
                
                # Send notifications
                results = email_service.send_bulk_absence_notifications(notification_data)
                
                flash(f'Absence notifications sent to {results["sent"]} parents', 'info')
                
                # Log notifications
                for student in absent_students:
                    database.log_absence_notification(
                        student['id'], subject_id, attendance_date,
                        student['parent_email'], True
                    )
            
            return redirect(url_for('attendance_records'))
            
        except Exception as e:
            flash(f'Error processing attendance: {str(e)}', 'error')
    
    return render_template('take_attendance.html', subjects=subjects, now=now)

# ============== Webcam Capture API ==============

@app.route('/api/detect_face', methods=['POST'])
@utils.login_required
def detect_face_api():
    """API endpoint to detect if face is present in frame"""
    try:
        data = request.json
        frame_data = data.get('frame')
        
        if not frame_data:
            return jsonify({'success': False, 'message': 'No frame data'})
        
        # Decode base64 image
        img_data = frame_data.split(',')[1] if ',' in frame_data else frame_data
        img_bytes = base64.b64decode(img_data)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Load face cascade
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Detect faces
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        if len(faces) > 0:
            return jsonify({
                'success': True,
                'face_detected': True,
                'faces_count': len(faces),
                'message': 'Face detected'
            })
        else:
            return jsonify({
                'success': True,
                'face_detected': False,
                'faces_count': 0,
                'message': 'No face detected'
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/recognize_frame', methods=['POST'])
@utils.login_required
def recognize_frame():
    """API endpoint to recognize face in webcam frame"""
    try:
        data = request.json
        frame_data = data.get('frame')
        
        if not frame_data:
            return jsonify({'success': False, 'message': 'No frame data'})
        
        # Decode base64 image
        img_data = frame_data.split(',')[1] if ',' in frame_data else frame_data
        img_bytes = base64.b64decode(img_data)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        # Process frame
        recognized = face_recognition_system.process_webcam_frame(frame)
        
        # Get student details
        students_info = []
        for student in recognized:
            student_data = database.get_student_by_id(student['student_id'])
            if student_data:
                students_info.append({
                    'id': student_data['id'],
                    'student_id': student_data['student_id'],
                    'name': student_data['full_name'],
                    'roll_number': student_data['roll_number'],
                    'confidence': round(student['confidence'] * 100, 2)
                })
        
        return jsonify({'success': True, 'students': students_info})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/test_cctv_connection', methods=['POST'])
@utils.login_required
def test_cctv_connection():
    """API endpoint to test CCTV stream connection"""
    try:
        data = request.json
        cctv_url = data.get('cctv_url')
        
        if not cctv_url:
            return jsonify({'success': False, 'message': 'No CCTV URL provided'})
        
        # Try to open the CCTV stream
        cap = cv2.VideoCapture(cctv_url)
        
        # Check if stream opened successfully
        if not cap.isOpened():
            return jsonify({
                'success': False,
                'message': 'Could not connect to the CCTV stream'
            })
        
        # Read a frame to confirm it's working
        ret, frame = cap.read()
        
        # Release the capture
        cap.release()
        
        if not ret or frame is None:
            return jsonify({
                'success': False,
                'message': 'Connected but could not read frames from the stream'
            })
        
        return jsonify({
            'success': True,
            'message': 'CCTV connection successful'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/process_cctv_stream', methods=['POST'])
@utils.login_required
def process_cctv_stream():
    """API endpoint to process CCTV stream and recognize faces"""
    try:
        data = request.json
        cctv_url = data.get('cctv_url')
        duration = int(data.get('duration', 30))  # Default to 30 seconds
        
        if not cctv_url:
            return jsonify({'success': False, 'message': 'No CCTV URL provided'})
        
        # Process the CCTV stream
        recognized_students = utils.process_cctv_for_attendance(cctv_url, duration)
        
        # Get student details
        students_info = []
        for student in recognized_students:
            student_data = database.get_student_by_id(student['student_id'])
            if student_data:
                students_info.append({
                    'id': student_data['id'],
                    'student_id': student_data['student_id'],
                    'name': student_data['full_name'],
                    'roll_number': student_data['roll_number'],
                    'confidence': round(student['confidence'] * 100, 2)
                })
        
        return jsonify({
            'success': True,
            'students': students_info
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# ============== Attendance Records ==============

@app.route('/attendance_records')
@utils.login_required
def attendance_records():
    """View attendance records with filters"""
    # Get filter parameters
    subject_id = request.args.get('subject_id')
    date = request.args.get('date')
    student_id = request.args.get('student_id')
    department = request.args.get('department')
    
    # Get records
    records = database.get_attendance_records(subject_id, date, student_id, department)
    
    # Get all subjects for filter
    subjects = database.get_all_subjects()
    
    # Get all departments (unique)
    students = database.get_all_students()
    departments = list(set([s['department'] for s in students]))
    
    return render_template('attendance_records.html',
                         records=records,
                         subjects=subjects,
                         departments=departments,
                         selected_subject=subject_id,
                         selected_date=date,
                         selected_department=department,
                         now=datetime.now())

# ============== Model Training ==============

@app.route('/train_model', methods=['GET', 'POST'])
@utils.login_required
def train_model():
    """Train the face recognition model"""
    if request.method == 'POST':
        try:
            success, message = face_recognition_system.train_model()
            
            if success:
                flash(message, 'success')
            else:
                flash(message, 'error')
                
        except Exception as e:
            flash(f'Training failed: {str(e)}', 'error')
        
        return redirect(url_for('train_model'))
    
    # Get training info
    total_students = database.get_students_count()
    model_trained = face_recognition_system.is_model_trained()
    trained_students_count = len(face_recognition_system.face_database)
    
    return render_template('model_training.html',
                         total_students=total_students,
                         model_trained=model_trained,
                         trained_students_count=trained_students_count,
                         now=datetime.now())

# ============== Error Handlers ==============

@app.errorhandler(404)
def not_found(error):
    flash('Page not found', 'error')
    return redirect(url_for('dashboard'))

@app.errorhandler(500)
def internal_error(error):
    flash('An internal error occurred', 'error')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=config.DEBUG, host='0.0.0.0', port=8100)
