"""
Face Recognition Attendance System - Setup Script
This script helps with initial setup and configuration
"""

import os
import sys
import subprocess

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")

def check_python_version():
    """Check if Python version is compatible"""
    print_header("Checking Python Version")
    
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required!")
        print(f"Current version: {sys.version}")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def install_dependencies():
    """Install required packages"""
    print_header("Installing Dependencies")
    
    print("This may take 5-10 minutes (downloading ML models)...")
    print("Please wait...\n")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("\n✅ All dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("\n❌ Failed to install dependencies!")
        print("Try manually: pip install -r requirements.txt")
        return False

def create_directories():
    """Create necessary directories"""
    print_header("Creating Directories")
    
    directories = [
        'database',
        'models',
        'uploads/temp_images',
        'uploads/temp_videos',
        'static/student_faces'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Created: {directory}")
    
    return True

def configure_email():
    """Help configure email settings"""
    print_header("Email Configuration")
    
    print("For email notifications to work, you need to configure SMTP settings.")
    print("\nFor Gmail:")
    print("1. Enable 2-Factor Authentication in Google Account")
    print("2. Go to: Google Account > Security > App passwords")
    print("3. Generate password for 'Mail'")
    print("4. Copy the 16-character password")
    print("\nDo you want to configure email now? (y/n): ", end='')
    
    choice = input().strip().lower()
    
    if choice == 'y':
        email = input("\nEnter your Gmail address: ").strip()
        password = input("Enter your Gmail App Password: ").strip()
        
        # Read config file
        with open('config.py', 'r') as f:
            config_content = f.read()
        
        # Replace email settings
        config_content = config_content.replace(
            "EMAIL_USERNAME = 'your-email@gmail.com'",
            f"EMAIL_USERNAME = '{email}'"
        )
        config_content = config_content.replace(
            "EMAIL_PASSWORD = 'your-app-password'",
            f"EMAIL_PASSWORD = '{password}'"
        )
        config_content = config_content.replace(
            "EMAIL_FROM_ADDRESS = 'your-email@gmail.com'",
            f"EMAIL_FROM_ADDRESS = '{email}'"
        )
        
        # Write back
        with open('config.py', 'w') as f:
            f.write(config_content)
        
        print("\n✅ Email configured successfully!")
        print("Note: You can change these settings later in config.py")
    else:
        print("\n⚠️  Remember to configure email in config.py before using!")
    
    return True

def create_first_teacher():
    """Ask if user wants to create first teacher account"""
    print_header("Initial Setup Complete!")
    
    print("Setup is complete! Next steps:")
    print("\n1. Run the application:")
    print("   python app.py")
    print("\n2. Open browser and go to:")
    print("   http://localhost:5000")
    print("\n3. Register as a teacher (first time)")
    print("\n4. Follow the Quick Start Guide (QUICKSTART.md)")
    
    print("\n" + "="*60)
    print("Would you like to start the application now? (y/n): ", end='')
    
    choice = input().strip().lower()
    
    if choice == 'y':
        print("\nStarting application...")
        print("Press Ctrl+C to stop the server")
        print("-"*60 + "\n")
        try:
            subprocess.run([sys.executable, "app.py"])
        except KeyboardInterrupt:
            print("\n\nApplication stopped.")
    
    return True

def main():
    """Main setup function"""
    print("\n" + "="*60)
    print("  Face Recognition Attendance System - Setup")
    print("="*60)
    
    # Check Python version
    if not check_python_version():
        return
    
    # Install dependencies
    if not install_dependencies():
        return
    
    # Create directories
    if not create_directories():
        return
    
    # Configure email
    if not configure_email():
        return
    
    # Final steps
    create_first_teacher()
    
    print("\n✅ Setup completed successfully!")
    print("\nFor detailed instructions, see:")
    print("  - QUICKSTART.md (quick guide)")
    print("  - README.md (full documentation)")
    print("\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error during setup: {str(e)}")
        print("Please check the error and try again.")
