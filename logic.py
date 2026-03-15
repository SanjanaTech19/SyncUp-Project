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
def create_new_project(project_name: str, plain_code: str, user_id: Optional[str] = None) -> bool:
    """Registers a new project including the user_id for future security."""
    try:
        hashed_code = get_hash(plain_code)
        
        # We include 'user_id' in our dictionary
        data = {
            "project_name": project_name, 
            "access_code_hash": hashed_code,
            "user_id": user_id  # If this is None, Supabase will just leave it empty
        }
        
        response = supabase.table("projects").insert(data).execute()
        print(f"DEBUG: Successfully created project for user: {user_id}")
        return True
    except Exception as e:
        print(f"DEBUG: CRITICAL INSERT ERROR: {str(e)}")
        st.error(f"Error creating project: {str(e)}")
        return False

def verify_project_code(plain_code: str):
    # 1. Generate the hash
    hashed_code = hashlib.sha256(plain_code.encode('utf-8')).hexdigest()
    print(f"DEBUG: Input: '{plain_code}' -> My Hash: '{hashed_code}'")

    # 2. Query the database
    response = supabase.table("projects").select("*").execute()
    
    # 3. Inspect the database data
    if not response.data:
        print("DEBUG: Database table is empty or inaccessible.")
        return None
        
    for row in response.data:
        db_hash = row.get('access_code_hash')
        print(f"DEBUG: Comparing '{hashed_code}' with DB Hash: '{db_hash}'")
        
        if db_hash == hashed_code:
            return row['id']
            
    return None
# --- Task & Progress Logic ---
# In logic.py
def get_project_tasks(project_id):
    
    return supabase.table("project_tasks") \
                   .select("*") \
                   .eq("project_id", project_id) \
                   .execute().data

def update_task_progress(task_id: str, new_percentage: int) -> bool:
    """Updates task progress using an atomic database operation."""
    try:
        supabase.table("project_tasks") \
            .update({"progress_percentage": new_percentage}) \
            .eq("id", task_id) \
            .execute()
        return True
    except Exception as e:
        st.error(f"Database error: {e}")
        return False

def send_nudge_email(email: str, task_name: str) -> bool:
    # 1. Setup the email content
    msg = EmailMessage()
    msg['Subject'] = f"Nudge: Time to check in on {task_name}"
    msg['From'] = st.secrets["EMAIL_USER"]
    msg['To'] = email
    msg.set_content(f"Hi there,\n\nThis is a friendly nudge from SyncUp. Please check in on your task: {task_name}.\n\nKeep up the great work!")

    # 2. Connect to the email server (using Gmail as an example)
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(st.secrets["EMAIL_USER"], st.secrets["EMAIL_PASS"])
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

def save_availability(project_id, email, day, slots):
    # First, clear existing slots for this user on this day to avoid duplicates
    supabase.table("project_availability")\
            .delete()\
            .eq("project_id", project_id)\
            .eq("user_email", email)\
            .eq("day", day)\
            .execute()
    
    # Insert new slots
    if slots:
        data = [{"project_id": project_id, "user_email": email, "day": day, "slot": s} for s in slots]
        supabase.table("project_availability").insert(data).execute()

def get_team_availability(project_id):
    response = supabase.table("project_availability")\
                       .select("user_email, day, slot")\
                       .eq("project_id", project_id)\
                       .execute()
    return response.data

def submit_pulse(project_id, score, label):
    data = {
        "project_id": project_id,
        "vibe_score": score,
        "vibe_label": label
    }
    supabase.table("project_pulse").insert(data).execute()

def get_pulse_data(project_id):
    # Fetch the last 20 entries to see the recent mood
    response = supabase.table("project_pulse")\
                       .select("vibe_score, vibe_label, submitted_at")\
                       .eq("project_id", project_id)\
                       .order("submitted_at", desc=True)\
                       .limit(20)\
                       .execute()
    return response.data

def get_file_hub_data(project_id):
    # Updated to use the correct column name: 'assigned_email'
    response = supabase.table("project_tasks") \
        .select("task_name, file_url, progress_percentage, assigned_email") \
        .eq("project_id", project_id) \
        .neq("file_url", "") \
        .not_.is_("file_url", "null") \
        .execute()
    return response.data

def update_task_with_file(task_id, new_progress, file_url):
    # This ensures both the progress and the link go to the database
    try:
        supabase.table("project_tasks") \
                .update({
                    "progress_percentage": new_progress,
                    "file_url": file_url  # Make sure this matches your DB column name!
                }) \
                .eq("id", str(task_id)) \
                .execute()
        return True
    except Exception as e:
        st.error(f"Database error: {e}")
        return False