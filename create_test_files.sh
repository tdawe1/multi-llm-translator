#!/bin/bash

# A script to clean the uploads folder and create fresh test files.

echo "[INFO] Clearing the 'uploads/' and 'outputs' directories..."
rm -f uploads/*
rm -f outputs/*


echo "[INFO] Creating new test files for .txt, .docx, .pptx, and .xlsx..."

./.venv/bin/python - <<EOF
import os
from docx import Document
from pptx import Presentation
from pptx.util import Inches
from openpyxl import Workbook

UPLOADS_DIR = "uploads"

# Ensure the directory exists
os.makedirs(UPLOADS_DIR, exist_ok=True)

# 1. Create a .txt file
with open(os.path.join(UPLOADS_DIR, "test_plain_text.txt"), 'w', encoding='utf-8') as f:
    f.write("This is a plain text file for testing.\nこれはテスト用のプレーンテキストファイルです。")
print("-> Created test_plain_text.txt")

# 2. Create a .docx file
doc = Document()
doc.add_heading('Test Document', level=1)
doc.add_paragraph('This is the first paragraph of a test Word document.')
doc.add_paragraph('これはテスト用のWord文書の最初の段落です。')
doc.save(os.path.join(UPLOADS_DIR, 'test_document.docx'))
print("-> Created test_document.docx")

# 3. Create a .pptx file
prs = Presentation()
title_slide_layout = prs.slide_layouts[0]
slide = prs.slides.add_slide(title_slide_layout)
title = slide.shapes.title
subtitle = slide.placeholders[1]
title.text = "Test Presentation"
subtitle.text = "これはテスト用のプレゼンテーションです。"
prs.save(os.path.join(UPLOADS_DIR, 'test_presentation.pptx'))
print("-> Created test_presentation.pptx")

# 4. Create an .xlsx file
wb = Workbook()
ws = wb.active
ws.title = "TestData"
ws['A1'] = "Test String"
ws['A2'] = 12345
ws['B1'] = "テスト文字列"
ws['B2'] = "これはB2セルです。"
wb.save(os.path.join(UPLOADS_DIR, 'test_spreadsheet.xlsx'))
print("-> Created test_spreadsheet.xlsx")

EOF

echo ""
echo "[SUCCESS] Test files have been created in the 'uploads/' directory:"
ls -l uploads/
