def get_text_from_file(filepath: str) -> str:
    """Reads and returns the text content from a given .txt file."""
    # This will be expanded later to handle .docx, .pptx, etc.
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found at {filepath}"
    except Exception as e:
        return f"Error: Could not read file. {e}"