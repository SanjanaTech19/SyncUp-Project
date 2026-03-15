import streamlit as st
from supabase import create_client

# Accessing secrets directly from the top level as defined in the flat secrets.toml
url = st.secrets["supabase_url"]
key = st.secrets["supabase_key"]

# Initialize the official Supabase client
supabase = create_client(url, key)

def handle_login(email, password):
    """
    Handles user authentication using the Supabase Python SDK [cite: 2026-03-08].
    """
    try:
        # Use the official client to sign in 
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        
        # Store user info in session state 
        st.session_state.user = response.user
        st.session_state.authenticated = True
        return True, "Login successful!"
    except Exception as e:
        # Return error message to display in UI
        return False, str(e)

def logout():
    """
    Clears the session state and signs the user out [cite: 2026-03-08].
    """
    st.session_state.authenticated = False
    st.session_state.user = None
    st.rerun() # Refresh to show login screen 

def handle_signup(email, password):
    """
    Attempts to create a new user via Supabase [cite: 2026-03-08].
    """
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
        return True, "Sign-up successful! Please check your email for confirmation."
    except Exception as e:
        return False, str(e)