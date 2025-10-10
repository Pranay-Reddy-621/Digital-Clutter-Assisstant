import zipfile
import os
from pathlib import Path

def compress_file(file_path, output_dir):
  """Compress file to ZIP archive"""

  try:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    file_name = os.path.basename(file_path)
    zip_path = os.path.join(output_dir, f"{os.path.splitext(file_name)[0]}.zip")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
      zipf.write(file_path, arcname=file_name)

    print(f"[✓] Compressed {file_path} to {zip_path}")
    return str(zip_path)
  
  except Exception as e:
        print(f"[x] Compression failed: {str(e)}")
        return None
  

def extract_file(zip_path, output_dir):
    """Extract ZIP archive contents"""
    try:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(output_dir)
            
        print(f"[✓] Extracted {zip_path} to {output_dir}")
        return str(output_dir)
    except Exception as e:
        print(f"[x] Extraction failed: {str(e)}")
        return None