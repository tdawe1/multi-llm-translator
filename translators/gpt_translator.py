import os
import openai
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY


def translate_with_gpt(text: str, target_language: str, source_language: str = "English") -> str:
    """
    Translates a given text to the target language using GPT-4.

    Args:
        text (str): The text to be translated.
        target_language (str): The language to translate into (e.g., "Japanese").
        source_language (str): The source language of the text.

    Returns:
        str: The translated text or an error message.
    """
    if not text or not text.strip():
        return ""

    # can be moved to a separate file later
    prompt = f"""
    As a professional translator, please translate the following text from {source_language} to {target_language}.
    Maintain the original tone, style, and formatting (including line breaks).
    Only provide the translated text as the output.

    Source Text:
    ---
    {text}
    ---

    Translation:
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",  
            messages=[
                {"role": "system", "content": "You are a highly skilled translation engine."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,  # Lower temperature for more predictable translations
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ERROR] An error occurred with the OpenAI API: {e}")
        return f"Error: Translation failed. {e}"