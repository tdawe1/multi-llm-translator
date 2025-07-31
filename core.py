import pandas as pd
import os
import time
import re
import threading
import pyperclip
import logging
import importlib
import config
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- Imports from our own project modules ---
from fetchers.file_fetcher import get_text_from_file
from translators.gpt_translator import translate_with_gpt, critique_with_gpt
from translators.claude_translator import translate_with_claude, critique_with_claude
from translators.gemini_translator import translate_with_gemini, critique_with_gemini
from regenerators.docx_regenerator import create_docx_from_text
from regenerators.pptx_regenerator import create_pptx_from_text
from regenerators.xlsx_regenerator import create_xlsx_from_text
from config import (
    OPERATION_MODE, 
    PRIMARY_MODEL,
    DEFAULT_SOURCE_LANGUAGE, 
    DEFAULT_TARGET_LANGUAGE,
    UI_RELOAD_SIGNAL_PATH
)

# --- Get a logger instance ---
logger = logging.getLogger(__name__)

# --- Configuration & State ---
JOBS_FEED_CSV_PATH = "monitor/jobs_feed.csv"
PROCESSED_LOG_PATH = "monitor/processed_jobs.log"
HOTFOLDER_MANIFEST_PATH = "monitor/hotfolder_manifest.log"
UPLOADS_DIR = "uploads"
OUTPUTS_DIR = "outputs"
HANDSHAKE_WAIT_TIME = 30
POLL_INTERVAL = 60
active_handshake_jobs = set()

# --- Helper Functions ---
def parse_languages(title: str) -> tuple[str, str] | tuple[None, None]:
    match = re.search(r'([\w\s]+)/([\w\s]+)', title)
    return (match.group(1).strip(), match.group(2).strip()) if match else (None, None)

def get_job_id_from_link(link: str) -> str | None:
    match = re.search(r'/(\d+)', link)
    return match.group(1) if match else None

def get_processed_jobs() -> set:
    if not os.path.exists(PROCESSED_LOG_PATH): return set()
    with open(PROCESSED_LOG_PATH, 'r', encoding='utf-8') as f: return {line.strip() for line in f}

def log_processed_job(job_link: str):
    with open(PROCESSED_LOG_PATH, 'a', encoding='utf-8') as f: f.write(job_link + '\n')

def find_job_file(job_id: str) -> str | None:
    if not os.path.exists(UPLOADS_DIR): return None
    for filename in os.listdir(UPLOADS_DIR):
        if filename.startswith(job_id): return os.path.join(UPLOADS_DIR, filename)
    return None

def save_translation_output(source_filepath: str, service: str, result: str, job_id: str | None = None):
    """A helper function to handle saving files in various formats."""
    base_name = os.path.splitext(os.path.basename(source_filepath))[0]
    if job_id: base_name = f"job_{job_id}"
    original_extension = os.path.splitext(source_filepath)[1]
    REGENERATORS = {'.docx': create_docx_from_text, '.pptx': create_pptx_from_text, '.xlsx': create_xlsx_from_text}
    regenerator_func = REGENERATORS.get(original_extension)
    if regenerator_func:
        output_filename = f"{base_name}_{service}{original_extension}"
        status = regenerator_func(source_filepath, result, os.path.join(OUTPUTS_DIR, output_filename))
        if status.startswith("Error:"): logger.error(f"[{base_name}] {service.capitalize()}: {status}")
        else: logger.info(f"-> [{base_name}] {service.capitalize()} translation regenerated to {output_filename}")
    else:
        output_filename = f"{base_name}_{service}.txt"
        with open(os.path.join(OUTPUTS_DIR, output_filename), 'w', encoding='utf-8') as f: f.write(result)
        logger.info(f"-> [{base_name}] {service.capitalize()} translation saved to {output_filename}")

