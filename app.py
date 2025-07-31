# app.py
import pandas as pd
import os
import time
import re
import threading
import pyperclip
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from translators.gpt_translator import translate_with_gpt
from translators.claude_translator import translate_with_claude
from translators.gemini_translator import translate_with_gemini
from fetchers.file_fetcher import get_text_from_file

# --- Configuration ---
JOBS_FEED_CSV_PATH = "monitor/jobs_feed.csv"
PROCESSED_LOG_PATH = "monitor/processed_jobs.log"
UPLOADS_DIR = "uploads"
OUTPUTS_DIR = "outputs"
HANDSHAKE_WAIT_TIME = 30
POLL_INTERVAL = 60

active_handshake_jobs = set()

# --- Helper Functions (Unchanged) ---
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
    print("[INFO] CSV Handshake Worker: Started.")
    while True:
        try:
            if not os.path.exists(JOBS_FEED_CSV_PATH):
                raise FileNotFoundError
            
            df = pd.read_csv(JOBS_FEED_CSV_PATH, sep=',')
            df.columns = [c.strip().lower() for c in df.columns]
            
            if 'link' not in df.columns or 'title' not in df.columns:
                print(f"\n[ERROR] CSV format issue: Required columns ('link', 'title') not found in '{JOBS_FEED_CSV_PATH}'.")
                print(f"[INFO] Columns Found: {list(df.columns)}")
                print(f"[INFO] Waiting {POLL_INTERVAL} seconds...")
                time.sleep(POLL_INTERVAL)
                continue

        except FileNotFoundError:
            print(f"\n[INFO] CSV Worker: Job feed not found at '{JOBS_FEED_CSV_PATH}'. Waiting...")
            time.sleep(POLL_INTERVAL)
            continue
        except Exception as e:
            print(f"\n[ERROR] Pandas could not process the CSV file. Error: {e}")
            print(f"[INFO] Waiting {POLL_INTERVAL} seconds...")
            time.sleep(POLL_INTERVAL)
            continue

        processed_links = get_processed_jobs()
        new_jobs = df[~df['link'].isin(processed_links)].copy()

        if new_jobs.empty:
            time.sleep(POLL_INTERVAL)
            continue
        
        pending_job_ids = {get_job_id_from_link(link) for link in new_jobs['link']}
        pending_job_ids.discard(None)
        if pending_job_ids:
            print(f"\n[INFO] CSV Worker: Found {len(pending_job_ids)} new jobs. Pre-registering IDs.")
            active_handshake_jobs.update(pending_job_ids)

        for _, job in new_jobs.iterrows():
            job_link = job['link']
            job_id = get_job_id_from_link(job_link)
            if not job_id: continue

            print("\n[ALERT] New Job Found! Action Required.")
            pyperclip.copy(job_id)
            print(f"  -> ID:    {job_id} (Copied to clipboard!)")
            print(f"  -> Title: {job['title']}")
            print(f"  -> URL:   {job_link}")
            print(f"  -> Waiting {HANDSHAKE_WAIT_TIME}s for you to download file to '{UPLOADS_DIR}/'")
            time.sleep(HANDSHAKE_WAIT_TIME)

            source_filepath = find_job_file(job_id)
            if source_filepath:
                print(f"[INFO] Found source file: {source_filepath}. Processing with all LLMs...")
                source_text = get_text_from_file(source_filepath)
                source_lang, target_lang = parse_languages(job['title'])

                print("  -> Translating with GPT-4...")
                gpt_translation = translate_with_gpt(source_text, target_lang, source_lang)
                if not gpt_translation.startswith("Error:"):
                    gpt_output_filename = f"job_{job_id}_{target_lang}_gpt.txt"
                    with open(os.path.join(OUTPUTS_DIR, gpt_output_filename), 'w', encoding='utf-8') as f: f.write(gpt_translation)
                    print(f"[SUCCESS] GPT translation saved to {gpt_output_filename}")
                
                print("  -> Translating with Claude...")
                claude_translation = translate_with_claude(source_text, target_lang, source_lang)
                if not claude_translation.startswith("Error:"):
                    claude_output_filename = f"job_{job_id}_{target_lang}_claude.txt"
                    with open(os.path.join(OUTPUTS_DIR, claude_output_filename), 'w', encoding='utf-8') as f: f.write(claude_translation)
                    print(f"[SUCCESS] Claude translation saved to {claude_output_filename}")

                print("  -> Translating with Gemini...")
                gemini_translation = translate_with_gemini(source_text, target_lang, source_lang)
                if not gemini_translation.startswith("Error:"):
                    gemini_output_filename = f"job_{job_id}_{target_lang}_gemini.txt"
                    with open(os.path.join(OUTPUTS_DIR, gemini_output_filename), 'w', encoding='utf-8') as f: f.write(gemini_translation)
                    print(f"[SUCCESS] Gemini translation saved to {gemini_output_filename}")

                log_processed_job(job_link)
                print(f"[INFO] Job ID: {job_id} Finished & Logged.")
            else:
                print(f"[ERROR] Timed out. File for job {job_id} not found.")
                print("[INFO] Assuming job was rejected. Logging to prevent future alerts.")
                log_processed_job(job_link)
            
            active_handshake_jobs.discard(job_id)

# --- Hot Folder Worker ---
class HotFolderHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory: return
        filename = os.path.basename(event.src_path)
        job_id_match = re.match(r'^(\d+)', filename)
        if job_id_match and job_id_match.group(1) in active_handshake_jobs:
            print(f"[INFO] Hot Folder: Ignoring file '{filename}' as it is being handled by the CSV worker.")
            return
        
        print(f"\n[INFO] Hot Folder: Detected new ad-hoc file '{filename}'.")
        base_name = os.path.splitext(filename)[0]
        if '_to_' in base_name:
            parts = base_name.split('_to_')
            target_lang = parts[-1]
            print(f"[INFO] Ad-hoc job detected. Translating to '{target_lang}'...")
            
            source_text = get_text_from_file(event.src_path)
            translation = translate_with_gpt(source_text, target_lang) # Defaulting to GPT for ad-hoc
            
            output_filename = f"{base_name}_translated_gpt.txt"
            with open(os.path.join(OUTPUTS_DIR, output_filename), 'w', encoding='utf-8') as f:
                f.write(translation)
            print(f"[SUCCESS] Ad-hoc translation saved to {output_filename}")

def folder_monitor_worker():
    print("[INFO] Hot Folder Worker: Started.")
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
    csv_thread = threading.Thread(target=csv_handshake_worker)
    folder_thread = threading.Thread(target=folder_monitor_worker, daemon=True)
    
    print("[INFO] Starting Multi-LLM Translation Assistant...")
    csv_thread.start()
    folder_thread.start()
    
    csv_thread.join()
    print("[INFO] Application Shutting Down.")