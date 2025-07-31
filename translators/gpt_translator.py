import openai
import logging
from config import OPENAI_API_KEY
from .utils import get_prompt_with_glossary

openai.api_key = OPENAI_API_KEY

def translate_with_gpt(text: str, target_language: str, source_language: str = "English") -> str:
    """Translates text using OpenAI's GPT model."""
    if not text or not text.strip(): return ""
    prompt = get_prompt_with_glossary('templates/translate_prompt.txt', {'{source_language}': source_language, '{target_language}': target_language, '{text}': text})
    logging.debug(f"Full prompt for GPT translation:\n{prompt}")
    try:
        response = openai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], temperature=0.2)
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"OpenAI translation API call failed: {e}")
        return f"Error: OpenAI translation failed. {e}"

def critique_with_gpt(source_text: str, primary_translation: str, target_language: str, source_language: str = "English") -> str:
    """Critiques a translation using OpenAI's GPT model."""
    if not source_text or not source_text.strip(): return ""
    prompt = get_prompt_with_glossary('templates/critique_prompt.txt', {'{source_language}': source_language, '{target_language}': target_language, '{source_text}': source_text, '{primary_translation}': primary_translation})
    logging.debug(f"Full prompt for GPT critique:\n{prompt}")
    try:
        response = openai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], temperature=0.4)
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"OpenAI critique API call failed: {e}")
        return f"Error: OpenAI critique failed. {e}"