# --- Core Processing Logic ---
def process_csv_job(job: pd.Series, source_filepath: str):
    """Orchestrates the full translation workflow for a job from the CSV."""
    job_id = get_job_id_from_link(job['link'])
    logger.info(f"[Job {job_id}] Found source file: {source_filepath}")
    source_text = get_text_from_file(source_filepath)
    source_lang, target_lang = parse_languages(job['title'])
    models = {"gpt": {"translate": translate_with_gpt, "critique": critique_with_gpt}, "claude": {"translate": translate_with_claude, "critique": critique_with_claude}, "gemini": {"translate": translate_with_gemini, "critique": critique_with_gemini}}

    if OPERATION_MODE == 'SIMPLE':
        logger.info(f"[Job {job_id}] Running SIMPLE translation with {PRIMARY_MODEL}...")
        translation = models[PRIMARY_MODEL]['translate'](source_text, target_lang, source_lang)
        if not translation.startswith("Error:"): save_translation_output(source_filepath, PRIMARY_MODEL, translation, job_id); logger.info(f"[Job {job_id}] Processing complete. 1/1 task succeeded.")
        else: logger.error(f"[Job {job_id}] Processing failed. 0/1 task succeeded.")
    
    elif OPERATION_MODE == 'PARALLEL':
        logger.info(f"[Job {job_id}] Running PARALLEL translation...")
        translations = {}; threads = []
        def run_translation(service, func): translations[service] = func(source_text, target_lang, source_lang)
        for name, funcs in models.items():
            thread = threading.Thread(target=run_translation, args=(name, funcs['translate'])); threads.append(thread); thread.start()
        for thread in threads: thread.join()
        success_count = sum(1 for r in translations.values() if not r.startswith("Error:"))
        for service, result in translations.items():
            if not result.startswith("Error:"): save_translation_output(source_filepath, service, result, job_id)
        if success_count == len(models): logger.info(f"[Job {job_id}] Processing complete. All {len(models)} translations succeeded.")
        else: logger.warning(f"[Job {job_id}] Processing complete with partial success. Succeeded: {success_count}/{len(models)}.")

    elif OPERATION_MODE == 'CRITIQUE':
        logger.info(f"[Job {job_id}] Running CRITIQUE with primary model {PRIMARY_MODEL}...")
        primary_translation = models[PRIMARY_MODEL]['translate'](source_text, target_lang, source_lang)
        if primary_translation.startswith("Error:"): logger.error(f"[Job {job_id}] Primary translation failed. Aborting critique.")
        else:
            logger.info(f"[Job {job_id}] Primary translation complete. Generating critiques...")
            critiques = {}; threads = []
            reviewer_models = {k: v for k, v in models.items() if k != PRIMARY_MODEL}
            def run_critique(service, func): critiques[service] = func(source_text, primary_translation, target_lang, source_lang)
            for name, funcs in reviewer_models.items():
                thread = threading.Thread(target=run_critique, args=(name, funcs['critique'])); threads.append(thread); thread.start()
            for thread in threads: thread.join()
            success_count = sum(1 for c in critiques.values() if not c.startswith("Error:"))
            final_report = f"--- SOURCE TEXT ---\n{source_text}\n\n--- PRIMARY TRANSLATION ({PRIMARY_MODEL.upper()}) ---\n{primary_translation}\n\n"
            for service, critique_text in critiques.items(): final_report += f"--- CRITIQUE & REFINEMENT ({service.upper()}) ---\n{critique_text}\n\n"
            with open(os.path.join(OUTPUTS_DIR, f"job_{job_id}_CRITIQUE_REPORT.md"), 'w', encoding='utf-8') as f: f.write(final_report)
            logger.info(f"[Job {job_id}] Critique report generated with {success_count}/{len(reviewer_models)} successful reviews.")
    
    log_processed_job(job['link']); logger.info(f"[Job {job_id}] Finished & Logged.")

    with open(UI_RELOAD_SIGNAL_PATH, 'w') as f: pass

def process_hot_folder_job(source_filepath: str):
    """Orchestrates the translation workflow for a file from the hot folder."""
    filename = os.path.basename(source_filepath)
    
    job_id = f"hotfolder_{int(time.time())}"
    logger.info(f"Hot Folder: Detected ad-hoc file '{filename}', assigning Job ID: {job_id}")

    with open(HOTFOLDER_MANIFEST_PATH, 'a', encoding='utf-8') as f:
        f.write(f"{job_id},{source_filepath}\n")

    source_lang, target_lang = DEFAULT_SOURCE_LANGUAGE, DEFAULT_TARGET_LANGUAGE
    if '_to_' in os.path.splitext(filename)[0]:
        target_lang = os.path.splitext(filename)[0].split('_to_')[-1]
    
    logger.info(f"Hot Folder Job [{job_id}]: Translating from '{source_lang}' to '{target_lang}' (PARALLEL mode)...")
    source_text = get_text_from_file(source_filepath)
    if source_text.startswith("Error:"):
        logger.error(f"Hot Folder Job [{job_id}]: Could not read file: {source_text}")
        return
    
    models = {"gpt": translate_with_gpt, "claude": translate_with_claude, "gemini": translate_with_gemini}
    translations = {}
    threads = []
    def run_translation(service, func):
        translations[service] = func(source_text, target_lang, source_lang)
    for name, func in models.items():
        thread = threading.Thread(target=run_translation, args=(name, func))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    
    success_count = 0
    for service, result in translations.items():
        if not result.startswith("Error:"):
            save_translation_output(source_filepath, service, result, job_id=job_id)
            success_count += 1
    
    total_tasks = len(models)
    if success_count == total_tasks:
        logger.info(f"Hot Folder Job [{job_id}]: Processing complete. All {total_tasks} succeeded.")
    elif success_count > 0:
        logger.warning(f"Hot Folder Job [{job_id}]: Partial success. Succeeded: {success_count}/{total_tasks}.")
    else:
        logger.error(f"Hot Folder Job [{job_id}]: All {total_tasks} translations failed.")

    with open(UI_RELOAD_SIGNAL_PATH, 'w') as f: pass

