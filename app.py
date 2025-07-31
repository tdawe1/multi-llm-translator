import pandas as pd
import os
import time
import re
import threading
import pyperclip
import logging
import colorlog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- Consolidate Imports ---
from fetchers.file_fetcher import get_text_from_file
from translators.gpt_translator import translate_with_gpt, critique_with_gpt
from translators.claude_translator import translate_with_claude, critique_with_claude
from translators.gemini_translator import translate_with_gemini, critique_with_gemini
from translators.dummy_translator import (
    dummy_translate_with_gpt, dummy_critique_with_gpt,
    dummy_translate_with_claude, dummy_critique_with_claude,
    dummy_translate_with_gemini, dummy_critique_with_gemini
)
from regenerators.docx_regenerator import create_docx_from_text
from regenerators.pptx_regenerator import create_pptx_from_text
from regenerators.xlsx_regenerator import create_xlsx_from_text
from config import (
    DUMMY_MODE, 
    DEFAULT_SOURCE_LANGUAGE, 
    DEFAULT_TARGET_LANGUAGE,
    OPERATION_MODE, 
    PRIMARY_MODEL
)

# --- Setup Advanced, Colored Logging ---
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
if logger.hasHandlers():
    logger.handlers.clear()
console_handler = colorlog.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = colorlog.ColoredFormatter(
    '%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(message)s',
    log_colors={
        'DEBUG':    'cyan', 'INFO':     'green',
        'WARNING':  'yellow', 'ERROR':    'red',
        'CRITICAL': 'red,bg_white',
    })
console_handler.setFormatter(console_formatter)
file_handler = logging.FileHandler("app.log", mode='w')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - %(threadName)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# --- DUMMY MODE SWITCH ---
if DUMMY_MODE:
    translate_with_gpt = dummy_translate_with_gpt; critique_with_gpt = dummy_critique_with_gpt
    translate_with_claude = dummy_translate_with_claude; critique_with_claude = dummy_critique_with_claude
    translate_with_gemini = dummy_translate_with_gemini; critique_with_gemini = dummy_critique_with_gemini

# --- Configuration & State ---
JOBS_FEED_CSV_PATH = "monitor/jobs_feed.csv"
PROCESSED_LOG_PATH = "monitor/processed_jobs.log"
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

def process_hot_folder_job(source_filepath: str):
    """Orchestrates the translation workflow for a file from the hot folder."""
    filename = os.path.basename(source_filepath)
    logger.info(f"Hot Folder: Detected new ad-hoc file '{filename}'.")
    source_lang, target_lang = DEFAULT_SOURCE_LANGUAGE, DEFAULT_TARGET_LANGUAGE
    if '_to_' in os.path.splitext(filename)[0]: target_lang = os.path.splitext(filename)[0].split('_to_')[-1]
    logger.info(f"Hot Folder: Translating from '{source_lang}' to '{target_lang}' (PARALLEL mode)...")
    source_text = get_text_from_file(source_filepath)
    if source_text.startswith("Error:"): logger.error(f"Hot Folder: Could not read file: {source_text}"); return
    
    models = {"gpt": translate_with_gpt, "claude": translate_with_claude, "gemini": translate_with_gemini}
    translations = {}; threads = []
    def run_translation(service, func): translations[service] = func(source_text, target_lang, source_lang)
    for name, func in models.items():
        thread = threading.Thread(target=run_translation, args=(name, func)); threads.append(thread); thread.start()
    for thread in threads: thread.join()
    
    success_count = 0
    for service, result in translations.items():
        if not result.startswith("Error:"): save_translation_output(source_filepath, service, result); success_count += 1
    
    total_tasks = len(models)
    if success_count == total_tasks: logger.info(f"Hot Folder Job '{filename}': Processing complete. All {total_tasks} succeeded.")
    elif success_count > 0: logger.warning(f"Hot Folder Job '{filename}': Partial success. Succeeded: {success_count}/{total_tasks}.")
    else: logger.error(f"Hot Folder Job '{filename}': All {total_tasks} translations failed.")

