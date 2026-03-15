import hashlib
import smtplib
from email.message import EmailMessage
import streamlit as st
from supabase import create_client
from typing import List, Dict, Optional

# --- Configuration ---
# Uses Streamlit's internal secrets management (secrets.toml)
url = st.secrets["supabase_url"]
key = st.secrets["supabase_key"]
supabase = create_client(url, key)

# --- Utilities ---
def get_hash(plain_code: str) -> str:
    """Standardizes input to ensure hashing consistency."""
    return hashlib.sha256(plain_code.strip().lower().encode()).hexdigest()

# --- Auth & Project Logic ---
# --- Updated Logic Functions ---

def create_new_project(client, project_name: str, plain_code: str, user_id: Optional[str] = None) -> bool:
    try:
        hashed_code = get_hash(plain_code)
        data = {"project_name": project_name, "access_code_hash": hashed_code, "user_id": user_id}
        client.table("projects").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Error creating project: {str(e)}")
        return False

def verify_project_code(client, plain_code: str):
    hashed_code = hashlib.sha256(plain_code.encode('utf-8')).hexdigest()
    response = client.table("projects").select("*").execute()
    for row in response.data:
        if row.get('access_code_hash') == hashed_code:
            return row['id']
    return None

def get_project_tasks(client, project_id):
    return client.table("project_tasks") \
                 .select("*") \
                 .eq("project_id", project_id) \
                 .execute().data

def save_availability(client, project_id, email, day, slots):
    client.table("project_availability").delete().eq("project_id", project_id).eq("user_email", email).eq("day", day).execute()
    if slots:
        data = [{"project_id": project_id, "user_email": email, "day": day, "slot": s} for s in slots]
        client.table("project_availability").insert(data).execute()

def get_team_availability(client, project_id):
    return client.table("project_availability").select("user_email, day, slot").eq("project_id", project_id).execute().data

def submit_pulse(client, project_id, score, label):
    data = {"project_id": project_id, "vibe_score": score, "vibe_label": label}
    client.table("project_pulse").insert(data).execute()

def get_pulse_data(client, project_id):
    return client.table("project_pulse").select("vibe_score, vibe_label, submitted_at").eq("project_id", project_id).order("submitted_at", desc=True).limit(20).execute().data

def update_task_with_file(client, task_id, new_progress, file_url):
    try:
        client.table("project_tasks").update({"progress_percentage": new_progress, "file_url": file_url}).eq("id", str(task_id)).execute()
        return True
    except Exception as e:
        st.error(f"Database error: {e}")
        return False