# --- Main Worker Loops (Controllable) ---
def csv_handshake_worker(stop_event: threading.Event):
    """Monitors the CSV, but stops when the stop_event is set."""
    logger.info("CSV Worker started.")
    while not stop_event.is_set():
        # --- NEW: Check for config reload signal ---
        if os.path.exists(config.CONFIG_RELOAD_SIGNAL_PATH):
            try:
                # Reload the config module to pick up changes from .env
                importlib.reload(config)
                # Re-apply dummy mode if it was changed
                # (This is a simplified approach; a more complex app might use a class)
                if config.DUMMY_MODE:
                    # Logic to re-patch functions if needed
                    pass
                os.remove(config.CONFIG_RELOAD_SIGNAL_PATH)
                logger.warning("Configuration reloaded due to signal from UI.")
                # Log the new state
                logger.info(f"New Operation Mode: {config.OPERATION_MODE}")
                logger.info(f"New Primary Model: {config.PRIMARY_MODEL}")
            except Exception as e:
                logger.error(f"Failed to reload configuration: {e}")
                
        try:
            if not os.path.exists(JOBS_FEED_CSV_PATH): raise FileNotFoundError
            df = pd.read_csv(JOBS_FEED_CSV_PATH, sep=',')
            df.columns = [c.strip().lower() for c in df.columns]
            if 'link' not in df.columns or 'title' not in df.columns:
                logger.error(f"CSV format issue in '{JOBS_FEED_CSV_PATH}'."); stop_event.wait(POLL_INTERVAL); continue
        except Exception as e:
            logger.error(f"Could not process CSV. Error: {e}"); stop_event.wait(POLL_INTERVAL); continue
        
        processed_links = get_processed_jobs(); new_jobs = df[~df['link'].isin(processed_links)].copy()
        if new_jobs.empty: stop_event.wait(POLL_INTERVAL); continue
        pending_job_ids = {get_job_id_from_link(link) for link in new_jobs['link']}; pending_job_ids.discard(None)
        if pending_job_ids: logger.info(f"CSV Worker: Found {len(pending_job_ids)} new jobs. Pre-registering IDs."); active_handshake_jobs.update(pending_job_ids)
        
        for _, job in new_jobs.iterrows():
            if stop_event.is_set(): break
            job_id = get_job_id_from_link(job['link'])
            if not job_id: continue
            logger.info(f"[Job {job_id}] New job found. Prompting for manual action.")
            pyperclip.copy(job_id); logger.info(f"[Job {job_id}] Copied ID to clipboard.")
            stop_event.wait(HANDSHAKE_WAIT_TIME)

            if stop_event.is_set(): break
            source_filepath = find_job_file(job_id)
            if source_filepath: process_csv_job(job, source_filepath)
            else: logger.warning(f"[Job {job_id}] Timed out. Assuming job was rejected."); log_processed_job(job['link'])
            active_handshake_jobs.discard(job_id)
    logger.info("CSV Worker received stop signal and is shutting down.")

class HotFolderHandler(FileSystemEventHandler):
    """Event handler that dispatches jobs to the processing function."""
    def on_created(self, event):
        if event.is_directory: return
        source_filepath = event.src_path
        job_id_match = re.match(r'^(\d+)', os.path.basename(source_filepath))
        if job_id_match and job_id_match.group(1) in active_handshake_jobs:
            logger.info(f"Hot Folder: Ignoring '{os.path.basename(source_filepath)}' (handled by CSV worker).")
            return
        process_hot_folder_job(source_filepath)

def folder_monitor_worker(stop_event: threading.Event):
    """Initializes and runs the watchdog observer, stopping when the event is set."""
    logger.info("Hot Folder Worker started.")
    observer = Observer()
    observer.schedule(HotFolderHandler(), UPLOADS_DIR, recursive=False); observer.start()
    try:
        while not stop_event.is_set():
            time.sleep(1) # The observer runs in its own thread, we just need to keep this one alive
    finally:
        observer.stop()
        observer.join()
        logger.info("Hot Folder Worker received stop signal and is shutting down.")
