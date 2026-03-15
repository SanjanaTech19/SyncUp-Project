import streamlit as st
import pandas as pd
import plotly.express as px
from db import supabase
from supabase import create_client
from logic import verify_project_code, create_new_project, get_project_tasks, send_nudge_email, update_task_progress , save_availability , get_team_availability, submit_pulse, get_pulse_data, get_file_hub_data, update_task_with_file



def get_authenticated_client():
    url = st.secrets["supabase_url"]
    key = st.secrets["supabase_key"]
    supabase = create_client(url, key)
    
    # This is the "Magic" part that makes RLS work
    if "session" in st.session_state and st.session_state["session"]:
        session = st.session_state["session"]
        supabase.auth.set_session(session.access_token, session.refresh_token)
    
    return supabase


client = get_authenticated_client()





# --- PAGE CONFIG ---
st.set_page_config(page_title="SyncUp Portal", layout="wide")

# --- CUSTOM BRANDING (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #E6E6FA; }
    [data-testid="stSidebar"] { background-color: #FFDAB9; }
    div.stButton > button:first-child { 
        background-color: #90EE90; color: #000000; border-radius: 8px; border: 1px solid #77DD77; 
    }
    div.stButton > button:first-child:hover { background-color: #77DD77; }
    </style>
    """, unsafe_allow_html=True)

# --- STATE MANAGEMENT ---
if "step" not in st.session_state: st.session_state.step = "login"
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "project_id" not in st.session_state: st.session_state.project_id = None

# --- AUTH FLOW ---
if not st.session_state.authenticated:
    if st.session_state.step == "login":
        col1, col2 = st.columns([1, 1])
        with col1:
            st.title("Welcome to SyncUp 🚀")
            st.subheader("Conflict-free collaboration for modern teams.")
            st.write("Stop ghosting and start building. SyncUp automates your scheduling and team health tracking.")
            if st.button("Start"): 
                st.session_state.step = "choice"
                st.rerun()
        
        with col2:
            # You can place your image here
            st.image("assets/homescreen.jpg", 
                     use_container_width=True)
        
        st.divider()
        

    elif st.session_state.step == "choice":
        choice = st.radio("What would you like to do?", ["Create New Project", "Open Existing Project"])
        if st.button("Continue"): st.session_state.step = "create" if choice == "Create New Project" else "open"; st.rerun()
    elif st.session_state.step == "create":
        name = st.text_input("Project Name")
        code = st.text_input("Set Code", type="password")
        if st.button("Register"): 
            create_new_project(client,name, code)
            st.session_state.step = "login"
            st.rerun()
    elif st.session_state.step == "open":
        code = st.text_input("Enter Code", type="password")
        if st.button("Access"):
            pid = verify_project_code(client ,code)
            if pid: 
                st.session_state.project_id = pid
                st.session_state.authenticated = True
                st.rerun()
            else: st.error("Invalid Code")
    st.stop() 

# --- MAIN APP INTERFACE ---
st.sidebar.title("SyncUp Navigation")
page = st.sidebar.selectbox("Go to", ["Dashboard", "Project Status", "Team Nudge", "Analytics","Smart Slot","Pulse Check","File Hub"])


tasks = get_project_tasks(client, st.session_state.project_id)

if page == "Dashboard":
    st.title("🚀 Project SyncUp Dashboard")
    with st.expander("➕ Create New Task"):
        with st.form("task_form", clear_on_submit=True):
            t_name = st.text_input("Task Name")
            t_email = st.text_input("Assign to Email")
            submit = st.form_submit_button("Add Task")
            if submit and t_name and t_email:
                new_data = {"task_name": t_name, "assigned_email": t_email, "progress_percentage": 0, "project_id": st.session_state.project_id}
                supabase.table("project_tasks").insert(new_data).execute()
                st.success(f"Task '{t_name}' added!")
                st.rerun()
    if tasks:
        df = pd.DataFrame(tasks)
        c1, _, c3 = st.columns(3)
        c1.metric("Tasks In Progress", len(df[df['progress_percentage'] < 100]))
        c3.metric("Avg Progress", f"{df['progress_percentage'].mean():.1f}%")
        fig = px.bar(df, x='assigned_email', y='progress_percentage', title="Team Workload")
        st.plotly_chart(fig, width='stretch')

elif page == "Analytics":
    st.title("📊 Project Analytics")
    if tasks:
        df = pd.DataFrame(tasks)
        fig_pie = px.pie(df, names='assigned_email', title="Responsibility Breakdown")
        st.plotly_chart(fig_pie, width='stretch')

elif page == "Project Status":
    st.title("📋 Project Status")
    for task in tasks:
        with st.container(border=True):
            st.write(f"### {task['task_name']}")
        
            c1, c2 = st.columns([2, 1])
        
            with c1:
                new_val = st.slider("Progress", 0, 100, int(task.get('progress_percentage', 0)), key=f"slide_{task['id']}")
            
            # File URL Input (The new piece)
                existing_url = task.get('file_url', "")
                new_url = st.text_input("Resource Link", value=existing_url, key=f"url_{task['id']}")
            
            with c2:
                if st.button("Save Changes", key=f"save_{task['id']}"):
                    if update_task_progress(client, task['id'], new_val):
                        st.toast("Updated successfully!")
                        st.rerun()

elif page == "Team Nudge":
    st.title("🔔 Automated Nudge Hub")
    if "nudge_history" not in st.session_state: st.session_state.nudge_history = []
    for task in tasks:
        col1, col2 = st.columns([3, 1])
        with col1: st.write(f"**Task:** {task['task_name']} | **Owner:** {task['assigned_email']}")
        with col2:
            if st.button(f"Nudge", key=f"nudge_{task['id']}"):
                if send_nudge_email(task['assigned_email'], task['task_name']):
                    st.toast(f"Nudge sent to {task['assigned_email']}!")
                    st.session_state.nudge_history.append(f"Nudged {task['assigned_email']} for '{task['task_name']}'")
    st.divider()
    st.subheader("📜 Nudge Audit Trail")
    for entry in st.session_state.nudge_history: st.text(f"✅ {entry}")

elif page == "Smart Slot":
    st.title("📅 Smart Slot Finder")
    
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    slots = ["Morning", "Afternoon", "Evening", "Night"]

    # --- USER INPUT ---
    with st.expander("Update My Availability"):
        with st.form("avail_form"):
            u_email = st.text_input("Your Email")
            u_day = st.selectbox("Select Day", days)
            u_slots = st.multiselect("When are you free?", slots)
            if st.form_submit_button("Save My Slots"):
                save_availability(st.session_state.project_id, u_email, u_day, u_slots)
                st.success("Availability updated!")
                st.rerun()

    # --- HEATMAP LOGIC ---
    raw_data = get_team_availability(st.session_state.project_id)
    
    if raw_data:
        # Create an empty matrix
        df_map = pd.DataFrame(0, index=slots, columns=days)
        
        # Populate counts
        for entry in raw_data:
            if entry['slot'] in slots and entry['day'] in days:
                df_map.at[entry['slot'], entry['day']] += 1
        
        st.subheader("Team Availability Heatmap")
        st.write("Darker colors indicate more people are free.")
        
        # Use Plotly for the Heatmap
        fig = px.imshow(
            df_map, 
            labels=dict(x="Day", y="Time of Day", color="People Free"),
            color_continuous_scale="Viridis"
        )
        st.plotly_chart(fig, width='stretch')
        
        # Simple breakdown
        st.dataframe(df_map)
    else:
        st.info("No availability data yet. Ask your team to input their schedules!")


elif page == "Pulse Check":
    st.title("💓 Team Pulse Check")
    st.write("How are you feeling about the project right now? (Anonymous)")

    # 1. Submission Section
    col1, col2 = st.columns([1, 2])
    
    with col1:
        vibe_options = {
            1: "🆘 Overwhelmed",
            2: "📉 Struggling",
            3: "😐 Just Okay",
            4: "📈 Productive",
            5: "🚀 Crushing It!"
        }
        
        score = st.radio("Select your vibe:", options=list(vibe_options.keys()), 
                         format_func=lambda x: vibe_options[x])
        
        if st.button("Submit Pulse"):
            submit_pulse(st.session_state.project_id, score, vibe_options[score])
            st.toast("Mood submitted anonymously!", icon="🙏")
            st.rerun()

    # 2. Visualization Section
    with col2:
        pulse_data = get_pulse_data(st.session_state.project_id)
        if pulse_data:
            df_pulse = pd.DataFrame(pulse_data)
            avg_vibe = df_pulse['vibe_score'].mean()
            
            # Display a Metric
            st.metric("Team Energy Level", f"{avg_vibe:.1f} / 5.0")
            
            # Show a distribution chart
            fig = px.histogram(df_pulse, x="vibe_label", 
                               category_orders={"vibe_label": list(vibe_options.values())},
                               color="vibe_label",
                               title="Current Team Mood Distribution")
            st.plotly_chart(fig, width='stretch')

elif page == "File Hub":
    st.title("📂 Central File Hub")
    st.write("Access all project resources and deliverables in one place.")

    # Pass 'client' here!
    files = get_file_hub_data(client, st.session_state.project_id)

    if files:
        search = st.text_input("Search for a specific file or task...", placeholder="e.g. Report, Design, etc.")
        for f in files:
            if search.lower() in f['task_name'].lower():
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"### {f['task_name']}")
                        st.caption(f"Owner: {f.get('assigned_email', 'Unassigned')} | Progress: {f['progress_percentage']}%")
                    with col2:
                        st.link_button("Open Resource", f['file_url'], use_container_width=True)
    else:
        st.info("No files found. Link files in the 'Project Status' page to see them here.")