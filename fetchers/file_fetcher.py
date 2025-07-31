def get_text_from_file(filepath: str) -> str:
    """Reads and returns the text content from a given .txt file."""
    # This will be expanded later to handle .docx, .pptx, etc.
    try:
        if filepath.endswith('.docx'):
            import docx
            doc = docx.Document(filepath)
            # Join the text of all paragraphs, separated by double newlines
            full_text = [p.text for p in doc.paragraphs]
            return "\n\n".join(full_text)
        elif filepath.endswith('.txt'):
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return "Error: Unsupported file type. Use .txt or .docx only."
    except FileNotFoundError:
        return f"Error: File not found at {filepath}"
    except Exception as e:
        return f"Error: Could not read file. {e}"
