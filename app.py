import pandas as pd
import os
import time
import re
import threading
import pyperclip 
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from translators.gpt_translator import translate_with_gpt
from fetchers.file_fetcher import get_text_from_file

# --- Configuration ---
JOBS_FEED_CSV_PATH = "monitor/jobs_feed.csv"
PROCESSED_LOG_PATH = "monitor/processed_jobs.log"
UPLOADS_DIR = "uploads"
OUTPUTS_DIR = "outputs"
HANDSHAKE_WAIT_TIME = 30  # Seconds to wait for manual download
POLL_INTERVAL = 60         # Seconds to wait before re-checking the CSV

# A shared set to prevent the folder watcher from processing a file meant for the CSV handshake
active_handshake_jobs = set()

# --- Helper Functions (largely unchanged) ---
def parse_languages(title: str) -> (str, str):
    match = re.search(r'([\w\s]+)/([\w\s]+)', title)
    return (match.group(1).strip(), match.group(2).strip()) if match else (None, None)

def get_job_id_from_link(link: str) -> str:
    match = re.search(r'/(\d+)', link)
    return match.group(1) if match else None

def get_processed_jobs() -> set:
    if not os.path.exists(PROCESSED_LOG_PATH): return set()
    with open(PROCESSED_LOG_PATH, 'r', encoding='utf-8') as f:
        return {line.strip() for line in f}

def log_processed_job(job_link: str):
    with open(PROCESSED_LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(job_link + '\n')

def find_job_file(job_id: str) -> str:
    if not os.path.exists(UPLOADS_DIR): return None
    for filename in os.listdir(UPLOADS_DIR):
        if filename.startswith(job_id):
            return os.path.join(UPLOADS_DIR, filename)
    return None

# --- Main Worker for CSV Handshake Workflow ---
def csv_handshake_worker():
    """Monitors the CSV, alerts user, and waits for file drop."""
    print("🚀 CSV Handshake Worker: Started.")
    while True:
        try:
            df = pd.read_csv(JOBS_FEED_CSV_PATH, sep='\t')
            df.columns = df.columns.str.strip()
        except FileNotFoundError:
            time.sleep(POLL_INTERVAL)
            continue

        processed_links = get_processed_jobs()
        new_jobs = df[~df['link'].isin(processed_links)].copy()

        if new_jobs.empty:
            time.sleep(POLL_INTERVAL)
            continue

        for _, job in new_jobs.iterrows():
            job_link = job['link']
            job_id = get_job_id_from_link(job_link)
            if not job_id: continue

            # Add to the shared set so the folder watcher ignores this ID for now
            active_handshake_jobs.add(job_id)

            # --- ACTION REQUIRED BLOCK ---
            print("\n--- ❗ ACTION REQUIRED: New Job Found! ---")
            pyperclip.copy(job_id)  # <-- COPY JOB ID TO CLIPBOARD
            print(f"  ID:    {job_id} (Copied to clipboard!)")
            print(f"  Title: {job['title']}")
            print(f"  URL:   {job_link}")
            print(f"  Waiting {HANDSHAKE_WAIT_TIME}s for you to download the file into '{UPLOADS_DIR}/'")
            print(f"  (The filename must start with '{job_id}')")
            time.sleep(HANDSHAKE_WAIT_TIME)

            source_filepath = find_job_file(job_id)

            if source_filepath:
                # --- File Found: Process It ---
                print(f"-> ✅ Found: {source_filepath}. Processing...")
                source_text = get_text_from_file(source_filepath)
                source_lang, target_lang = parse_languages(job['title'])
                translation = translate_with_gpt(source_text, target_lang, source_lang)
                
                output_filename = f"job_{job_id}_{target_lang}_gpt.txt"
                with open(os.path.join(OUTPUTS_DIR, output_filename), 'w', encoding='utf-8') as f:
                    f.write(translation)

                print(f"-> ✔️ Success! Translation saved to {output_filename}")
                log_processed_job(job_link) # Log as successfully completed
            else:
                # --- File Not Found: Assume Rejected ---
                print(f"-> ❌ Timed out. File for job {job_id} not found.")
                print("   Assuming job was rejected. Logging to prevent future alerts.")
                log_processed_job(job_link) # Log to ignore in the future

            # Clean up the job from the active set
            active_handshake_jobs.remove(job_id)

# --- Worker for Hot Folder Workflow ---
class HotFolderHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory: return

        filename = os.path.basename(event.src_path)
        job_id_match = re.match(r'^(\d+)', filename)
        
        # If the file starts with an ID that is part of an active handshake, ignore it.
        if job_id_match and job_id_match.group(1) in active_handshake_jobs:
            print(f"Hot Folder: Ignoring '{filename}', as it's part of an active CSV job.")
            return

        print(f"\n🔥 Hot Folder: Detected new file '{filename}'")
        
        # Logic for "adhoc" files, e.g., 'my_report_to_Japanese.txt'
        base_name = os.path.splitext(filename)[0]
        if '_to_' in base_name:
            parts = base_name.split('_to_')
            target_lang = parts[-1]
            print(f"-> Adhoc job detected. Translating to '{target_lang}'...")

            source_text = get_text_from_file(event.src_path)
            translation = translate_with_gpt(source_text, target_lang)
            
            output_filename = f"{base_name}_translated_gpt.txt"
            with open(os.path.join(OUTPUTS_DIR, output_filename), 'w', encoding='utf-8') as f:
                f.write(translation)
            print(f"-> ✔️ Success! Adhoc translation saved to {output_filename}")


def folder_monitor_worker():
    """Initializes and runs the watchdog observer."""
    print("🚀 Hot Folder Worker: Started.")
    observer = Observer()
    observer.schedule(HotFolderHandler(), UPLOADS_DIR, recursive=False)
    observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# --- Main Thread Orchestrator ---
if __name__ == "__main__":
    for d in [UPLOADS_DIR, OUTPUTS_DIR, "monitor"]:
        if not os.path.exists(d): os.makedirs(d)

    # Create threads
    csv_thread = threading.Thread(target=csv_handshake_worker)
    folder_thread = threading.Thread(target=folder_monitor_worker, daemon=True) # Daemon so it exits when main does

    print("--- Starting Multi-LLM Translation Assistant ---")
    
    # Start threads
    csv_thread.start()
    folder_thread.start()

    # Wait for the main CSV thread to complete
    csv_thread.join()
    print("--- Application Shutting Down ---")