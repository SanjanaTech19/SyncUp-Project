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
# --- Add this helper in logic.py ---
def _generate_hash(code: str) -> str:
    # Always strip whitespace and convert to lowercase before hashing
    return hashlib.sha256(code.strip().lower().encode('utf-8')).hexdigest()

# --- Now update your logic functions ---
def create_new_project(client, project_name: str, plain_code: str, user_id: Optional[str] = None) -> bool:
    try:
        hashed_code = _generate_hash(plain_code) # Use the helper
        data = {"project_name": project_name, "access_code_hash": hashed_code, "user_id": user_id}
        client.table("projects").insert(data).execute()
        return True
    except Exception as e:
        return False

def verify_project_code(client, plain_code: str):
    hashed_code = _generate_hash(plain_code) # Use the helper
    response = client.table("projects").select("id, access_code_hash").execute()
    
    
    st.write(f"DEBUG: Input: {plain_code} | Hash: {hashed_code}")
    
    
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

def send_nudge_email(email: str, task_name: str) -> bool:
    """Sends a friendly nudge email to a team member."""
    # 1. Setup the email content
    msg = EmailMessage()
    msg['Subject'] = f"SyncUp Nudge: {task_name}"
    msg['From'] = st.secrets["EMAIL_USER"]
    msg['To'] = email
    msg.set_content(f"Hi there,\n\nThis is a friendly nudge from SyncUp. Please check in on your task: '{task_name}'.\n\nKeep up the great work!")

    # 2. Connect to the email server (using Gmail as an example)
    try:
        # Note: Use port 465 for SSL or 587 for TLS
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False
    
def update_task_progress(client, task_id: str, new_percentage: int) -> bool:
    """Updates task progress using an authenticated client."""
    try:
        client.table("project_tasks") \
            .update({"progress_percentage": new_percentage}) \
            .eq("id", str(task_id)) \
            .execute()
        return True
    except Exception as e:
        # In a production app, logging the error is better than just showing it to the user
        st.error(f"Database error: {e}")
        return False
    
def get_file_hub_data(client, project_id: str) -> List[Dict]:
    """
    Fetches task data for the File Hub, filtering only for tasks 
    that have an associated file_url.
    """
    try:
        response = client.table("project_tasks") \
            .select("task_name, file_url, progress_percentage, assigned_email") \
            .eq("project_id", project_id) \
            .not_.is_("file_url", "null") \
            .neq("file_url", "") \
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error fetching file hub data: {e}")
        return []