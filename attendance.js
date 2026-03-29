// Tab switching
const tabs = document.querySelectorAll('.tab');
const tabContents = document.querySelectorAll('.tab-content');

tabs.forEach(tab => {
    tab.addEventListener('click', (e) => {
        e.preventDefault();
        
        // Remove active class from all tabs
        tabs.forEach(t => t.classList.remove('tab-active'));
        
        // Add active class to clicked tab
        tab.classList.add('tab-active');
        
        // Hide all tab contents
        tabContents.forEach(content => {
            content.classList.remove('hidden'); // Ensure hidden class is removed first
            content.style.display = 'none';
        });
        
        // Show selected tab content
        const tabName = tab.getAttribute('data-tab');
        const selectedTabContent = document.getElementById(tabName + 'Tab');
        if (selectedTabContent) {
            selectedTabContent.style.display = 'block';
        }
    });
});

// Webcam functionality
let webcamStream = null;
let recognizedStudentsData = [];

const webcam = document.getElementById('webcam');
const canvas = document.getElementById('canvas');
const startBtn = document.getElementById('startWebcam');
const recognizeBtn = document.getElementById('recognizeBtn');
const stopBtn = document.getElementById('stopWebcam');
const recognizedDiv = document.getElementById('recognizedStudents');
const studentsTableBody = document.getElementById('studentsTableBody');
const webcamDataInput = document.getElementById('webcamData');
const markAttendanceBtn = document.getElementById('markAttendanceBtn');

// Start webcam
if (startBtn) {
    startBtn.addEventListener('click', async () => {
        try {
            webcamStream = await navigator.mediaDevices.getUserMedia({ 
                video: { width: 640, height: 480 } 
            });
            
            webcam.srcObject = webcamStream;
            webcam.play();
            
            startBtn.disabled = true;
            recognizeBtn.disabled = false;
            stopBtn.disabled = false;
            
        } catch (error) {
            console.error('Error accessing webcam:', error);
            alert('Unable to access webcam. Please check permissions.');
        }
    });
}

// Recognize faces
if (recognizeBtn) {
    recognizeBtn.addEventListener('click', async () => {
        // Disable button during recognition
        recognizeBtn.disabled = true;
        recognizeBtn.innerHTML = '<span class="loading loading-spinner"></span> Recognizing...';
        
        // Capture current frame
        canvas.width = webcam.videoWidth;
        canvas.height = webcam.videoHeight;
        const context = canvas.getContext('2d');
        context.drawImage(webcam, 0, 0, canvas.width, canvas.height);
        
        // Convert to data URL
        const frameData = canvas.toDataURL('image/jpeg', 0.9);
        
        try {
            // Send to server for recognition
            const response = await fetch('/api/recognize_frame', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ frame: frameData })
            });
            
            const result = await response.json();
            
            if (result.success && result.students.length > 0) {
                recognizedStudentsData = result.students;
                displayRecognizedStudents(result.students);
                markAttendanceBtn.disabled = false;
                
                // Store data for submission
                webcamDataInput.value = JSON.stringify(result.students.map(s => ({
                    student_id: s.id,
                    confidence: s.confidence / 100
                })));
            } else {
                alert('No students recognized. Please try again.');
            }
            
        } catch (error) {
            console.error('Error recognizing faces:', error);
            alert('Error recognizing faces. Please try again.');
        }
        
        // Re-enable button
        recognizeBtn.disabled = false;
        recognizeBtn.innerHTML = '<i class="fas fa-search mr-2"></i> Recognize Faces';
    });
}

