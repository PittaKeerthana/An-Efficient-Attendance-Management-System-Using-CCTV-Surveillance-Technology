import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import config

def send_absence_notification(student_name, student_id, roll_number, subject_name, 
                              date, parent_email, parent_name):
    """Send absence notification email to parent"""
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Absence Alert - {student_name} - {subject_name}"
        msg['From'] = f"{config.EMAIL_FROM_NAME} <{config.EMAIL_FROM_ADDRESS}>"
        msg['To'] = parent_email
        
        # Email body
        text_body = f"""
Dear {parent_name},

This is to inform you that your child {student_name} (Roll No: {roll_number}, ID: {student_id}) 
was marked ABSENT in {subject_name} on {date}.

Please contact the school if you have any concerns.

This is an automated message from the Attendance System.
Please do not reply to this email.

Best regards,
{config.EMAIL_FROM_NAME}
"""
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .header {{
            background-color: #dc2626;
            color: white;
            padding: 15px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }}
        .content {{
            padding: 20px;
            background-color: #f9fafb;
        }}
        .info-box {{
            background-color: white;
            padding: 15px;
            margin: 15px 0;
            border-left: 4px solid #dc2626;
            border-radius: 3px;
        }}
        .footer {{
            text-align: center;
            padding: 15px;
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>⚠️ Absence Alert</h2>
        </div>
        <div class="content">
            <p>Dear <strong>{parent_name}</strong>,</p>
            
            <p>This is to inform you that your child was marked <strong>ABSENT</strong> today.</p>
            
            <div class="info-box">
                <p><strong>Student Name:</strong> {student_name}</p>
                <p><strong>Student ID:</strong> {student_id}</p>
                <p><strong>Roll Number:</strong> {roll_number}</p>
                <p><strong>Subject:</strong> {subject_name}</p>
                <p><strong>Date:</strong> {date}</p>
            </div>
            
            <p>If you have any concerns or questions regarding this absence, 
            please contact the school administration.</p>
            
            <p>Best regards,<br>
            <strong>{config.EMAIL_FROM_NAME}</strong></p>
        </div>
        <div class="footer">
            <p>This is an automated message. Please do not reply to this email.</p>
            <p>&copy; {datetime.now().year} Face Recognition Attendance System</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Attach both text and HTML versions
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email
        server = smtplib.SMTP(config.EMAIL_HOST, config.EMAIL_PORT)
        server.starttls()
        server.login(config.EMAIL_USERNAME, config.EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"Absence notification sent to {parent_email} for {student_name}")
        return True, "Email sent successfully"
        
    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        print(error_msg)
        return False, error_msg

def send_bulk_absence_notifications(absent_students_data):
    """Send absence notifications to multiple parents"""
    results = {
        'sent': 0,
        'failed': 0,
        'errors': []
    }
    
    for student_data in absent_students_data:
        success, message = send_absence_notification(
            student_name=student_data['student_name'],
            student_id=student_data['student_id'],
            roll_number=student_data['roll_number'],
            subject_name=student_data['subject_name'],
            date=student_data['date'],
            parent_email=student_data['parent_email'],
            parent_name=student_data['parent_name']
        )
        
        if success:
            results['sent'] += 1
        else:
            results['failed'] += 1
            results['errors'].append({
                'student': student_data['student_name'],
                'error': message
            })
    
    return results

def test_email_configuration():
    """Test email configuration by sending a test email"""
    try:
        server = smtplib.SMTP(config.EMAIL_HOST, config.EMAIL_PORT)
        server.starttls()
        server.login(config.EMAIL_USERNAME, config.EMAIL_PASSWORD)
        server.quit()
        return True, "Email configuration is working"
    except Exception as e:
        return False, f"Email configuration error: {str(e)}"
