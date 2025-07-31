import google.generativeai as genai
from config import GOOGLE_API_KEY
from .utils import get_prompt_with_glossary

genai.configure(api_key=GOOGLE_API_KEY)

def translate_with_gemini(text: str, target_language: str, source_language: str = "English") -> str:
    """Translates text using Google's Gemini model with a dynamic prompt."""
    if not text or not text.strip():
        return ""

    prompt_placeholders = {
        '{source_language}': source_language,
        '{target_language}': target_language,
        '{text}': text
    }

    prompt = get_prompt_with_glossary('templates/translate_prompt.txt', prompt_placeholders)
    
    try:
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error: Gemini translation failed. {e}"

def critique_with_gemini(source_text: str, primary_translation: str, target_language: str, source_language: str = "English") -> str:
    """Critiques a translation using Google's Gemini model."""
    prompt_placeholders = {
        '{source_language}': source_language,
        '{target_language}': target_language,
        '{source_text}': source_text,
        '{primary_translation}': primary_translation
    }

    prompt = get_prompt_with_glossary('templates/critique_prompt.txt', prompt_placeholders)

    try:
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        response = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.4))
        return response.text.strip()
    except Exception as e:
        return f"Error: Gemini critique failed. {e}"
