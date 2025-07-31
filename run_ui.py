import streamlit as st
import os
import re
import time
from collections import defaultdict

# --- Import the robust text extractor from your core logic ---
from fetchers.file_fetcher import get_text_from_file
from config import UI_RELOAD_SIGNAL_PATH

# --- Configuration ---
OUTPUTS_DIR = "outputs"
UPLOADS_DIR = "uploads"
HOTFOLDER_MANIFEST_PATH = "monitor/hotfolder_manifest.log"

st.set_page_config(layout="wide", page_title="Translation Review")

# --- Signal Handling ---
if os.path.exists(UI_RELOAD_SIGNAL_PATH):
    try:
        os.remove(UI_RELOAD_SIGNAL_PATH)
        st.cache_data.clear() # Clear the cache to force a data refresh
        st.toast("New job results detected. Refreshing...")
    except OSError as e:
        st.error(f"Error handling reload signal: {e}")

# --- Helper Functions (Cached) ---
@st.cache_data
def get_job_data():
    """Scans directories and returns all necessary data. Cached until cleared."""
    job_files = defaultdict(list)
    if os.path.exists(OUTPUTS_DIR):
        for f in os.listdir(OUTPUTS_DIR):
            match = re.search(r'job_([\w\d.-]+)_', f) # Expanded regex for timestamps
            if match:
                job_files[match.group(1)].append(f)
    
    manifest = {}
    if os.path.exists(HOTFOLDER_MANIFEST_PATH):
        with open(HOTFOLDER_MANIFEST_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                if ',' in line:
                    job_id, filepath = line.strip().split(',', 1)
                    manifest[job_id] = filepath
    return job_files, manifest

def find_source_file(job_id, hotfolder_manifest):
    """Finds the original source file for any job ID and extracts its text."""
    source_filepath = None
    if job_id.startswith("hotfolder_"):
        source_filepath = hotfolder_manifest.get(job_id)
    else:
        if os.path.exists(UPLOADS_DIR):
            for f in os.listdir(UPLOADS_DIR):
                if f.startswith(job_id):
                    source_filepath = os.path.join(UPLOADS_DIR, f); break
    
    if source_filepath and os.path.exists(source_filepath):
        source_content = get_text_from_file(source_filepath)
        return os.path.basename(source_filepath), source_content
    return None, "Source file not found."

# --- Main UI Application ---
st.title("Multi-LLM Translation Review")

all_jobs, hotfolder_manifest = get_job_data()

job_ids = ["-- Select a Job to Review --"] + sorted(all_jobs.keys(), reverse=True)
selected_job_id = st.selectbox("Select a Job ID:", job_ids)

if selected_job_id != "-- Select a Job to Review --":
    st.divider()
    st.header(f"Reviewing Job: `{selected_job_id}`")

    with st.expander("View Original Source Text"):
        source_filename, source_content = find_source_file(selected_job_id, hotfolder_manifest)
        if source_filename:
            st.subheader(f"Source: `{source_filename}`")
            st.text_area("Source Content", source_content, height=300)
        else:
            st.error(source_content)
    
    job_outputs = all_jobs[selected_job_id]
    critique_report_file = next((f for f in job_outputs if "CRITIQUE_REPORT" in f), None)

    if critique_report_file:
        st.subheader("Critique & Refinement Report")
        with open(os.path.join(OUTPUTS_DIR, critique_report_file), 'r', encoding='utf-8') as f:
            st.markdown(f.read())
    else:
        st.subheader("Parallel Translation Comparison")
        gpt_file = next((f for f in job_outputs if 'gpt' in f), None)
        claude_file = next((f for f in job_outputs if 'claude' in f), None)
        gemini_file = next((f for f in job_outputs if 'gemini' in f), None)
        col1, col2, col3 = st.columns(3)

        def display_translation(file, service_name, column):
            with column:
                st.subheader(f"{service_name}")
                if file:
                    content = get_text_from_file(os.path.join(OUTPUTS_DIR, file))
                    st.text_area(file, content, height=500, label_visibility="collapsed")
                else:
                    st.warning(f"No output file found.")

        display_translation(gpt_file, "GPT-4o-mini", col1)
        display_translation(claude_file, "Claude 3.5 Sonnet", col2)
        display_translation(gemini_file, "Gemini 2.5 Pro", col3)
else:
    st.info(f"Select a job from the dropdown to see the translation results. The list will update automatically when new jobs are processed.")

time.sleep(5)
st.rerun()