// Display recognized students
function displayRecognizedStudents(students) {
    studentsTableBody.innerHTML = '';
    
    students.forEach(student => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${student.student_id}</td>
            <td>${student.name}</td>
            <td>${student.roll_number}</td>
            <td>
                <div class="badge badge-${student.confidence > 80 ? 'success' : student.confidence > 60 ? 'warning' : 'error'}">
                    ${student.confidence}%
                </div>
            </td>
        `;
        studentsTableBody.appendChild(row);
    });
    
    recognizedDiv.classList.remove('hidden');
}

// Stop webcam
if (stopBtn) {
    stopBtn.addEventListener('click', () => {
        if (webcamStream) {
            webcamStream.getTracks().forEach(track => track.stop());
            webcam.srcObject = null;
            
            startBtn.disabled = false;
            recognizeBtn.disabled = true;
            stopBtn.disabled = true;
        }
    });
}

// Form submission
const attendanceForm = document.getElementById('attendanceForm');
if (attendanceForm) {
    attendanceForm.addEventListener('submit', (e) => {
        const subjectSelect = document.getElementById('subjectSelect');
        const dateInput = document.getElementById('attendanceDate');
        
        if (!subjectSelect.value || !dateInput.value) {
            e.preventDefault();
            alert('Please select subject and date');
            return false;
        }
        
        // Show loading for submit button
        const submitBtns = attendanceForm.querySelectorAll('button[type="submit"]');
        submitBtns.forEach(btn => {
            if (!btn.disabled) {
                btn.disabled = true;
                btn.innerHTML = '<span class="loading loading-spinner"></span> Processing...';
            }
        });
    });
}

// CCTV functionality
const cctvUrlInput = document.getElementById('cctvUrl');
const cctvDurationInput = document.getElementById('cctvDuration');
const testCctvBtn = document.getElementById('testCctvBtn');
const processCctvBtn = document.getElementById('processCctvBtn');
const cctvPreview = document.getElementById('cctvPreview');
const cctvVideo = document.getElementById('cctvVideo');
const cctvRecognizedStudents = document.getElementById('cctvRecognizedStudents');
const cctvStudentsTableBody = document.getElementById('cctvStudentsTableBody');
const cctvDataInput = document.getElementById('cctvData');
const markCctvAttendanceBtn = document.getElementById('markCctvAttendanceBtn');

// Test CCTV connection
if (testCctvBtn) {
    testCctvBtn.addEventListener('click', async () => {
        const cctvUrl = cctvUrlInput.value.trim();
        
        if (!cctvUrl) {
            alert('Please enter a valid CCTV stream URL');
            return;
        }
        
        testCctvBtn.disabled = true;
        testCctvBtn.innerHTML = '<span class="loading loading-spinner"></span> Testing...';
        
        try {
            // Send test request to server
            const response = await fetch('/api/test_cctv_connection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ cctv_url: cctvUrl })
            });
            
            const result = await response.json();
            
            if (result.success) {
                alert('CCTV connection successful! You can now process the stream.');
                cctvPreview.classList.remove('hidden');
                // We can't directly show RTSP streams in browser, so we'll show a placeholder or first frame
                // In a real implementation, you might use WebRTC or HLS for preview
            } else {
                alert(`Connection failed: ${result.message}`);
            }
        } catch (error) {
            console.error('Error testing CCTV connection:', error);
            alert('Error testing CCTV connection. Please check the URL and try again.');
        }
        
        testCctvBtn.disabled = false;
        testCctvBtn.innerHTML = '<i class="fas fa-vial mr-2"></i> Test Connection';
    });
}

// Process CCTV stream
if (processCctvBtn) {
    processCctvBtn.addEventListener('click', async () => {
        const cctvUrl = cctvUrlInput.value.trim();
        const duration = cctvDurationInput.value;
        
        if (!cctvUrl) {
            alert('Please enter a valid CCTV stream URL');
            return;
        }
        
        processCctvBtn.disabled = true;
        processCctvBtn.innerHTML = '<span class="loading loading-spinner"></span> Processing...';
        
        try {
            // Send process request to server
            const response = await fetch('/api/process_cctv_stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    cctv_url: cctvUrl,
                    duration: duration
                })
            });
            
            const result = await response.json();
            
            if (result.success && result.students.length > 0) {
                displayCctvRecognizedStudents(result.students);
                markCctvAttendanceBtn.disabled = false;
                
                // Store data for submission
                cctvDataInput.value = JSON.stringify(result.students.map(s => ({
                    student_id: s.id,
                    confidence: s.confidence / 100
                })));
            } else {
                alert('No students recognized. Please try again or adjust the camera position.');
            }
        } catch (error) {
            console.error('Error processing CCTV stream:', error);
            alert('Error processing CCTV stream. Please check the URL and try again.');
        }
        
        processCctvBtn.disabled = false;
        processCctvBtn.innerHTML = '<i class="fas fa-play mr-2"></i> Process Stream';
    });
}

// Display recognized students from CCTV
function displayCctvRecognizedStudents(students) {
    cctvStudentsTableBody.innerHTML = '';
    
    students.forEach(student => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${student.student_id}</td>
            <td>${student.name}</td>
            <td>${student.roll_number}</td>
            <td>
                <div class="badge badge-${student.confidence > 80 ? 'success' : student.confidence > 60 ? 'warning' : 'error'}">
                    ${student.confidence}%
                </div>
            </td>
        `;
        cctvStudentsTableBody.appendChild(row);
    });
    
    cctvRecognizedStudents.classList.remove('hidden');
}

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
    }
});