# --- Main Worker Loops ---
def csv_handshake_worker():
    """Monitors the CSV, alerts user, and dispatches jobs for processing."""
    logger.info("CSV Worker started.")
    while True:
        try:
            if not os.path.exists(JOBS_FEED_CSV_PATH): raise FileNotFoundError
            df = pd.read_csv(JOBS_FEED_CSV_PATH, sep=',')
            df.columns = [c.strip().lower() for c in df.columns]
            if 'link' not in df.columns or 'title' not in df.columns:
                logger.error(f"CSV format issue in '{JOBS_FEED_CSV_PATH}'."); time.sleep(POLL_INTERVAL); continue
        except Exception as e:
            logger.error(f"Could not process CSV. Error: {e}"); time.sleep(POLL_INTERVAL); continue
        
        processed_links = get_processed_jobs(); new_jobs = df[~df['link'].isin(processed_links)].copy()
        if new_jobs.empty: time.sleep(POLL_INTERVAL); continue
        pending_job_ids = {get_job_id_from_link(link) for link in new_jobs['link']}; pending_job_ids.discard(None)
        if pending_job_ids: logger.info(f"CSV Worker: Found {len(pending_job_ids)} new jobs. Pre-registering IDs."); active_handshake_jobs.update(pending_job_ids)
        
        for _, job in new_jobs.iterrows():
            job_id = get_job_id_from_link(job['link'])
            if not job_id: continue
            logger.info(f"[Job {job_id}] New job found. Prompting for manual action.")
            pyperclip.copy(job_id); logger.info(f"[Job {job_id}] Copied ID to clipboard.")
            time.sleep(HANDSHAKE_WAIT_TIME)

            source_filepath = find_job_file(job_id)
            if source_filepath:
                process_csv_job(job, source_filepath)
            else:
                logger.warning(f"[Job {job_id}] Timed out. File not found. Assuming job was rejected."); log_processed_job(job['link'])
            active_handshake_jobs.discard(job_id)

class HotFolderHandler(FileSystemEventHandler):
    """Event handler for the hot folder that dispatches jobs for processing."""
    def on_created(self, event):
        if event.is_directory: return
        source_filepath = event.src_path
        job_id_match = re.match(r'^(\d+)', os.path.basename(source_filepath))
        if job_id_match and job_id_match.group(1) in active_handshake_jobs:
            logger.info(f"Hot Folder: Ignoring '{os.path.basename(source_filepath)}' (handled by CSV worker).")
            return
        process_hot_folder_job(source_filepath)

def folder_monitor_worker():
    """Initializes and runs the watchdog observer for the hot folder."""
    logger.info("Hot Folder Worker started.")
    observer = Observer()
    observer.schedule(HotFolderHandler(), UPLOADS_DIR, recursive=False); observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: observer.stop()
    observer.join()

# --- Main Thread Orchestrator ---
if __name__ == "__main__":
    for d in [UPLOADS_DIR, OUTPUTS_DIR, "monitor"]: os.makedirs(d, exist_ok=True)
    logger.info("--- Starting Multi-LLM Translation Assistant ---")
    logger.info(f"Operation Mode: {OPERATION_MODE}")
    logger.info(f"Primary Model for SIMPLE/CRITIQUE modes: {PRIMARY_MODEL}")
    if DUMMY_MODE: logger.warning("DUMMY MODE IS ACTIVE. NO REAL API CALLS WILL BE MADE.")
    csv_thread = threading.Thread(target=csv_handshake_worker, name="CSVHandshakeThread")
    folder_thread = threading.Thread(target=folder_monitor_worker, name="FolderMonitorThread", daemon=True)
    csv_thread.start(); folder_thread.start()
    csv_thread.join()
    logger.info("--- Application Shutting Down ---")