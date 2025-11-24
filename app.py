import streamlit as st
import google.generativeai as genai
import sqlite3
import hashlib
import uuid
import json
from datetime import datetime
import os

# ---------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------

# Load API Key
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    API_KEY = os.getenv("GEMINI_API_KEY", "")

if API_KEY:
    genai.configure(api_key=API_KEY)

BOT_AVATAR = "https://raw.githubusercontent.com/Joseph1997-eng/Joseph-AI/main/joseph.JPG"

# Load System Prompt
def load_system_prompt():
    try:
        return st.secrets["SYSTEM_PROMPT"]
    except:
        try:
            with open("system_prompt.txt", "r", encoding="utf-8") as f:
                return f.read()
        except:
            return """You are a helpful AI assistant named Leoliver (Joseph). 
You communicate in Lai language (Hakha dialect) and are wise, friendly, and caring."""

def load_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except:
        pass

# ---------------------------------------------------------
# 2. REMEMBER LOGIN (Cookie Storage)
# ---------------------------------------------------------

def save_credentials(username, password):
    """Save login credentials to browser local storage"""
    credentials = {"username": username, "password": password}
    st.session_state['saved_credentials'] = json.dumps(credentials)
    
def load_saved_credentials():
    """Load saved credentials"""
    if 'saved_credentials' in st.session_state:
        try:
            return json.loads(st.session_state['saved_credentials'])
        except:
            return None
    return None

def clear_saved_credentials():
    """Clear saved credentials"""
    if 'saved_credentials' in st.session_state:
        del st.session_state['saved_credentials']

# ---------------------------------------------------------
# 3. DATABASE FUNCTIONS
# ---------------------------------------------------------

