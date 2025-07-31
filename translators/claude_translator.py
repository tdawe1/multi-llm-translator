import logging
import anthropic
from config import ANTHROPIC_API_KEY
from .utils import get_prompt_with_glossary

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def translate_with_claude(
    text: str, target_language: str, source_language: str = "English"
) -> str:
    """Translates text using Anthropic's Claude model with a dynamic prompt."""
    if not text or not text.strip():
        return ""
    prompt_placeholders = {
        "{source_language}": source_language,
        "{target_language}": target_language,
        "{text}": text,
    }
    system_prompt = get_prompt_with_glossary(
        "templates/translate_prompt.txt", prompt_placeholders
    )
    logging.debug(f"Full system prompt for Claude translation:\n{system_prompt}")
    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": text}],
        )
        return message.content[0].text
    except Exception as e:
        logging.error(f"Claude translation API call failed: {e}")
        return f"Error: Claude translation failed. {e}"


def critique_with_claude(
    source_text: str,
    primary_translation: str,
    target_language: str,
    source_language: str = "English",
) -> str:
    """Critiques a translation using Anthropic's Claude model."""
    if not source_text or not source_text.strip():
        return ""
    prompt_placeholders = {
        "{source_language}": source_language,
        "{target_language}": target_language,
        "{source_text}": source_text,
        "{primary_translation}": primary_translation,
    }
    critique_prompt = get_prompt_with_glossary(
        "templates/critique_prompt.txt", prompt_placeholders
    )
    logging.debug(f"Full prompt for Claude critique:\n{critique_prompt}")
    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=4096,
            messages=[{"role": "user", "content": critique_prompt}],
            temperature=0.4,
        )
        return message.content[0].text
    except Exception as e:
        logging.error(f"Claude critique API call failed: {e}")
        return f"Error: Claude critique failed. {e}"
