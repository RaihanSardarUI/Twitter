import os
import json
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def convert_raw_cookies_to_netscape(raw_cookies_path: str, output_path: str = 'cookies.txt') -> bool:
    """Convert raw_cookies.json to Netscape format cookies.txt"""
    try:
        with open(raw_cookies_path, 'r', encoding='utf-8') as f:
            cookies_data = json.load(f)
        
        # Handle both direct array and object with cookies property
        if isinstance(cookies_data, dict) and 'cookies' in cookies_data:
            cookies = cookies_data['cookies']
        elif isinstance(cookies_data, list):
            cookies = cookies_data
        else:
            print("❌ Invalid cookie format. Expected array or object with 'cookies' property")
            return False
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Netscape HTTP Cookie File\n")
            f.write("# This is a generated file! Do not edit.\n\n")
            
            cookie_count = 0
            for cookie in cookies:
                domain = cookie.get('domain', '')
                # Handle both x.com and twitter.com domains
                if domain and not domain.startswith('.'):
                    domain = '.' + domain
                
                flag = 'TRUE' if domain.startswith('.') else 'FALSE'
                path = cookie.get('path', '/')
                secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
                
                # Handle expiration date safely
                expiration_raw = cookie.get('expirationDate', cookie.get('expires', 0))
                try:
                    expiration = str(int(float(expiration_raw))) if expiration_raw else '0'
                except (ValueError, TypeError):
                    expiration = '0'
                
                name = cookie.get('name', '')
                value = cookie.get('value', '')
                
                if name and value and domain:  # Only save valid cookies
                    # Save for x.com domain
                    f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}\n")
                    cookie_count += 1
                    
                    # Also save for twitter.com domain for compatibility
                    if 'x.com' in domain:
                        twitter_domain = domain.replace('x.com', 'twitter.com')
                        f.write(f"{twitter_domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}\n")
                        cookie_count += 1
        
        print(f"✅ Converted {len(cookies)} cookies to {output_path}")
        print(f"📊 Total cookie entries saved: {cookie_count}")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error converting cookies: {e}")
        return False

class CookieFileHandler(FileSystemEventHandler):
    """Handle file system events for cookie files"""
    
    def __init__(self):
        self.processed_files = set()
        self.last_processed = {}
    
    def on_created(self, event):
        if not event.is_directory:
            self.handle_file_event(event.src_path, "created")
    
    def on_modified(self, event):
        if not event.is_directory:
            self.handle_file_event(event.src_path, "modified")
    
    def handle_file_event(self, file_path, event_type):
        """Handle cookie file events"""
        filename = os.path.basename(file_path)
        
        # Only process raw_cookies.json files
        if filename.lower() != 'raw_cookies.json':
            return
        
        # Prevent duplicate processing
        current_time = time.time()
        if file_path in self.last_processed:
            if current_time - self.last_processed[file_path] < 2:  # 2-second cooldown
                return
        
        self.last_processed[file_path] = current_time
        
        # Wait a moment for file write to complete
        time.sleep(0.5)
        
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            print(f"\n🔍 Cookie file {event_type}: {filename}")
            
            success = convert_raw_cookies_to_netscape(file_path)
            if success:
                print("✅ Cookies are now ready for use!")
                print("🎯 API will automatically use new cookies for requests")
                
                # Optionally remove the raw file after successful conversion
                try:
                    os.remove(file_path)
                    print(f"🗑️  Cleaned up {filename}")
                except:
                    pass
            else:
                print("❌ Cookie conversion failed - please check file format")

def start_cookie_watcher(watch_directory: str = '.'):
    """Start watching for cookie files in the specified directory"""
    print(f"🔍 Starting cookie file watcher in: {os.path.abspath(watch_directory)}")
    print("📁 Watching for: raw_cookies.json")
    print("🔄 Auto-convert to: cookies.txt")
    
    # Check for existing raw_cookies.json on startup
    raw_cookies_path = os.path.join(watch_directory, 'raw_cookies.json')
    if os.path.exists(raw_cookies_path):
        print(f"\n🔍 Found existing {raw_cookies_path}")
        success = convert_raw_cookies_to_netscape(raw_cookies_path)
        if success:
            print("✅ Existing cookies converted successfully!")
            try:
                os.remove(raw_cookies_path)
                print("🗑️  Cleaned up raw_cookies.json")
            except:
                pass
    
    # Setup file watcher
    event_handler = CookieFileHandler()
    observer = Observer()
    observer.schedule(event_handler, watch_directory, recursive=False)
    
    try:
        observer.start()
        print("✅ Cookie file watcher is active")
        print("💡 Drop raw_cookies.json into this folder to auto-convert")
        
        # Keep the watcher running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Cookie watcher stopped")
        observer.stop()
    except Exception as e:
        print(f"❌ Cookie watcher error: {e}")
        observer.stop()
    
    observer.join()

if __name__ == "__main__":
    start_cookie_watcher() 