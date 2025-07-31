import anthropic
from config import ANTHROPIC_API_KEY
from .utils import get_prompt_with_glossary

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def translate_with_claude(text: str, target_language: str, source_language: str = "English") -> str:
    """Translates text using Anthropic's Claude model with a dynamic prompt."""
    if not text or not text.strip():
        return ""

    prompt_placeholders = {
        '{source_language}': source_language,
        '{target_language}': target_language,
        '{text}': text
    }
    
    system_prompt = get_prompt_with_glossary('templates/translate_prompt.txt', prompt_placeholders)
    # The actual user message is now simpler as the instruction is in the system prompt.
    user_message = text 

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=4096,
            system=system_prompt, # Using the full prompt as a system prompt for Claude
            messages=[{"role": "user", "content": user_message}]
        )
        return message.content[0].text
    except Exception as e:
        return f"Error: Claude translation failed. {e}"

def critique_with_claude(source_text: str, primary_translation: str, target_language: str, source_language: str = "English") -> str:
    """Critiques a translation using Anthropic's Claude model."""
    prompt_placeholders = {
        '{source_language}': source_language,
        '{target_language}': target_language,
        '{source_text}': source_text,
        '{primary_translation}': primary_translation
    }
    
    critique_prompt = get_prompt_with_glossary('templates/critique_prompt.txt', prompt_placeholders)

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=4096,
            # For critique, the entire structured prompt is sent as the user message.
            messages=[{"role": "user", "content": critique_prompt}],
            temperature=0.4
        )
        return message.content[0].text
    except Exception as e:
        return f"Error: Claude critique failed. {e}"
