# file_deleter.py
import os
import send2trash 

def delete_file(filepath):
    """Safely delete file with backup option"""
    try:
        if os.path.exists(filepath):
            send2trash.send2trash(filepath)
            print(f"[✓] Sent to recycle bin: {filepath}")
            return True
        return False 
    except Exception as e:
        print(f"[x] Deletion failed: {str(e)}")
        return False

