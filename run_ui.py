import streamlit as st
import os
import re
import time
from collections import defaultdict

from fetchers.file_fetcher import get_text_from_file
from config import UI_RELOAD_SIGNAL_PATH, CONFIG_RELOAD_SIGNAL_PATH
import config as app_config

# --- Configuration ---
OUTPUTS_DIR = "outputs"
UPLOADS_DIR = "uploads"
HOTFOLDER_MANIFEST_PATH = "monitor/hotfolder_manifest.log"
APP_LOG_PATH = "app.log"

st.set_page_config(layout="wide", page_title="Translation Review")

# --- Initialize Session State ---
if "show_log" not in st.session_state:
    st.session_state.show_log = False

# --- Signal Handling ---
if os.path.exists(UI_RELOAD_SIGNAL_PATH):
    try:
        os.remove(UI_RELOAD_SIGNAL_PATH)
        st.cache_data.clear()
        st.toast("New job results detected. Refreshing...")
    except OSError as e:
        st.error(f"Error handling reload signal: {e}")


# --- Helper Functions ---
@st.cache_data
def get_job_data():
    job_files = defaultdict(list)
    if os.path.exists(OUTPUTS_DIR):
        for f in os.listdir(OUTPUTS_DIR):
            match = re.search(r"job_([\w\d.-]+)_", f)
            if match:
                job_files[match.group(1)].append(f)
    manifest = {}
    if os.path.exists(HOTFOLDER_MANIFEST_PATH):
        with open(HOTFOLDER_MANIFEST_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if "," in line:
                    job_id, filepath = line.strip().split(",", 1)
                    manifest[job_id] = filepath
    return job_files, manifest


def find_source_file(job_id, hotfolder_manifest):
    source_filepath = None
    if job_id.startswith("hotfolder_"):
        source_filepath = hotfolder_manifest.get(job_id)
    else:
        if os.path.exists(UPLOADS_DIR):
            for f in os.listdir(UPLOADS_DIR):
                if f.startswith(job_id):
                    source_filepath = os.path.join(UPLOADS_DIR, f)
                    break
    if source_filepath and os.path.exists(source_filepath):
        return os.path.basename(source_filepath), get_text_from_file(source_filepath)
    return None, "Source file not found."


def read_log_file(lines_to_show=50):
    if not os.path.exists(APP_LOG_PATH):
        return "Log file not found."
    try:
        with open(APP_LOG_PATH, "r", encoding="utf-8") as f:
            return "".join(f.readlines()[-lines_to_show:])
    except Exception as e:
        return f"Error reading log file: {e}"


def update_env_file(settings: dict):
    env_lines = []
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            env_lines = f.readlines()
    for key, value in settings.items():
        found = False
        for i, line in enumerate(env_lines):
            if line.strip().startswith(f"{key}="):
                env_lines[i] = f"{key}={value}\n"
                found = True
                break
        if not found:
            env_lines.append(f"{key}={value}\n")
    with open(".env", "w") as f:
        f.writelines(env_lines)


# --- Sidebar for Configuration and Logs ---
with st.sidebar:
    st.header("⚙️ Configuration")
    current_mode_index = ["SIMPLE", "PARALLEL", "CRITIQUE"].index(
        app_config.OPERATION_MODE
    )
    new_mode = st.selectbox(
        "Operation Mode", ["SIMPLE", "PARALLEL", "CRITIQUE"], index=current_mode_index
    )
    current_model_index = ["gpt", "claude", "gemini"].index(app_config.PRIMARY_MODEL)
    new_model = st.selectbox(
        "Primary Model", ["gpt", "claude", "gemini"], index=current_model_index
    )
    new_dummy_mode = st.toggle("Dummy Mode (API-Free)", value=app_config.DUMMY_MODE)

    if st.button("Save and Reload Service"):
        settings_to_save = {
            "OPERATION_MODE": new_mode,
            "PRIMARY_MODEL": new_model,
            "DUMMY_MODE": new_dummy_mode,
        }
        update_env_file(settings_to_save)
        with open(CONFIG_RELOAD_SIGNAL_PATH, "w") as f:
            pass
        st.success("Configuration saved! Service will reload on its next cycle.")
        time.sleep(2)
        st.rerun()

    st.divider()
    # --- Log Toggle Logic ---
    st.session_state.show_log = st.toggle(
        "Show Service Log", value=st.session_state.show_log
    )
    if st.session_state.show_log:
        st.header("📜 Service Log")
        log_content = read_log_file(lines_to_show=100)
        st.code(log_content, language="log", line_numbers=True)

# --- Main UI Application ---
st.title("Multi-LLM Translation Review")

all_jobs, hotfolder_manifest = get_job_data()
job_ids = ["-- Select a Job to Review --"] + sorted(all_jobs.keys(), reverse=True)
selected_job_id = st.selectbox("Select a Job ID:", job_ids)

if selected_job_id != "-- Select a Job to Review --":
    st.divider()
    st.header(f"Reviewing Job: `{selected_job_id}`")
    with st.expander("View Original Source Text"):
        source_filename, source_content = find_source_file(
            selected_job_id, hotfolder_manifest
        )
        if source_filename:
            st.subheader(f"Source: `{source_filename}`")
            st.text_area("Source Content", source_content, height=300)
        else:
            st.error(source_content)
    job_outputs = all_jobs[selected_job_id]
    critique_report_file = next(
        (f for f in job_outputs if "CRITIQUE_REPORT" in f), None
    )
    if critique_report_file:
        st.subheader("Critique & Refinement Report")
        with open(
            os.path.join(OUTPUTS_DIR, critique_report_file), "r", encoding="utf-8"
        ) as f:
            st.markdown(f.read())
    else:
        st.subheader("Parallel Translation Comparison")
        gpt_file = next((f for f in job_outputs if "gpt" in f), None)
        claude_file = next((f for f in job_outputs if "claude" in f), None)
        gemini_file = next((f for f in job_outputs if "gemini" in f), None)
        col1, col2, col3 = st.columns(3)

        def display_translation(file, service_name, column):
            with column:
                st.subheader(f"{service_name}")
                if file:
                    content = get_text_from_file(os.path.join(OUTPUTS_DIR, file))
                    st.text_area(
                        file, content, height=500, label_visibility="collapsed"
                    )
                else:
                    st.warning("No output file found.")

        display_translation(gpt_file, "GPT-4o-mini", col1)
        display_translation(claude_file, "Claude 3.5 Sonnet", col2)
        display_translation(gemini_file, "Gemini 2.5 Pro", col3)
else:
    st.info(
        "Select a job from the dropdown to see results. The UI will update automatically when new jobs are processed."
    )

time.sleep(5)
st.rerun()
