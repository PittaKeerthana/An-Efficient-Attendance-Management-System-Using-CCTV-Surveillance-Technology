import os
import cv2
import numpy as np
import pickle
from deepface import DeepFace
from datetime import datetime
import config
import database

class FaceRecognitionSystem:
    def __init__(self):
        self.model_name = config.FACE_RECOGNITION_MODEL
        self.detector_backend = config.FACE_DETECTION_BACKEND
        self.threshold = config.FACE_RECOGNITION_THRESHOLD
        self.face_database = {}
        self.load_model()
    
    def detect_faces(self, image_path):
        """Detect faces in an image"""
        try:
            # Use DeepFace to detect faces
            faces = DeepFace.extract_faces(
                img_path=image_path,
                detector_backend=self.detector_backend,
                enforce_detection=False
            )
            return faces
        except Exception as e:
            print(f"Error detecting faces: {str(e)}")
            return []
    
    def generate_embedding(self, image_path):
        """Generate face embedding for an image"""
        try:
            embedding = DeepFace.represent(
                img_path=image_path,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=True
            )
            
            if embedding and len(embedding) > 0:
                print(f"DEBUG: Embedding generated successfully. First 5 elements: {embedding[0]['embedding'][:5]}")
                return embedding[0]["embedding"]
            print(f"DEBUG: Embedding generation failed or returned empty for {image_path}")
            return None
        except Exception as e:
            print(f"Error generating embedding: {str(e)}")
            return None
    
    def calculate_distance(self, embedding1, embedding2):
        """Calculate Euclidean distance between two embeddings"""
        return np.linalg.norm(np.array(embedding1) - np.array(embedding2))
    
    def recognize_face(self, image_path):
        """Recognize face in image and return student info"""
        try:
            # First, ensure we're working with a face image
            img = cv2.imread(image_path)
            if img is None:
                print(f"DEBUG: Could not read image: {image_path}")
                return None, 0.0, "Could not read image"
                
            # Detect face in the image
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            
            # If no face detected, return early
            if len(faces) == 0:
                print(f"DEBUG: No face detected in image: {image_path}")
                return None, 0.0, "No face detected"
                
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
            
            # Save the face image temporarily
            temp_face_path = os.path.join(config.TEMP_IMAGES_FOLDER, 'temp_recognition_face.jpg')
            cv2.imwrite(temp_face_path, face_img)
            
            # Generate embedding for the face image
            print(f"DEBUG: Generating embedding for face image: {temp_face_path}")
            input_embedding = self.generate_embedding(temp_face_path)
            
            # Clean up temp file
            try:
                os.remove(temp_face_path)
            except:
                pass
            
            if input_embedding is None:
                print(f"DEBUG: Embedding generation failed for detected face")
                return None, 0.0, "Embedding generation failed"
            print(f"DEBUG: Input embedding generated. Shape: {len(input_embedding)}")
            
            # Compare with all stored embeddings
            best_match = None
            best_distance = float('inf')
            
            print(f"DEBUG: Starting comparison with {len(self.face_database)} students in database.")
            for student_id, embeddings_list in self.face_database.items():
                for stored_embedding in embeddings_list:
                    distance = self.calculate_distance(input_embedding, stored_embedding)
                    print(f"DEBUG: Comparing student {student_id}, Distance: {distance:.4f}, Threshold: {self.threshold:.4f}")
                    
                    if distance < best_distance:
                        best_distance = distance
                        best_match = student_id
            
            # Check if match is within threshold
            if best_match and best_distance < self.threshold:
                confidence = max(0, 1 - (best_distance / self.threshold))
                return best_match, confidence, "Match found"
            else:
                return None, 0.0, "No match found"
                
        except Exception as e:
            print(f"Error recognizing face: {str(e)}")
            return None, 0.0, str(e)
    
    def recognize_faces_in_image(self, image_path):
        """Recognize multiple faces in an image"""
        recognized_students = []
        
        try:
            # Detect all faces in image
            faces = self.detect_faces(image_path)
            
            if not faces:
                return []
            
            # Load image
            img = cv2.imread(image_path)
            
            for i, face in enumerate(faces):
                # Extract face region
                facial_area = face.get('facial_area', {})
                if not facial_area:
                    continue
                
                x = facial_area.get('x', 0)
                y = facial_area.get('y', 0)
                w = facial_area.get('w', 0)
                h = facial_area.get('h', 0)
                
                # Crop face
                face_img = img[y:y+h, x:x+w]
                
                # Save temporary face image
                temp_face_path = os.path.join(config.TEMP_IMAGES_FOLDER, f'temp_face_{i}.jpg')
                cv2.imwrite(temp_face_path, face_img)
                
                # Recognize face
                student_id, confidence, message = self.recognize_face(temp_face_path)
                
                # Add logging for the embedding generated from the cropped webcam frame
                if student_id:
                    print(f"DEBUG: Webcam frame embedding for student {student_id}. First 5 elements: {self.generate_embedding(temp_face_path)[:5]}")
                    recognized_students.append({
                        'student_id': student_id,
                        'confidence': confidence,
                        'face_location': (x, y, w, h)
                    })
                
                # Clean up temp file
                try:
                    os.remove(temp_face_path)
                except:
                    pass
            
            return recognized_students
            
        except Exception as e:
            print(f"Error recognizing faces in image: {str(e)}")
            return []
    
    def recognize_faces_in_video(self, video_path, frame_skip=30):
        """Recognize faces in video (process every nth frame)"""
        recognized_students = {}
        
        try:
            cap = cv2.VideoCapture(video_path)
            frame_count = 0
            
            while cap.isOpened():
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                # Process every nth frame
                if frame_count % frame_skip == 0:
                    # Save frame temporarily
                    temp_frame_path = os.path.join(config.TEMP_IMAGES_FOLDER, 'temp_frame.jpg')
                    cv2.imwrite(temp_frame_path, frame)
                    
                    # Recognize faces in frame
                    students = self.recognize_faces_in_image(temp_frame_path)
                    
                    # Aggregate results
                    for student in students:
                        student_id = student['student_id']
                        confidence = student['confidence']
                        
                        if student_id in recognized_students:
                            # Update with higher confidence
                            if confidence > recognized_students[student_id]:
                                recognized_students[student_id] = confidence
                        else:
                            recognized_students[student_id] = confidence
                    
                    # Clean up temp file
                    try:
                        os.remove(temp_frame_path)
                    except:
                        pass
                
                frame_count += 1
            
            cap.release()
            
            # Convert to list format
            result = [
                {'student_id': sid, 'confidence': conf}
                for sid, conf in recognized_students.items()
            ]
            
            return result
            
        except Exception as e:
            print(f"Error recognizing faces in video: {str(e)}")
            return []
    
    def process_webcam_frame(self, frame):
        """Process a single webcam frame for face recognition"""
        temp_frame_path = None
        try:
            # Save frame temporarily
            if frame is None:
                print("Error: Received empty frame in process_webcam_frame")
                return []
            
            temp_frame_path = os.path.join(config.TEMP_IMAGES_FOLDER, 'webcam_frame.jpg')
            cv2.imwrite(temp_frame_path, frame)
            print(f"Saved webcam frame to {temp_frame_path}")
            
            # Recognize faces
            students = self.recognize_faces_in_image(temp_frame_path)
            
            return students
            
        except Exception as e:
            print(f"Error processing webcam frame: {str(e)}")
            return []
        finally:
            # Clean up temp file
            if temp_frame_path and os.path.exists(temp_frame_path):
                try:
                    os.remove(temp_frame_path)
                except Exception as e:
                    print(f"Error cleaning up temp webcam frame: {str(e)}")
    
    def train_model(self):
        """Train/update the face recognition model with all student embeddings"""
        try:
            print("Starting model training...")
            
            # Clear existing database
            self.face_database = {}
            
            # Get all students
            students = database.get_all_students()
            
            if not students:
                return False, "No students found to train"
            
            trained_count = 0
            failed_count = 0
            
            for student in students:
                student_db_id = student['id']
                student_id = student['student_id']
                face_images_path = student['face_images_path']
                
                if not face_images_path:
                    failed_count += 1
                    continue
                
                # Parse image paths
                import json
                image_paths = json.loads(face_images_path)
                
                student_embeddings = []
                
                for img_path in image_paths:
                    if os.path.exists(img_path):
                        # Detect faces in the training image
                        faces = self.detect_faces(img_path)
                        
                        if not faces:
                            print(f"DEBUG: No face detected in training image: {img_path}")
                            continue
                        
                        # Load image
                        img = cv2.imread(img_path)

                        for i, face in enumerate(faces):
                            # Extract face region
                            facial_area = face.get('facial_area', {})
                            if not facial_area:
                                continue
                            
                            x = facial_area.get('x', 0)
                            y = facial_area.get('y', 0)
                            w = facial_area.get('w', 0)
                            h = facial_area.get('h', 0)
                            
                            # Crop face
                            face_img = img[y:y+h, x:x+w]
                            
                            # Save temporary cropped face image
                            temp_face_path = os.path.join(config.TEMP_IMAGES_FOLDER, f'train_face_{student_db_id}_{i}.jpg')
                            cv2.imwrite(temp_face_path, face_img)

                            embedding = self.generate_embedding(temp_face_path)
                            
                            if embedding is not None:
                                student_embeddings.append(embedding)
                                # Save to database
                                database.save_face_embedding(student_db_id, embedding, img_path)
                                print(f"DEBUG: Saved embedding for student {student_db_id} from {img_path}. First 5 elements: {embedding[:5]}")
                            
                            # Clean up temp file
                            try:
                                os.remove(temp_face_path)
                            except Exception as e:
                                print(f"Error cleaning up temp training face image: {str(e)}")
                
                if student_embeddings:
                    self.face_database[student_db_id] = student_embeddings
                    trained_count += 1
                else:
                    failed_count += 1
            
            # Save model to file
            self.save_model()
            
            message = f"Training complete! Successfully trained {trained_count} students. Failed: {failed_count}"
            print(message)
            
            return True, message
            
        except Exception as e:
            error_msg = f"Error training model: {str(e)}"
            print(error_msg)
            return False, error_msg
    
    def save_model(self):
        """Save face database to file"""
        try:
            with open(config.MODEL_PATH, 'wb') as f:
                pickle.dump(self.face_database, f)
            print("Model saved successfully")
            return True
        except Exception as e:
            print(f"Error saving model: {str(e)}")
            return False
    
    def load_model(self):
        """Load face database from file"""
        try:
            if os.path.exists(config.MODEL_PATH):
                with open(config.MODEL_PATH, 'rb') as f:
                    self.face_database = pickle.load(f)
                print(f"Model loaded successfully with {len(self.face_database)} students")
                return True
            else:
                print("No saved model found. Please train the model first.")
                return False
        except Exception as e:
            print(f"Error loading model: {str(e)}")
            self.face_database = {}
            return False
    
    def is_model_trained(self):
        """Check if model is trained"""
        return len(self.face_database) > 0

# Global face recognition system instance
face_recognition_system = FaceRecognitionSystem()
