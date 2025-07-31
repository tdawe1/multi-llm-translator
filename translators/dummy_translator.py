import logging
import time
import random

def dummy_translate_with_gpt(text: str, target_language: str, source_language: str = "English") -> str:
    """Simulates a GPT translation call."""
    logging.info(f"  -> [DUMMY] Simulating translation with GPT ({source_language} -> {target_language})...")
    time.sleep(random.uniform(1, 2))
    return f"[DUMMY GPT]: This is a simulated translation into {target_language}."

def dummy_translate_with_claude(text: str, target_language: str, source_language: str = "English") -> str:
    """Simulates a Claude translation call that sometimes 'fails'."""
    logging.info(f"  -> [DUMMY] Simulating translation with Claude ({source_language} -> {target_language})...")
    time.sleep(random.uniform(1, 3))
    if random.random() < 0.3:
        logging.warning("  -> [DUMMY] Simulating a failure for Claude translation.")
        return "Error: Dummy Claude translation failed as intended."
    return f"[DUMMY CLAUDE]: This is a simulated translation into {target_language}."

def dummy_translate_with_gemini(text: str, target_language: str, source_language: str = "English") -> str:
    """Simulates a Gemini translation call."""
    logging.info(f"  -> [DUMMY] Simulating translation with Gemini ({source_language} -> {target_language})...")
    time.sleep(random.uniform(1, 2.5))
    return f"[DUMMY GEMINI]: This is a simulated translation into {target_language}."

def dummy_critique_with_gpt(source_text: str, primary_translation: str, target_language: str, source_language: str = "English") -> str:
    """Simulates a GPT critique call."""
    logging.info("  -> [DUMMY] Simulating critique with GPT...")
    time.sleep(random.uniform(1, 2))
    return "**Critique:** [DUMMY GPT] The primary translation is generally good but lacks nuance.\n**Refined Translation:** This is a refined GPT translation."

def dummy_critique_with_claude(source_text: str, primary_translation: str, target_language: str, source_language: str = "English") -> str:
    """Simulates a Claude critique call."""
    logging.info("  -> [DUMMY] Simulating critique with Claude...")
    time.sleep(random.uniform(1, 3))
    return "**Critique:** [DUMMY CLAUDE] The tone is slightly off in the primary translation.\n**Refined Translation:** This is a refined Claude translation that adjusts the tone."

def dummy_critique_with_gemini(source_text: str, primary_translation: str, target_language: str, source_language: str = "English") -> str:
    """Simulates a Gemini critique call."""
    logging.info("  -> [DUMMY] Simulating critique with Gemini...")
    time.sleep(random.uniform(1, 2.5))
    return "**Critique:** [DUMMY GEMINI] A few key terms could be improved for accuracy.\n**Refined Translation:** This is a refined Gemini translation with better terminology."