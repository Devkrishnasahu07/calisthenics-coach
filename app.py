import streamlit as st
import asyncio
import json
import os
import cv2
from coach import generate_workout, speak_workout
from vision import FormTracker

# Configure the web page
st.set_page_config(page_title="AI Calisthenics Coach", page_icon="🦾", layout="wide")

# --- AUTHENTICATION & PROGRESS SYSTEM ---
USER_FILE = "users.json"
PROGRESS_FILE = "progress.json"

def load_users():
    if not os.path.exists(USER_FILE):
        return {}
    with open(USER_FILE, "r") as f:
        return json.load(f)

def save_user(username, password):
    users = load_users()
    if username in users:
        return False
    users[username] = password
    with open(USER_FILE, "w") as f:
        json.dump(users, f)
    return True

def authenticate(username, password):
    users = load_users()
    return users.get(username) == password

def load_user_progress(username):
    if not os.path.exists(PROGRESS_FILE):
        return {"total_workouts": 0, "favorite": "-", "streak": 0, "history": {"Activity": [0]}}
    with open(PROGRESS_FILE, "r") as f:
        data = json.load(f)
    return data.get(username, {"total_workouts": 0, "favorite": "-", "streak": 0, "history": {"Activity": [0]}})

def update_user_progress(username, exercise, reps):
    if not os.path.exists(PROGRESS_FILE):
        data = {}
    else:
        with open(PROGRESS_FILE, "r") as f:
            data = json.load(f)
    
    user_data = data.get(username, {"total_workouts": 0, "favorite": exercise, "streak": 1, "history": {}})
    user_data["total_workouts"] += 1
    user_data["favorite"] = exercise
    
    if exercise not in user_data["history"]:
        user_data["history"][exercise] = [0]
    user_data["history"][exercise].append(reps)
    
    data[username] = user_data
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f)

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- LOGIN / SIGNUP SCREEN ---
if not st.session_state.logged_in:
    st.title("🦾 Welcome to AI Calisthenics Coach")
    st.write("Please log in or create an account to access your personal AI trainer.")
    
    tab_login, tab_signup = st.tabs(["🔒 Login", "📝 Sign Up"])
    
    with tab_login:
        st.subheader("Login to your account")
        login_user = st.text_input("Username", key="login_user")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", type="primary"):
            if authenticate(login_user, login_pass):
                st.session_state.logged_in = True
                st.session_state.username = login_user
                st.session_state.messages = []
                st.experimental_rerun()
            else:
                st.error("Invalid username or password.")
                
    with tab_signup:
        st.subheader("Create a new account")
        new_user = st.text_input("Choose a Username", key="new_user")
        new_pass = st.text_input("Choose a Password", type="password", key="new_pass")
        if st.button("Sign Up"):
            if new_user and new_pass:
                if save_user(new_user, new_pass):
                    st.success("Account created successfully! You can now log in.")
                else:
                    st.error("That username already exists. Try another one.")
            else:
                st.warning("Please fill in both fields.")

# --- MAIN APP (ONLY VISIBLE IF LOGGED IN) ---
else:
    with st.sidebar:
        st.title("Profile")
        st.write(f"👤 **Logged in as:** {st.session_state.username}")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.messages = []
            st.experimental_rerun()

    st.title("🦾 AI Calisthenics Coach")
    st.write(f"Welcome back, **{st.session_state.username}**! Your local, voice-activated personal trainer powered by Gemma 2.")

    tab1, tab2, tab3 = st.tabs(["💬 AI Coach", "📊 Progress Dashboard", "📹 Live Form Tracker"])

    with tab1:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.write(message["content"])
                else:
                    workout = message["content"]
                    st.subheader(f"🏋️‍♂️ {workout.get('exercise', 'Freestyle')}")
                    st.write(f"**Reps:** {workout.get('reps', '10')} | **Rest:** {workout.get('rest_seconds', '30')} seconds")
                    st.info(f"🗣️ {workout.get('coach_message', 'Keep pushing hard!')}")

        if user_state := st.chat_input("How are you feeling today? (e.g., '10 mins, sore arms')"):
            with st.chat_message("user"):
                st.write(user_state)
            st.session_state.messages.append({"role": "user", "content": user_state})

            with st.chat_message("assistant"):
                with st.spinner("Analyzing and generating routine..."):
                    workout = asyncio.run(generate_workout(user_state))
                    
                    st.subheader(f"🏋️‍♂️ {workout.get('exercise', 'Freestyle')}")
                    st.write(f"**Reps:** {workout.get('reps', '10')} | **Rest:** {workout.get('rest_seconds', '30')} seconds")
                    st.info(f"🗣️️ {workout.get('coach_message', 'Keep pushing hard!')}")
                    
                    if workout.get("exercise") == "Penalty Burpees":
                        st.error("🚨 OFF-TOPIC DETECTED: PENALTY INITIATED 🚨")
                        st.snow()
                    
                    speak_workout(workout)
                    
                    update_user_progress(
                        st.session_state.username, 
                        workout.get("exercise", "Freestyle"), 
                        workout.get("reps", 10)
                    )
                    
            st.session_state.messages.append({"role": "assistant", "content": workout})

    with tab2:
        st.header("Your Fitness Journey")
        user_stats = load_user_progress(st.session_state.username)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Workouts", user_stats["total_workouts"])
        col2.metric("Favorite Exercise", user_stats["favorite"])
        col3.metric("Consistency", f"{user_stats['streak']} Day Streak", "🔥" if user_stats['streak'] > 0 else "")
        
        st.subheader("Reps Over Time")
        st.line_chart(user_stats["history"])

    with tab3:
        st.header("Live Computer Vision Rep Counter")
        st.write("Turn on your webcam to track your form and count reps automatically.")
        
        col_cam, col_stats = st.columns([3, 1])
        
        with col_stats:
            rep_metric = st.empty()
            stage_metric = st.empty()
            start_tracking = st.toggle("Activate Webcam")
        
        with col_cam:
            frame_placeholder = st.empty()

        if start_tracking:
            tracker = FormTracker()
            cap = cv2.VideoCapture(0)
            
            while start_tracking and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    st.error("Unable to access the webcam.")
                    break
                
                # Process the frame through MediaPipe
                processed_frame, count, stage = tracker.process_frame(frame)
                
                # Render the webcam stream
                frame_placeholder.image(processed_frame, channels="BGR", use_container_width=True)
                
                # Update metrics live on screen
                rep_metric.metric("Reps Completed", count)
                stage_metric.metric("Stage", stage if stage else "Ready")
            
            cap.release()
            frame_placeholder.empty()