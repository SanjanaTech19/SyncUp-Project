import streamlit as st
import hashlib
from supabase import create_client


url = st.secrets["supabase_url"]
key = st.secrets["supabase_key"]
supabase = create_client(url, key)

# Only run this when YOU want to add a new project
def create_new_project(project_name, plain_code):
    hashed_code = hashlib.sha256(plain_code.encode('utf-8')).hexdigest()
    
    # Save to Supabase
    data = {"name": project_name, "access_code_hash": hashed_code}
    supabase.table("projects").insert(data).execute()
    st.success(f"Project '{project_name}' created!")

# UI for you to add future projects easily
if st.checkbox("Admin Mode"):
    new_name = st.text_input("Project Name")
    new_code = st.text_input("Access Code")
    if st.button("Add Project"):
        create_new_project(new_name, new_code)