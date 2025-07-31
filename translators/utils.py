import json
import logging
import config 

def load_glossary() -> dict:
    """Loads the glossary from the path specified in the config module."""
    glossary_path = config.GLOSSARY_PATH 
    try:
        with open(glossary_path, 'r', encoding='utf-8') as f:
            glossary = json.load(f)
            logging.info(f"Successfully loaded glossary from '{glossary_path}' with {len(glossary)} terms.")
            return glossary
    except FileNotFoundError:
        logging.warning(f"Glossary file not found at '{glossary_path}'. Continuing without it.")
        return {}
    except json.JSONDecodeError:
        logging.error(f"Could not decode JSON from '{glossary_path}'. Please check its format. Continuing without glossary.")
        return {}

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