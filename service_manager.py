import os
import subprocess
import threading
import time
import signal
import sys
from cookie_watcher import start_cookie_watcher

class ServiceManager:
    """Manage both API server and cookie watcher"""
    
    def __init__(self):
        self.api_process = None
        self.watcher_thread = None
        self.running = True
        
    def start_api_server(self):
        """Start the FastAPI server"""
        try:
            print("🚀 Starting FastAPI server...")
            self.api_process = subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Monitor API output
            def monitor_api():
                while self.running and self.api_process:
                    try:
                        line = self.api_process.stdout.readline()
                        if line:
                            print(f"[API] {line.strip()}")
                        elif self.api_process.poll() is not None:
                            break
                    except:
                        break
            
            threading.Thread(target=monitor_api, daemon=True).start()
            time.sleep(2)  # Give server time to start
            print("✅ FastAPI server started on http://localhost:8000")
            
        except Exception as e:
            print(f"❌ Error starting API server: {e}")
    
    def start_cookie_watcher(self):
        """Start the cookie file watcher"""
        try:
            print("🔍 Starting Cookie File Watcher...")
            
            def watcher_worker():
                try:
                    start_cookie_watcher('.')
                except Exception as e:
                    if self.running:
                        print(f"❌ Cookie watcher error: {e}")
            
            self.watcher_thread = threading.Thread(target=watcher_worker, daemon=True)
            self.watcher_thread.start()
            print("✅ Cookie File Watcher started")
            
        except Exception as e:
            print(f"❌ Error starting cookie watcher: {e}")
    
    def stop_services(self):
        """Stop all services"""
        print("\n🛑 Stopping services...")
        self.running = False
        
        if self.api_process:
            try:
                self.api_process.terminate()
                self.api_process.wait(timeout=5)
                print("✅ API server stopped")
            except:
                try:
                    self.api_process.kill()
                    print("⚠️ API server force stopped")
                except:
                    pass
        
        print("✅ All services stopped")
    
    def run(self):
        """Main run method"""
        print("=" * 60)
        print("🎬 Twitter Video Downloader - Full Service")
        print("=" * 60)
        
        # Setup signal handlers
        def signal_handler(signum, frame):
            self.stop_services()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Start services
            self.start_api_server()
            time.sleep(1)
            self.start_cookie_watcher()
            
            print("\n" + "=" * 60)
            print("🎉 ALL SERVICES RUNNING!")
            print("=" * 60)
            print("📡 API Server: http://localhost:8000")
            print("📚 API Docs: http://localhost:8000/docs") 
            print("🔍 Cookie Watcher: Active")
            print("\n📋 COOKIE USAGE:")
            print("   1. Export cookies from your browser")
            print("   2. Save as raw_cookies.json in this folder")
            print("   3. File will auto-convert to cookies.txt")
            print("   4. API will use new cookies automatically")
            print("\n🔞 ADULT CONTENT:")
            print("   • Set is_adult_content: true in API requests")
            print("   • Upload Twitter/X cookies for access")
            print("\n⏹️  Press Ctrl+C to stop all services")
            print("=" * 60)
            
            # Keep running
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_services()

if __name__ == "__main__":
    manager = ServiceManager()
    manager.run() 