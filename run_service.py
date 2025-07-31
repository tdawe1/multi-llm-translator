import threading
import logging
import colorlog
from config import DUMMY_MODE, OPERATION_MODE, PRIMARY_MODEL

from core import csv_handshake_worker, folder_monitor_worker

# --- Setup Advanced, Colored Logging for this entry point ---
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
if logger.hasHandlers():
    logger.handlers.clear()
console_handler = colorlog.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(message)s",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_white",
    },
)
console_handler.setFormatter(console_formatter)
file_handler = logging.FileHandler("app.log", mode="w")
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)-8s - %(threadName)s - %(message)s"
)
file_handler.setFormatter(file_formatter)
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# --- DUMMY MODE SWITCH ---
if DUMMY_MODE:
    from translators import dummy_translator
    import core

    core.translate_with_gpt = dummy_translator.dummy_translate_with_gpt
    core.critique_with_gpt = dummy_translator.dummy_critique_with_gpt
    core.translate_with_claude = dummy_translator.dummy_translate_with_claude
    core.critique_with_claude = dummy_translator.dummy_critique_with_claude
    core.translate_with_gemini = dummy_translator.dummy_translate_with_gemini
    core.critique_with_gemini = dummy_translator.dummy_critique_with_gemini

# --- Main Thread Orchestrator ---
if __name__ == "__main__":
    stop_event = threading.Event()

    # Create the worker threads, passing the stop_event to them
    csv_thread = threading.Thread(
        target=csv_handshake_worker, args=(stop_event,), name="CSVHandshakeThread"
    )
    folder_thread = threading.Thread(
        target=folder_monitor_worker,
        args=(stop_event,),
        name="FolderMonitorThread",
        daemon=True,
    )

    logger.info("--- Starting Multi-LLM Translation Service (Headless) ---")
    logger.info(f"Operation Mode: {OPERATION_MODE}")
    logger.info(f"Primary Model for SIMPLE/CRITIQUE modes: {PRIMARY_MODEL}")
    if DUMMY_MODE:
        logger.warning("DUMMY MODE IS ACTIVE. NO REAL API CALLS WILL BE MADE.")

    # Start the threads
    csv_thread.start()
    folder_thread.start()

    try:
        # Keep the main thread alive. The only job is to wait for a KeyboardInterrupt.
        csv_thread.join()
    except KeyboardInterrupt:
        logger.info("--- Shutdown signal (Ctrl+C) received. Stopping workers... ---")
        stop_event.set()
        # Wait for the main worker to finish its current loop and shut down gracefully
        csv_thread.join()

    logger.info("--- Application Shut Down ---")
