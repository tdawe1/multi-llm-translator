
# ✅ Project Summary: Multi-LLM Translation Assistant

## 🔍 Overview  
A Python-based tool designed to **monitor incoming translation jobs** (from a CSV or local folder), **fetch content from URLs or documents**, translate it using **multiple LLMs (GPT-4, Claude, Gemini)**, and output **finished, editable translated files**.

The assistant will support `.docx`, `.pptx`, `.xlsx`, and URLs (e.g. articles, job pages) as input. It will be able to run in the background, triggered by job updates, and optionally include a simple UI for reviewing outputs or managing jobs.

## 🎯 Key Goals

- ✅ Automate first-pass translation of incoming work
- ✅ Increase throughput and reduce manual prep time
- ✅ Use multiple LLMs for quality comparison and consistency
- ✅ Reintegrate translations into the original document formats
- ✅ Lay the groundwork for future tooling (e.g. glossary support, QA workflows)

## 🧱 Core Features

| Feature                             | Description |
|------------------------------------|-------------|
| **Job monitoring**                 | Watches a `.csv` or folder for new jobs (from your existing tool) |
| **URL + file fetching**           | Extracts content from `.docx`, `.pptx`, `.xlsx`, or HTML pages |
| **Multi-model translation**        | Uses GPT-4, Claude 3, and Gemini to translate content in parallel |
| **Output regeneration**            | Saves translated content back to editable `.docx`, `.pptx`, `.xlsx` |
| **Optional UI (Streamlit)**        | Allows previewing, approving, or comparing translations |
| **Extensible prompt templates**    | Style/tone can be adjusted per job, domain, or client |

## 🧰 Tooling & Libraries

| Task                   | Tools/Libraries |
|------------------------|-----------------|
| File monitoring        | `watchdog`, `pandas` |
| URL/text extraction    | `requests`, `BeautifulSoup` |
| File I/O               | `python-docx`, `python-pptx`, `openpyxl` |
| LLM access             | `openai`, `anthropic`, `google.generativeai` |
| UI (optional)          | `streamlit` |
| Config/logging         | `dotenv`, `logging`, `json`, `yaml` |

## 🗓️ First Steps Plan (Weeks 1–2)

### Step 1: Set Up Project Structure
- Create base folders: `monitor/`, `fetchers/`, `translators/`, `outputs/`
- Create config files and `.env` for API keys

### Step 2: Implement Basic LLM Translation Logic
- Write functions for translating text via:
  - GPT-4 (OpenAI)
  - Claude 3 (Anthropic)
  - Gemini 1.5 (Google)
- Standardize prompt template

### Step 3: Add CSV Monitor and URL Fetcher
- Parse `.csv` to detect new jobs (by ID, hash, or timestamp)
- Extract source content from job URL using `requests` + `BeautifulSoup`

### Step 4: Output Basic Text File
- Translate fetched text with all 3 models
- Save outputs as `.txt` or `.md` side-by-side for manual review

## 🪜 Phase 2+ (After Initial Working Prototype)

- Add support for `.docx`, `.pptx`, `.xlsx` inputs
- Regenerate fully formatted output files
- Add glossary/term enforcement
- Build Streamlit UI for manual comparison + QA
- Add job status tracking (e.g. `processed`, `pending`)
- Optional: auto-send outputs to email/Notion/Drive
