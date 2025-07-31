from docx import Document


def create_docx_from_text(
    original_filepath: str, translated_text: str, output_filepath: str
):
    """
    Creates a new .docx file with the translated text, preserving paragraph breaks.

    Note: This is a simple regeneration. It does not preserve advanced formatting like
    bold, italics, or tables. That requires a more complex, style-mapping approach.
    """
    try:
        # Create a new document
        new_doc = Document()

        # Split the translated text back into paragraphs
        translated_paragraphs = translated_text.split("\n\n")

        for para in translated_paragraphs:
            new_doc.add_paragraph(para)

        new_doc.save(output_filepath)
        return f"Successfully created {output_filepath}"
    except Exception as e:
        return f"Error: Failed to regenerate .docx file. {e}"
