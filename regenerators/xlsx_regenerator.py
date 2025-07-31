import openpyxl

def create_xlsx_from_text(original_filepath: str, translated_text: str, output_filepath: str):
    """
    Creates a new .xlsx file by replacing string cell values with translated text.
    """
    try:
        wb = openpyxl.load_workbook(original_filepath)
        translated_texts = translated_text.split('\n\n')
        text_index = 0

        for sheet in wb.worksheets:
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.value and isinstance(cell.value, str):
                        if text_index < len(translated_texts):
                            cell.value = translated_texts[text_index]
                            text_index += 1
        
        wb.save(output_filepath)
        return f"Successfully created {output_filepath}"
    except Exception as e:
        return f"Error: Failed to regenerate .xlsx file. {e}"