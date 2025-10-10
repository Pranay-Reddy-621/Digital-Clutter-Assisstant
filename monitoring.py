## Updated monitoring.py
import time
import os
import win32gui
import win32process
import psutil
import json
from pathlib import Path
from watchdog.observers import Observer 
from watchdog.events import FileSystemEventHandler
from next_action import get_next_action
from file_deleter import delete_file
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from compress_extract import compress_file,extract_file
from file_crypto import encrypt_file
processed_files = set()

# Add near the top of monitoring.py
def load_processed_files():
    """Load processed files from shared file"""
    global processed_files
    try:
        with open('processed_files.json', 'r') as f:
            file_list = json.load(f)
            # Update set with file list
            processed_files.update(file_list)
    except (FileNotFoundError, json.JSONDecodeError):
        pass  # File doesn't exist yet or is empty



def check_scheduled_deletions():
    print("[!] Checking scheduled deletions...")
    now = datetime.now()
    
    try:
        with open('files_to_be_deleted.txt', 'r') as f:
            scheduled = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "error"

    deleted_files = []
    
    for filepath, date_str in scheduled.items():
        try:
            deletion_date = datetime.fromisoformat(date_str)
            if now >= deletion_date:
                if delete_file(filepath):
                    deleted_files.append(filepath)
        except Exception as e:
            print(f"[x] Error processing {filepath}: {str(e)}")
    
    # Update schedule file
    for filepath in deleted_files:
        del scheduled[filepath]
    
    with open('files_to_be_deleted.txt', 'w') as f:
        json.dump(scheduled, f, indent=2)

def get_active_window_info():
    """Get active window process name and title"""
    hwnd = win32gui.GetForegroundWindow()
    pid = win32process.GetWindowThreadProcessId(hwnd)[-1]
    try:
        process = psutil.Process(pid)
        return {
            'process_name': process.name(),
            'window_title': win32gui.GetWindowText(hwnd)
        }
    except psutil.NoSuchProcess:
        return {'process_name': 'unknown', 'window_title': ''}
    
from datetime import timedelta

def parse_time_delta(time_str):
    value, unit = time_str.split()
    value = int(value)
    
    # Normalize unit by stripping trailing 's' if it's plural
    unit = unit.lower().rstrip('s')
    
    # Map normalized unit to timedelta argument
    unit_map = { 
        'day': 'days',
        'hour': 'hours',
        'minute': 'minutes',
        'second': 'seconds'
    }
    
    if unit not in unit_map:
        raise ValueError(f"Unsupported time unit: {unit}")
    
    return timedelta(**{unit_map[unit]: value})