def init_db():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS userstable(username TEXT PRIMARY KEY, password TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS chathistory(session_id TEXT, username TEXT, role TEXT, content TEXT, timestamp TEXT)')
    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def add_userdata(username, password):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO userstable(username,password) VALUES (?,?)', (username, password))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('SELECT * FROM userstable WHERE username =? AND password = ?', (username, password))
    data = c.fetchall()
    conn.close()
    return data

def save_chat_message(session_id, username, role, content):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('INSERT INTO chathistory(session_id, username, role, content, timestamp) VALUES (?,?,?,?,?)', 
              (session_id, username, role, content, ts))
    conn.commit()
    conn.close()

def get_chat_history(session_id):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('SELECT role, content FROM chathistory WHERE session_id=? ORDER BY timestamp', (session_id,))
    data = c.fetchall()
    conn.close()
    return data

def get_user_sessions(username):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        SELECT session_id, MAX(timestamp) as last_time
        FROM chathistory 
        WHERE username=? 
        GROUP BY session_id 
        ORDER BY last_time DESC
        LIMIT 20
    ''', (username,))
    data = c.fetchall()
    conn.close()
    return data

def delete_chat_session(session_id):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('DELETE FROM chathistory WHERE session_id=?', (session_id,))
    conn.commit()
    conn.close()

def delete_all_sessions(username):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('DELETE FROM chathistory WHERE username=?', (username,))
    conn.commit()
    conn.close()

# ---------------------------------------------------------
# 4. MODEL SETTINGS
# ---------------------------------------------------------

system_prompt = load_system_prompt()
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=system_prompt,
    generation_config=genai.GenerationConfig(temperature=0.8, max_output_tokens=4000)
)

# ---------------------------------------------------------
# 5. MAIN APP
# ---------------------------------------------------------

def main():
    st.set_page_config(
        page_title="Joseph's AI Assistant",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    load_css("style.css")
    init_db()

    # Session State
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "username" not in st.session_state:
        st.session_state["username"] = ""
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())
    if "remember_me" not in st.session_state:
        st.session_state["remember_me"] = False

    # Try auto-login if credentials saved
    if not st.session_state["logged_in"]:
        saved_creds = load_saved_credentials()
        if saved_creds:
            if login_user(saved_creds['username'], saved_creds['password']):
                st.session_state["logged_in"] = True
                st.session_state["username"] = saved_creds['username']
                st.rerun()

    # ---------------------------------------------------------
    # LOGIN PAGE
    # ---------------------------------------------------------
    if not st.session_state["logged_in"]:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"""
            <div class='login-container'>
                <img src='{BOT_AVATAR}' class='login-logo'>
                <h1 class='app-title'>Joseph's AI Assistant</h1>
                <p class='app-subtitle'>LAI HOLH AI</p>
            </div>
            """, unsafe_allow_html=True)
            
            tab1, tab2 = st.tabs(["Sign In", "Register"])
            
            with tab1:
                with st.form("login_form"):
                    u = st.text_input("Username", placeholder="Na min Tialnak")
                    p = st.text_input("Password", type='password', placeholder="Password Tialnak")
                    remember = st.checkbox("Remember Me", value=True)
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        login_btn = st.form_submit_button("Login", use_container_width=True)
                    
                    if login_btn:
                        if u and p:
                            hp = make_hashes(p)
                            if login_user(u, hp):
                                st.session_state["logged_in"] = True
                                st.session_state["username"] = u
                                
                                if remember:
                                    save_credentials(u, hp)
                                
                                st.success("✅ Login successful!")
                                st.rerun()
                            else:
                                st.error("❌ Invalid credentials!")
                        else:
                            st.warning("⚠️ Please fill all fields!")
            
            with tab2:
                with st.form("register_form"):
                    nu = st.text_input("Username", placeholder="Min Thar Tialnak")
                    np = st.text_input("Password", type='password', placeholder="Password Thar Tialnak")
                    np2 = st.text_input("Confirm Password", type='password', placeholder="Password Thar Tial Thannak")
                    
                    register_btn = st.form_submit_button("Register", use_container_width=True)
                    
                    if register_btn:
                        if nu and np and np2:
                            if np != np2:
                                st.error("❌ Passwords don't match!")
                            elif len(np) < 6:
                                st.error("❌ Password must be 6+ characters!")
                            else:
                                if add_userdata(nu, make_hashes(np)):
                                    st.success("✅ Account created! Please sign in.")
                                else:
                                    st.error("❌ Username exists!")
                        else:
                            st.warning("⚠️ Please fill all fields!")

    # ---------------------------------------------------------
    # CHAT PAGE
    # ---------------------------------------------------------
    else:
        # Sidebar
        with st.sidebar:
            st.markdown(f"### 👤 {st.session_state['username']}")
            
            if st.button("➕ New Chat", use_container_width=True):
                st.session_state["session_id"] = str(uuid.uuid4())
                st.rerun()
            
            st.markdown("---")
            st.markdown("### 📝 Chat History")
            
            sessions = get_user_sessions(st.session_state["username"])
            if sessions:
                if st.button("🗑️ Clear All", use_container_width=True, type="secondary"):
                    delete_all_sessions(st.session_state["username"])
                    st.session_state["session_id"] = str(uuid.uuid4())
                    st.rerun()
                
                for sess_id, ts in sessions:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        is_current = (sess_id == st.session_state["session_id"])
                        if st.button(
                            f"{'📍' if is_current else '📅'} {ts[:16]}", 
                            key=f"s_{sess_id[:8]}", 
                            use_container_width=True,
                            type="primary" if is_current else "secondary"
                        ):
                            st.session_state["session_id"] = sess_id
                            st.rerun()
                    with col2:
                        if st.button("🗑️", key=f"d_{sess_id[:8]}"):
                            delete_chat_session(sess_id)
                            if sess_id == st.session_state["session_id"]:
                                st.session_state["session_id"] = str(uuid.uuid4())
                            st.rerun()
            else:
                st.info("No history yet")
            
            st.markdown("---")
            
            if st.button("🚪 Logout", use_container_width=True, type="secondary"):
                clear_saved_credentials()
                st.session_state["logged_in"] = False
                st.session_state["username"] = ""
                st.rerun()

        # Main Chat Area
        st.markdown(f"""
        <div class='chat-header'>
            <img src='{BOT_AVATAR}' class='header-avatar'>
            <div>
                <h2>Joseph's AI Assistant</h2>
                <p>Hello, {st.session_state['username']}! 👋</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Display Messages
        db_messages = get_chat_history(st.session_state["session_id"])
        
        if not db_messages:
            st.markdown("""
            <div class='welcome-box'>
                <h3>👋 Welcome!</h3>
                <p>I'm here to help you in Lai language. Ask me anything!</p>
            </div>
            """, unsafe_allow_html=True)
        
        for role, content in db_messages:
            with st.chat_message(role, avatar=BOT_AVATAR if role == "assistant" else "👤"):
                st.markdown(content)

        # File Upload
        uploaded_file = st.file_uploader(
            "📎 Upload file (optional)",
            type=["pdf", "jpg", "png", "jpeg", "txt", "mp4"]
        )

        # Chat Input
        user_input = st.chat_input(" 💭Bia Halnak...")
        
        if user_input:
            save_chat_message(st.session_state["session_id"], st.session_state["username"], "user", user_input)
            st.rerun()

        # Generate Response
        if db_messages and db_messages[-1][0] == 'user':
            current_prompt = db_messages[-1][1]
            
            with st.chat_message("assistant", avatar=BOT_AVATAR):
                with st.spinner("Thinking..."):
                    try:
                        gemini_hist = []
                        for r, c in db_messages[:-1]:
                            role_name = "model" if r == "assistant" else "user"
                            gemini_hist.append({"role": role_name, "parts": [c]})
                        
                        user_context = f"[User: {st.session_state['username']}]. "
                        full_prompt = user_context + current_prompt

                        if uploaded_file:
                            inputs = [
                                {"mime_type": uploaded_file.type, "data": uploaded_file.getvalue()}, 
                                full_prompt
                            ]
                            response = model.generate_content(inputs)
                        else:
                            chat = model.start_chat(history=gemini_hist)
                            response = chat.send_message(full_prompt)
                        
                        final_text = response.text.replace("*", "")
                        st.markdown(final_text)
                        
                        save_chat_message(st.session_state["session_id"], st.session_state["username"], "assistant", final_text)
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    main()
