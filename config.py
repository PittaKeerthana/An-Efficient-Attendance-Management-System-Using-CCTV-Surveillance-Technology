import os

# Base directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Flask Configuration
SECRET_KEY = 'your-secret-key-change-this-in-production'
DEBUG = True

# Database Configuration
DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'attendance.db')

# Upload Configuration
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
TEMP_IMAGES_FOLDER = os.path.join(UPLOAD_FOLDER, 'temp_images')
TEMP_VIDEOS_FOLDER = os.path.join(UPLOAD_FOLDER, 'temp_videos')
STUDENT_FACES_FOLDER = os.path.join(BASE_DIR, 'static', 'student_faces')

# Allowed file extensions
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}

# Maximum file size (16MB)
MAX_FILE_SIZE = 16 * 1024 * 1024

# Face Recognition Configuration
FACE_RECOGNITION_THRESHOLD = 9.0  # Higher value allows more matches
FACE_DETECTION_BACKEND = 'opencv'
FACE_RECOGNITION_MODEL = 'Facenet'
IMAGES_PER_STUDENT = 10

# Model Configuration
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'face_embeddings.pkl')

# Email Configuration (Update with your SMTP details)
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USERNAME = 'ayushtiwari.creatorslab@gmail.com'  # Change this
EMAIL_PASSWORD = 'tecxbcymvxdzdtni'      # Change this (use app password for Gmail)
EMAIL_FROM_NAME = 'Attendance System'
EMAIL_FROM_ADDRESS = 'ayushtiwari.creatorslab@gmail.com'

# Session Configuration
PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes

# Create necessary directories
os.makedirs(os.path.join(BASE_DIR, 'database'), exist_ok=True)
os.makedirs(TEMP_IMAGES_FOLDER, exist_ok=True)
os.makedirs(TEMP_VIDEOS_FOLDER, exist_ok=True)
os.makedirs(STUDENT_FACES_FOLDER, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'models'), exist_ok=True)
