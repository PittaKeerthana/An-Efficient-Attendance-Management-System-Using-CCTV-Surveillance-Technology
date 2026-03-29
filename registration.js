// Registration webcam capture with automatic face detection
let webcamStream = null;
let capturedImages = [];
const maxImages = 10;
let isCapturing = false;
let captureInterval = null;
let faceCheckInterval = null;

const webcam = document.getElementById('webcam');
const canvas = document.getElementById('canvas');
const startBtn = document.getElementById('startWebcam');
const captureBtn = document.getElementById('captureBtn');
const stopBtn = document.getElementById('stopWebcam');
const captureCount = document.getElementById('captureCount');
const capturedImagesDiv = document.getElementById('capturedImages');
const imagesDataInput = document.getElementById('imagesData');
const submitBtn = document.getElementById('submitBtn');

// Start webcam
startBtn.addEventListener('click', async () => {
    try {
        webcamStream = await navigator.mediaDevices.getUserMedia({ 
            video: { width: 640, height: 480 } 
        });
        
        webcam.srcObject = webcamStream;
        webcam.play();
        
        startBtn.disabled = true;
        captureBtn.disabled = false;
        stopBtn.disabled = false;
        
        // Show instruction
        showNotification('Camera started! Click "Start Auto Capture" to begin automatic face detection.', 'info');
        
    } catch (error) {
        console.error('Error accessing webcam:', error);
        alert('Unable to access webcam. Please check permissions.');
    }
});

// Auto capture with face detection
captureBtn.addEventListener('click', () => {
    if (isCapturing) {
        // Stop auto capture
        stopAutoCapture();
        captureBtn.innerHTML = '<i class="fas fa-camera mr-2"></i> Start Auto Capture (<span id="captureCount">' + capturedImages.length + '</span>/10)';
        captureBtn.classList.remove('btn-error');
        captureBtn.classList.add('btn-secondary');
        showNotification('Auto-capture stopped.', 'warning');
    } else {
        // Start auto capture
        startAutoCapture();
        captureBtn.innerHTML = '<i class="fas fa-stop mr-2"></i> Stop Auto Capture (<span id="captureCount">' + capturedImages.length + '</span>/10)';
        captureBtn.classList.remove('btn-secondary');
        captureBtn.classList.add('btn-error');
        
        showNotification('Auto-capture started! Position your face and change angles slightly.', 'success');
    }
});

async function startAutoCapture() {
    isCapturing = true;
    let lastCaptureTime = 0;
    const captureDelay = 2000; // 2 seconds between captures
    
    // Continuous face detection
    faceCheckInterval = setInterval(async () => {
        if (capturedImages.length >= maxImages) {
            stopAutoCapture();
            captureBtn.innerHTML = '<i class="fas fa-check mr-2"></i> Completed (<span id="captureCount">10</span>/10)';
            captureBtn.disabled = true;
            showNotification('All 10 images captured successfully!', 'success');
            return;
        }
        
        const currentTime = Date.now();
        
        // Check if enough time has passed since last capture
        if (currentTime - lastCaptureTime < captureDelay) {
            return;
        }
        
        // Detect face
        const faceDetected = await detectFaceInFrame();
        
        if (faceDetected) {
            captureImage();
            lastCaptureTime = currentTime;
            
            // Visual and audio feedback
            flashWebcam();
            playBeep();
            
            // Update button text
            captureBtn.innerHTML = '<i class="fas fa-stop mr-2"></i> Stop Auto Capture (<span id="captureCount">' + capturedImages.length + '</span>/10)';
            
            // Show progress
            const remaining = maxImages - capturedImages.length;
            if (remaining > 0) {
                showNotification(`Captured! ${remaining} more to go. Please change your angle.`, 'success');
            }
        }
        
    }, 500); // Check every 500ms
}

function stopAutoCapture() {
    isCapturing = false;
    if (faceCheckInterval) {
        clearInterval(faceCheckInterval);
        faceCheckInterval = null;
    }
}

async function detectFaceInFrame() {
    try {
        // Set canvas size
        canvas.width = webcam.videoWidth;
        canvas.height = webcam.videoHeight;
        
        // Draw current frame
        const context = canvas.getContext('2d');
        context.drawImage(webcam, 0, 0, canvas.width, canvas.height);
        
        // Convert to data URL
        const frameData = canvas.toDataURL('image/jpeg', 0.8);
        
        // Send to backend for face detection
        const response = await fetch('/api/detect_face', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ frame: frameData })
        });
        
        const result = await response.json();
        
        if (result.success && result.face_detected) {
            return true;
        }
        
        return false;
        
    } catch (error) {
        console.error('Face detection error:', error);
        // On error, use simple timer-based capture
        return true;
    }
}

