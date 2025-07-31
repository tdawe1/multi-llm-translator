import anthropic
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def translate_with_claude(text: str, target_language: str, source_language: str = "English") -> str:
    """
    Translates text using Anthropic's most advanced available model.
    """
    if not text or not text.strip():
        return ""

    system_prompt = f"Translate the following text from {source_language} to {target_language}. Maintain original formatting and style."

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": text}]
        )
        return message.content[0].text
    except Exception as e:
        print(f"An error occurred with the Anthropic API: {e}")
        return f"Error: Claude translation failed. {e}"

