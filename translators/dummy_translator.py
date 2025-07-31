import time
import random

def dummy_translate_with_gpt(text: str, target_language: str, source_language: str = "English") -> str:
    """Simulates a GPT translation call."""
    print("  -> [DUMMY] Simulating translation with GPT...")
    time.sleep(random.uniform(1, 3)) # Simulate network delay
    return f"[DUMMY GPT]: Successfully translated text to {target_language}."

def dummy_translate_with_claude(text: str, target_language: str, source_language: str = "English") -> str:
    """Simulates a Claude translation call that sometimes 'fails'."""
    print("  -> [DUMMY] Simulating translation with Claude...")
    time.sleep(random.uniform(1, 3))
    
    # Simulate a failure every so often to test resilience
    if random.random() < 0.3: 
        print("  -> [DUMMY] Simulating a failure for Claude.")
        return "Error: Dummy Claude translation failed as intended."
    
    return f"[DUMMY CLAUDE]: Successfully translated text to {target_language}."

def dummy_translate_with_gemini(text: str, target_language: str, source_language: str = "English") -> str:
    """Simulates a Gemini translation call."""
    print("  -> [DUMMY] Simulating translation with Gemini...")
    time.sleep(random.uniform(1, 3))
    return f"[DUMMY GEMINI]: Successfully translated text to {target_language}."