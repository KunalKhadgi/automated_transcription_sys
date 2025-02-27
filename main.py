import os
import whisper
import time
import json
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess

# Set FFmpeg path manually
os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"

# Configuration
WATCH_DIR = "./media"  # Change this to your directory
PROCESSED_FILES = "processed_files.json"
SUPPORTED_FORMATS = {"mp3", "wav", "mp4", "mkv", "mov", "flv", "aac", "m4a"}

def load_processed_files():
    if os.path.exists(PROCESSED_FILES):
        with open(PROCESSED_FILES, "r") as f:
            return json.load(f)
    return {}

def save_processed_files(processed_files):
    with open(PROCESSED_FILES, "w") as f:
        json.dump(processed_files, f, indent=4)

def wait_for_download(file_path, timeout=900, check_interval=5):
    """
    Wait until the file is fully downloaded by checking if its size remains unchanged.
    
    - timeout: Maximum wait time (default: 900s = 15 min)
    - check_interval: Time between file size checks (default: 5s)
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if not os.path.exists(file_path):
            time.sleep(check_interval)  # Wait if file doesn't exist yet
            continue

        initial_size = os.path.getsize(file_path)
        time.sleep(check_interval)

        if os.path.getsize(file_path) == initial_size:
            print(f"✅ File {file_path} has finished downloading.") 
            return True  # File is stable

    print(f"⚠️ Warning: Timeout reached while waiting for {file_path} to finish downloading.")
    return False  # File might still be incomplete

def extract_audio(file_path):
    """Extracts audio from video files if necessary using FFmpeg."""
    ext = file_path.suffix.lower()
    if ext in {".mp4", ".mkv", ".mov", ".flv"}:
        audio_path = file_path.with_suffix(".wav")
        if not audio_path.exists():
            subprocess.run(["ffmpeg", "-i", str(file_path), str(audio_path)], check=True)
        return audio_path
    return file_path

def transcribe_file(file_path, model, processed_files):
    """Transcribes an audio file using Whisper."""
    if file_path in processed_files:
        print(f"Skipping already processed file: {file_path}")
        return
    
    if not wait_for_download(file_path):
        print(f"Skipping file {file_path} due to incomplete download.")
        return
    
    print(f"Processing: {file_path}")
    audio_path = extract_audio(Path(file_path))
    result = model.transcribe(str(audio_path))
    
    # Save transcription
    text_file = Path(file_path).with_suffix(".txt")
    with open(text_file, "w", encoding="utf-8") as f:
        f.write(result["text"])
    
    processed_files[file_path] = text_file.name
    save_processed_files(processed_files)
    print(f"Saved transcription: {text_file}")

def scan_existing_files(model, processed_files):
    """Scans and processes existing media files."""
    for root, _, files in os.walk(WATCH_DIR):
        for file in files:
            if file.split(".")[-1].lower() in SUPPORTED_FORMATS:
                transcribe_file(os.path.join(root, file), model, processed_files)

class FileEventHandler(FileSystemEventHandler):
    def __init__(self, model, processed_files):
        self.model = model
        self.processed_files = processed_files
    
    def on_created(self, event):
        if event.is_directory:
            return
        ext = event.src_path.split(".")[-1].lower()
        if ext in SUPPORTED_FORMATS:
            transcribe_file(event.src_path, self.model, self.processed_files)

if __name__ == "__main__":
    print("Loading Whisper model...")
    model = whisper.load_model("base")  # Change to "small", "medium", or "large" if needed
    processed_files = load_processed_files()
    
    print("Scanning existing files...")
    scan_existing_files(model, processed_files)
    
    print("Starting real-time monitoring...")
    event_handler = FileEventHandler(model, processed_files)
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("🛑 Stopping watchdog...")
        observer.stop()
    observer.join()
    print("✅ Watchdog stopped.")