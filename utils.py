import os
import hashlib
import secrets
from functools import wraps
from flask import session, redirect, url_for, flash
from datetime import datetime
import config

def hash_password(password):
    """Hash a password using SHA-256"""
    salt = secrets.token_hex(16)
    pwdhash = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return f"{salt}${pwdhash}"

def verify_password(password, password_hash):
    """Verify a password against its hash"""
    try:
        salt, pwdhash = password_hash.split('$')
        return hashlib.sha256((salt + password).encode('utf-8')).hexdigest() == pwdhash
    except:
        return False

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'teacher_id' not in session:
            flash('Please login to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def generate_student_id():
    """Generate a unique student ID"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_part = secrets.token_hex(3)
    return f"STU{timestamp}{random_part}".upper()

def allowed_file(filename, file_type='image'):
    """Check if file extension is allowed"""
    if '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    
    if file_type == 'image':
        return ext in config.ALLOWED_IMAGE_EXTENSIONS
    elif file_type == 'video':
        return ext in config.ALLOWED_VIDEO_EXTENSIONS
    
    return False

def process_cctv_for_attendance(cctv_url, duration=30):
    """Process CCTV stream for the specified duration and recognize faces"""
    import cv2
    import os
    import numpy as np
    from face_recognition import face_recognition_system
    import config
    
    # Open the CCTV stream
    cap = cv2.VideoCapture(cctv_url)
    
    if not cap.isOpened():
        raise Exception("Could not open CCTV stream")
    
    # Calculate frames to process based on duration and FPS
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:  # If FPS cannot be determined, assume 30 FPS
        fps = 30
    
    total_frames = int(fps * duration)
    frame_skip = max(1, int(fps / 3))  # Process 3 frames per second
    
    # Initialize face detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    recognized_students = {}
    frame_count = 0
    processed_count = 0
    
    # Process frames for the specified duration
    while frame_count < total_frames and processed_count < 100:  # Limit to 100 processed frames
        ret, frame = cap.read()
        
        if not ret:
            break
        
        # Process every nth frame
        if frame_count % frame_skip == 0:
            # Detect faces
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            for (x, y, w, h) in faces:
                # Add margin to face (20%)
                margin_x = int(w * 0.2)
                margin_y = int(h * 0.2)
                
                # Calculate new coordinates with margin
                x1 = max(0, x - margin_x)
                y1 = max(0, y - margin_y)
                x2 = min(frame.shape[1], x + w + margin_x)
                y2 = min(frame.shape[0], y + h + margin_y)
                
                # Extract face region
                face_img = frame[y1:y2, x1:x2]
                
                # Save face temporarily
                temp_face_path = os.path.join(config.UPLOAD_FOLDER, f'temp_face_{processed_count}.jpg')
                cv2.imwrite(temp_face_path, face_img)
                
                # Recognize face
                student = face_recognition_system.recognize_face(temp_face_path)
                
                if student:
                    student_id = student['id']
                    confidence = student['confidence']
                    
                    # Update student record with highest confidence
                    if student_id not in recognized_students or confidence > recognized_students[student_id]['confidence']:
                        recognized_students[student_id] = {
                            'student_id': student_id,
                            'confidence': confidence
                        }
                
                # Clean up temporary file
                if os.path.exists(temp_face_path):
                    os.remove(temp_face_path)
            
            processed_count += 1
        
        frame_count += 1
    
    # Release the video capture
    cap.release()
    
    # Convert dictionary to list
    return list(recognized_students.values())

def validate_image(file):
    """Validate uploaded image file"""
    if not file:
        return False, "No file provided"
    
    if file.filename == '':
        return False, "No file selected"
    
    if not allowed_file(file.filename, 'image'):
        return False, f"Invalid file type. Allowed: {', '.join(config.ALLOWED_IMAGE_EXTENSIONS)}"
    
    return True, "Valid"

def validate_video(file):
    """Validate uploaded video file"""
    if not file:
        return False, "No file provided"
    
    if file.filename == '':
        return False, "No file selected"
    
    if not allowed_file(file.filename, 'video'):
        return False, f"Invalid file type. Allowed: {', '.join(config.ALLOWED_VIDEO_EXTENSIONS)}"
    
    return True, "Valid"

def create_student_directory(student_id):
    """Create directory for student face images"""
    student_dir = os.path.join(config.STUDENT_FACES_FOLDER, student_id)
    os.makedirs(student_dir, exist_ok=True)
    return student_dir

def format_date(date_obj):
    """Format date object to string"""
    if isinstance(date_obj, str):
        return date_obj
    return date_obj.strftime('%Y-%m-%d')

def format_datetime(datetime_obj):
    """Format datetime object to string"""
    if isinstance(datetime_obj, str):
        return datetime_obj
    return datetime_obj.strftime('%Y-%m-%d %H:%M:%S')

def get_file_extension(filename):
    """Get file extension from filename"""
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def cleanup_temp_files(directory):
    """Clean up temporary files in a directory"""
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)
        return True
    except Exception as e:
        print(f"Error cleaning up temp files: {str(e)}")
        return False

def save_uploaded_file(file, directory, filename=None):
    """Save uploaded file to specified directory"""
    try:
        if filename is None:
            filename = secrets.token_hex(8) + '.' + get_file_extension(file.filename)
        
        filepath = os.path.join(directory, filename)
        file.save(filepath)
        return filepath, filename
    except Exception as e:
        print(f"Error saving file: {str(e)}")
        return None, None
