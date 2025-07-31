import json
from config import GLOSSARY_PATH

def load_glossary() -> dict:
    try:
        with open(GLOSSARY_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {} # Return empty dict if no glossary exists

def get_prompt_with_glossary(template_path: str, placeholders: dict) -> str:
    """Reads a prompt template, injects the glossary, and fills placeholders."""
    with open(template_path, 'r', encoding='utf-8') as f:
        prompt_template = f.read()

    glossary = load_glossary()
    glossary_section = ""
    if glossary:
        terms = "\n".join([f'- "{key}" must be translated as "{value}"' for key, value in glossary.items()])
        glossary_section = f"You must adhere to the following glossary terms:\n{terms}\n"
    
    placeholders['{glossary_section}'] = glossary_section

    for key, value in placeholders.items():
        prompt_template = prompt_template.replace(key, value)
    
    return prompt_template