class FileHandler(FileSystemEventHandler):
    def on_created(self, event):
        global processed_files
        if not event.is_directory:

            filepath = event.src_path

            if filepath in processed_files:
                return
            
            print(f"[+] New File detected: {filepath}")
            processed_files.add(filepath)
            try:
            # Wait for file to be fully written
                for _ in range(5):  # Retry 5 times
                    try:
                        with open(filepath, 'rb') as f:
                            break
                    except IOError:
                        time.sleep(0.5)
                else:
                    print(f"[x] File inaccessible: {filepath}")
                    return

                # Get window context before moving file
                window_info = get_active_window_info()
                
                # Add metadata to filename
                new_path = self.add_metadata_to_filename(filepath, window_info)
                
                processed_files.add(new_path)

                action = get_next_action(new_path,window_info)

                final_path = new_path

                if action['type'] == 'compress':
                     self.record_compress_action(new_path)
                elif action['type'] == 'extract':
                    self.record_extract_action(new_path)
                elif action['type'] in ['move', 'copy']:
                    self.record_pending_action(new_path, action)
                elif action['type'] == 'encrypt':
                   self.record_encrypt_action(new_path)
                elif action['type'] == 'decrypt':
                    self.record_decrypt_action(new_path)
                elif action['type'] == 'delete' and action.get('time'):
                    try:
                        delta = parse_time_delta(action['time'])
                        deletion_date = datetime.now() + delta
                        
                        # Update deletion schedule
                        try:
                            with open('files_to_be_deleted.txt', 'r') as f:
                                scheduled = json.load(f)
                        except (FileNotFoundError, json.JSONDecodeError):
                            scheduled = {}
                        
                        scheduled[final_path] = deletion_date.isoformat()
                        
                        with open('files_to_be_deleted.txt', 'w') as f:
                            json.dump(scheduled, f, indent=2)
                        
                        print(f"[✓] Scheduled deletion for {final_path} on {deletion_date}")
                        
                    except Exception as e:
                        print(f"[x] Deletion scheduling failed: {str(e)}")
                elif action['type'] == 'no_action':
                    print(f"[!] No matching rules for {new_path}")
                else:
                    print(f"[x] Unknown action type: {action['type']}")
            except:
                print(f"[x] Critical error processing {filepath}: {str(e)}")


    def record_encrypt_action(self, filepath):
        self._record_action('encrypt_actions.json', filepath)

    def record_decrypt_action(self, filepath):
        self._record_action('decrypt_actions.json', filepath)

    def record_compress_action(self, filepath):
        self._record_action('compress_actions.json', filepath)

    def record_extract_action(self, filepath):
        self._record_action('extract_actions.json', filepath)
    
    def _record_action(self, filename, filepath):
        try:
            with open(filename, 'r') as f:
                actions = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            actions = []
            
        actions.append(filepath)
        
        with open(filename, 'w') as f:
            json.dump(actions, f, indent=2)
        
        print(f"[✓] Recorded {filename.split('_')[0]} action for {filepath}")

    def record_pending_action(self, filepath, action):
        """Save proposed moves/copies for user approval"""
        try:
            # Load existing pending actions
            try:
                with open('pending_actions.json', 'r') as f:
                    pending = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pending = []
                
            # Add new action
            pending.append({
                "original_path": filepath,
                "target_path": action.get('target'),
                "type": action['type'],
                "timestamp": datetime.now().isoformat()
            })
            
            # Save back to file
            with open('pending_actions.json', 'w') as f:
                json.dump(pending, f, indent=2)
                
            print(f"[✓] Recorded pending {action['type']} for {filepath}")
            
        except Exception as e:
            print(f"[x] Failed to record action: {str(e)}")
    
    def add_metadata_to_filename(self, path, info):
        """Safer filename tagging with retries"""
        original_path = path
        for attempt in range(3):
            try:
                base, ext = os.path.splitext(path)
                clean_title = info['window_title'].replace(' ','_')[:50]
                
                #cleaning title
                invalid_chars = r'\/:*?"<>|'
                for char in invalid_chars:
                    clean_title = clean_title.replace(char, '_')

                clean_title = clean_title[:50]
                new_name = f"{base}_APP-{info['process_name']}_TITLE-{clean_title}{ext}"
                os.rename(path, new_name)
                return new_name
            except Exception as e:
                print(f"[x] Rename failed (attempt {attempt+1}): {str(e)}")
                time.sleep(0.5)
        return original_path  # Return original if all retries fail



def start_monitoring(folders_to_watch):
    observers = []                                                                          

    for folder in folders_to_watch:
        if os.path.exists(folder):
            observer = Observer()
            observer.schedule(FileHandler(), path=folder, recursive=False)
            observer.start()
            observers.append(observer)
            print(f"[✓] Monitoring started on: {folder}", flush=True)
        else:
            print(f"[x] Folder not found: {folder}", flush=True)
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_scheduled_deletions, 'interval', seconds=30)
    scheduler.add_job(load_processed_files, 'interval', seconds=5)

    scheduler.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        for obs in observers:
            obs.stop()
        for obs in observers:
            obs.join()

if __name__ == "__main__":
    user_path = str(Path.home())
    folders = [
        r"C:\Users\g6msd\OneDrive\Pictures\Screenshots",
        r"C:\Users\g6msd\Downloads"
        # Add or remove as needed
    ]

    start_monitoring(folders)
