import google.generativeai as genai
from config import GOOGLE_API_KEY

genai.configure(api_key=GOOGLE_API_KEY)

def translate_with_gemini(text: str, target_language: str, source_language: str = "English") -> str:
    """
    Translates text using Google's Gemini 2.5 Pro model.
    """
    if not text or not text.strip():
        return ""

    prompt = f"Translate the following text from {source_language} to {target_language}, preserving original formatting:\n\n{text}"
    
    try:
        # Using the specific preview ID for Gemini 2.5 Pro as per documentation
        model = genai.GenerativeModel('gemini-2.5-pro-preview-06-05')
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"[ERROR] An error occurred with the Google Generative AI API: {e}")
        return f"Error: Gemini translation failed. {e}"