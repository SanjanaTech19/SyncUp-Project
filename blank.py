import streamlit as st
import requests

# Load secrets directly from Streamlit secrets
url = st.secrets["supabase_url"]
key = st.secrets["supabase_key"]

# Build the REST API endpoint URL
# Note: Ensure URL in secrets doesn't end with a slash
api_url = f"{url}/rest/v1/projects"

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

print(f"--- DIAGNOSTIC START ---")
print(f"Target URL: {api_url}")

try:
    response = requests.get(api_url, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")