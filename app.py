import pandas as pd
import os
import time
import re
import threading
import pyperclip
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from regenerators.docx_regenerator import create_docx_from_text
from translators.gpt_translator import translate_with_gpt
from translators.claude_translator import translate_with_claude
from translators.gemini_translator import translate_with_gemini
from fetchers.file_fetcher import get_text_from_file

from config import DUMMY_MODE
from translators.dummy_translator import (
    dummy_translate_with_gpt,
    dummy_translate_with_claude,
    dummy_translate_with_gemini
)

# --- DUMMY MODE SWITCH ---
if DUMMY_MODE:
    print("[ALERT] DUMMY MODE IS ACTIVE. NO REAL API CALLS WILL BE MADE.")
    translate_with_gpt = dummy_translate_with_gpt
    translate_with_claude = dummy_translate_with_claude
    translate_with_gemini = dummy_translate_with_gemini

# --- Configuration ---
JOBS_FEED_CSV_PATH = "monitor/jobs_feed.csv"
PROCESSED_LOG_PATH = "monitor/processed_jobs.log"
UPLOADS_DIR = "uploads"
OUTPUTS_DIR = "outputs"
HANDSHAKE_WAIT_TIME = 30
POLL_INTERVAL = 60

active_handshake_jobs = set()

# --- Helper Functions ---
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
                print(f"[INFO] Found source file: {source_filepath}. Processing with all LLMs in parallel...")
                source_text = get_text_from_file(source_filepath)
                source_lang, target_lang = parse_languages(job['title'])
                translations = {}
                threads = []
                def run_translation(service, func):
                    print(f"  -> Starting translation with {service}...")
                    translations[service] = func(source_text, target_lang, source_lang)
                    print(f"  -> Finished translation with {service}.")
                gpt_thread = threading.Thread(target=run_translation, args=("gpt", translate_with_gpt))
                claude_thread = threading.Thread(target=run_translation, args=("claude", translate_with_claude))
                gemini_thread = threading.Thread(target=run_translation, args=("gemini", translate_with_gemini))
                threads.extend([gpt_thread, claude_thread, gemini_thread])
                for t in threads: t.start()
                for t in threads: t.join()
                print("[INFO] All translations complete. Saving results...")

                # Save results from the completed translations
                for service, result in translations.items():
                    if result and not result.startswith("Error:"):
                        # --- NEW REGENERATION LOGIC ---
                        if source_filepath.endswith('.docx'):
                            output_filename = f"job_{job_id}_{target_lang}_{service}.docx"
                            output_path = os.path.join(OUTPUTS_DIR, output_filename)
                            # Call the regenerator instead of writing a .txt
                            regen_status = create_docx_from_text(source_filepath, result, output_path)
                            if regen_status.startswith("Error:"):
                                print(f"[ERROR] {service.capitalize()}: {regen_status}")
                            else:
                                print(f"[SUCCESS] {service.capitalize()} translation regenerated to {output_filename}")
                        else: # Fallback for .txt files
                            output_filename = f"job_{job_id}_{target_lang}_{service}.txt"
                            output_path = os.path.join(OUTPUTS_DIR, output_filename)
                            with open(output_path, 'w', encoding='utf-8') as f:
                                f.write(result)
                            print(f"[SUCCESS] {service.capitalize()} translation saved to {output_filename}")
                        # --- END NEW REGENERATION LOGIC ---
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
            source_text = get_text_from_file(event.src_path)
            print(f"[INFO] Ad-hoc job detected. Translating to '{target_lang}' with all LLMs in parallel...")
            translations = {}
            threads = []
            def run_translation(service, func):
                print(f"  -> Starting ad-hoc translation with {service}...")
                translations[service] = func(source_text, target_lang)
                print(f"  -> Finished ad-hoc translation with {service}.")
            gpt_thread = threading.Thread(target=run_translation, args=("gpt", translate_with_gpt))
            claude_thread = threading.Thread(target=run_translation, args=("claude", translate_with_claude))
            gemini_thread = threading.Thread(target=run_translation, args=("gemini", translate_with_gemini))
            threads.extend([gpt_thread, claude_thread, gemini_thread])
            for t in threads: t.start()
            for t in threads: t.join()
            print("[INFO] All ad-hoc translations complete. Saving results...")
            success_count = 0
            for service, result in translations.items():
                if result and not result.startswith("Error:"):
                    output_filename = f"{base_name}_translated_{service}.txt"
                    with open(os.path.join(OUTPUTS_DIR, output_filename), 'w', encoding='utf-8') as f:
                        f.write(result)
                    print(f"[SUCCESS] {service.capitalize()} ad-hoc translation saved to {output_filename}")
                    success_count += 1
            if success_count == 0:
                print("[ERROR] All translation services failed for the ad-hoc job.")

# --- THIS FUNCTION WAS MISSING ---
def folder_monitor_worker():
    """Initializes and runs the watchdog observer."""
    print("[INFO] Hot Folder Worker: Started.")
    observer = Observer()
    observer.schedule(HotFolderHandler(), UPLOADS_DIR, recursive=False)
    observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
# --- END MISSING FUNCTION ---

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
