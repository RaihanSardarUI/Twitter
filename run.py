#!/usr/bin/env python3
"""
Twitter Video Downloader - Launcher Script
Simple script to launch different components of the system
"""

import sys
import os
import subprocess

def print_banner():
    """Print the application banner"""
    print("=" * 60)
    print("🎬 Twitter Video Downloader")
    print("=" * 60)
    print("Choose how to run the application:")
    print()

def print_options():
    """Print available options"""
    options = [
        ("1", "🚀 Full Service (API + Cookie Watcher)", "service_manager.py"),
        ("2", "📡 API Server Only", "main.py"),
        ("3", "🔍 Cookie Watcher Only", "cookie_watcher.py"),
        ("4", "📚 Show API Documentation URLs", None),
        ("5", "🔧 Install Dependencies", None),
        ("q", "❌ Quit", None),
    ]
    
    for key, description, _ in options:
        print(f"  {key}. {description}")
    print()

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import yt_dlp
        import watchdog
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False

def install_dependencies():
    """Install required dependencies"""
    print("🔧 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def show_documentation():
    """Show documentation URLs"""
    print("📚 API Documentation URLs:")
    print("  • Main API: http://localhost:8000")
    print("  • Interactive Docs: http://localhost:8000/docs")
    print("  • Test Endpoint: http://localhost:8000/test")
    print("  • Auth Status: http://localhost:8000/auth/status")
    print()
    print("📋 Quick Test:")
    print("  curl http://localhost:8000/test?url=https://x.com/user/status/123")
    print()

def run_script(script_name):
    """Run a Python script"""
    if not os.path.exists(script_name):
        print(f"❌ Script not found: {script_name}")
        return False
    
    try:
        print(f"🚀 Starting {script_name}...")
        print("⏹️  Press Ctrl+C to stop")
        print("-" * 40)
        subprocess.run([sys.executable, script_name])
        return True
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
        return True
    except Exception as e:
        print(f"❌ Error running {script_name}: {e}")
        return False

def main():
    """Main launcher function"""
    print_banner()
    
    # Check if we're in the right directory
    required_files = ["main.py", "service_manager.py", "cookie_watcher.py", "requirements.txt"]
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print("❌ Missing required files:", ", ".join(missing_files))
        print("Please run this script from the project root directory.")
        return
    
    while True:
        print_options()
        choice = input("Enter your choice: ").strip().lower()
        
        if choice == "q" or choice == "quit":
            print("👋 Goodbye!")
            break
        elif choice == "1":
            if not check_dependencies():
                print("Please install dependencies first (option 5)")
                continue
            run_script("service_manager.py")
        elif choice == "2":
            if not check_dependencies():
                print("Please install dependencies first (option 5)")
                continue
            run_script("main.py")
        elif choice == "3":
            if not check_dependencies():
                print("Please install dependencies first (option 5)")
                continue
            run_script("cookie_watcher.py")
        elif choice == "4":
            show_documentation()
        elif choice == "5":
            install_dependencies()
        else:
            print("❌ Invalid choice. Please try again.")
        
        print()

if __name__ == "__main__":
    main() 