function captureImage() {
    if (capturedImages.length >= maxImages) {
        return;
    }
    
    // Set canvas size to match video
    canvas.width = webcam.videoWidth;
    canvas.height = webcam.videoHeight;
    
    // Draw current frame to canvas
    const context = canvas.getContext('2d');
    context.drawImage(webcam, 0, 0, canvas.width, canvas.height);
    
    // Convert to data URL
    const imageData = canvas.toDataURL('image/jpeg', 0.9);
    
    // Add to captured images array
    capturedImages.push(imageData);
    
    // Update UI
    updateCapturedImagesDisplay();
    updateCaptureCount();
    
    // Enable submit button if at least 5 images captured
    if (capturedImages.length >= 5) {
        submitBtn.disabled = false;
    }
}

// Visual feedback for capture
function flashWebcam() {
    webcam.style.border = '5px solid #22c55e';
    webcam.style.boxShadow = '0 0 20px #22c55e';
    setTimeout(() => {
        webcam.style.border = '2px solid #e5e7eb';
        webcam.style.boxShadow = 'none';
    }, 300);
}

// Audio feedback
function playBeep() {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 1000;
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.15);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.15);
    } catch (error) {
        // Ignore audio errors
    }
}

// Show notification
function showNotification(message, type) {
    // Remove existing notifications
    const existingAlerts = document.querySelectorAll('.auto-capture-alert');
    existingAlerts.forEach(alert => alert.remove());
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} shadow-lg mb-4 auto-capture-alert`;
    alert.innerHTML = `
        <div>
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'warning' ? 'exclamation-triangle' : 'info-circle'}"></i>
            <span>${message}</span>
        </div>
    `;
    
    // Insert before webcam
    const webcamContainer = document.querySelector('.webcam-container');
    webcamContainer.parentNode.insertBefore(alert, webcamContainer);
    
    // Auto remove after 2.5 seconds
    setTimeout(() => {
        alert.style.transition = 'opacity 0.5s';
        alert.style.opacity = '0';
        setTimeout(() => alert.remove(), 500);
    }, 2500);
}

// Stop webcam
stopBtn.addEventListener('click', () => {
    stopAutoCapture();
    
    if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
        webcam.srcObject = null;
        
        startBtn.disabled = false;
        captureBtn.disabled = true;
        captureBtn.innerHTML = '<i class="fas fa-camera mr-2"></i> Start Auto Capture (<span id="captureCount">' + capturedImages.length + '</span>/10)';
        captureBtn.classList.remove('btn-error');
        captureBtn.classList.add('btn-secondary');
        stopBtn.disabled = true;
        
        showNotification('Camera stopped.', 'info');
    }
});

// Update captured images display
function updateCapturedImagesDisplay() {
    capturedImagesDiv.innerHTML = '';
    
    capturedImages.forEach((imageData, index) => {
        const imgContainer = document.createElement('div');
        imgContainer.className = 'relative';
        
        const img = document.createElement('img');
        img.src = imageData;
        img.className = 'face-preview border-2 border-primary rounded-lg';
        
        const deleteBtn = document.createElement('button');
        deleteBtn.type = 'button';
        deleteBtn.className = 'btn btn-circle btn-xs btn-error absolute top-1 right-1';
        deleteBtn.innerHTML = '<i class="fas fa-times"></i>';
        deleteBtn.onclick = () => removeImage(index);
        
        imgContainer.appendChild(img);
        imgContainer.appendChild(deleteBtn);
        capturedImagesDiv.appendChild(imgContainer);
    });
}

// Remove captured image
function removeImage(index) {
    capturedImages.splice(index, 1);
    updateCapturedImagesDisplay();
    updateCaptureCount();
    
    if (capturedImages.length < 5) {
        submitBtn.disabled = true;
    }
}

// Update capture count
function updateCaptureCount() {
    captureCount.textContent = capturedImages.length;
}

// Form submission
document.getElementById('registrationForm').addEventListener('submit', (e) => {
    if (capturedImages.length < 5) {
        e.preventDefault();
        alert('Please capture at least 5 face images');
        return false;
    }
    
    // Store images data in hidden input
    imagesDataInput.value = JSON.stringify(capturedImages);
    
    // Show loading
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="loading loading-spinner"></span> Registering...';
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
    }
});
