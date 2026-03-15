# db.py
import streamlit as st
from supabase import create_client

url = st.secrets["supabase_url"]
key = st.secrets["supabase_key"]

# This creates the client instance named 'supabase'
supabase = create_client(url, key)