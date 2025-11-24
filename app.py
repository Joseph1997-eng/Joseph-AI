import streamlit as st
import google.generativeai as genai
import sqlite3
import hashlib
import uuid
from datetime import datetime
import os

# ---------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    API_KEY = os.getenv("GEMINI_API_KEY", "")

if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.error("⚠️ API Key not found!")

BOT_AVATAR = "https://raw.githubusercontent.com/Joseph1997-eng/Joseph-AI/main/joseph.JPG"

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
# 2. DATABASE FUNCTIONS
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
# 3. MODEL SETTINGS
# ---------------------------------------------------------

system_prompt = load_system_prompt()
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=system_prompt,
    generation_config=genai.GenerationConfig(temperature=0.8, max_output_tokens=4000)
)

# ---------------------------------------------------------
# 4. COPY BUTTON
# ---------------------------------------------------------

def create_copy_button_html(text, unique_id):
    import json
    text_json = json.dumps(text)
    
    return f"""
    <div style="margin-bottom: 10px; text-align: right;">
        <button id="copy_btn_{unique_id}" onclick="copyText_{unique_id}()" 
                style="background: linear-gradient(90deg, #667eea, #764ba2); color: white; border: none; 
                       border-radius: 8px; padding: 8px 16px; cursor: pointer; font-size: 13px; 
                       font-weight: 500; transition: all 0.3s; box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);"
                onmouseover="this.style.transform='scale(1.05)';" 
                onmouseout="this.style.transform='scale(1)';">
            📋 Copy
        </button>
    </div>
    <script>
    function copyText_{unique_id}() {{
        const text = {text_json};
        if (navigator.clipboard) {{
            navigator.clipboard.writeText(text).then(() => {{
                const btn = document.getElementById('copy_btn_{unique_id}');
                btn.innerHTML = '✅ Copied!';
                btn.style.background = 'linear-gradient(90deg, #22c55e, #16a34a)';
                setTimeout(() => {{
                    btn.innerHTML = '📋 Copy';
                    btn.style.background = 'linear-gradient(90deg, #667eea, #764ba2)';
                }}, 2000);
            }});
        }}
    }}
    </script>
    """

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
            
            tab1, tab2 = st.tabs(["🔐 Sign In", "📝 Register"])
            
            with tab1:
                with st.form("login_form"):
                    u = st.text_input("Username", placeholder="Min Tialnak")
                    p = st.text_input("Password", type='password', placeholder="Password Tialnak")
                    
                    if st.form_submit_button("Login", use_container_width=True):
                        if u and p:
                            hp = make_hashes(p)
                            if login_user(u, hp):
                                st.session_state["logged_in"] = True
                                st.session_state["username"] = u
                                st.success("✅ Login successful!")
                                st.rerun()
                            else:
                                st.error("❌ Invalid credentials!")
                        else:
                            st.warning("⚠️ Fill all fields!")
            
            with tab2:
                with st.form("register_form"):
                    nu = st.text_input("Username", placeholder="Min Thar Tialnak")
                    np = st.text_input("Password", type='password', placeholder="Password Thar Tialnak")
                    np2 = st.text_input("Confirm Password", type='password', placeholder="Password Thar Tial Thannak")
                    
                    if st.form_submit_button("Register", use_container_width=True):
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
                            st.warning("⚠️ Fill all fields!")
            
            st.markdown("""
            <div class='login-footer'>
                <p><a href='https://github.com/Joseph1997-eng' target='_blank'>GitHub</a> | 
                   <a href='mailto:josephsaimonn@gmail.com'>Email</a></p>
                <p class='copyright'>© 2025 Joseph's Assistant</p>
            </div>
            """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # CHAT PAGE
    # ---------------------------------------------------------
    else:
        # SIDEBAR
        with st.sidebar:
            st.markdown(f"""
            <div class="user-profile">
                <div class="profile-avatar">👤</div>
                <div class="profile-name">{st.session_state['username']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("➕ New Chat", use_container_width=True):
                st.session_state["session_id"] = str(uuid.uuid4())
                st.rerun()
            
            st.markdown("---")
            
            st.markdown("""
            <div class="sidebar-section">
                <h4>🎯 Objectives</h4>
                <p>Lai holh tein bia ruah khawh le fimnak hrawmh.</p>
            </div>
            """, unsafe_allow_html=True)
            
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
            
            st.markdown("""
            <div class="sidebar-contact">
                <h4>📞 Contact</h4>
                <p><a href='https://github.com/Joseph1997-eng' target='_blank'>🔗 GitHub</a></p>
                <p><a href='mailto:josephsaimonn@gmail.com'>📧 Email</a></p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🚪 Logout", use_container_width=True, type="secondary"):
                st.session_state["logged_in"] = False
                st.session_state["username"] = ""
                st.rerun()

        # MAIN CHAT AREA
        st.markdown(f"""
        <div class='chat-header'>
            <img src='{BOT_AVATAR}' class='header-avatar'>
            <div>
                <h2>Joseph's AI Assistant</h2>
                <p>Hello, {st.session_state['username']}! 👋</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Get Messages
        db_messages = get_chat_history(st.session_state["session_id"])
        
        # Welcome Message
        if not db_messages:
            st.markdown("""
            <div class='welcome-box'>
                <h3>👋 Welcome!</h3>
                <p>I'm here to help you in Lai language. Ask me anything!</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Display Messages - WhatsApp Style
        for idx, (role, content) in enumerate(db_messages):
            if role == "assistant":
                # AI on LEFT
                col1, col2, col3 = st.columns([0.7, 0.05, 0.25])
                with col1:
                    st.markdown(f"""
                    <div class="chat-bubble chat-bubble-left">
                        <img src="{BOT_AVATAR}" class="chat-avatar">
                        <div class="chat-content-left">{content}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    import streamlit.components.v1 as components
                    unique_id = f"msg_{st.session_state['session_id'][:8]}_{idx}"
                    components.html(create_copy_button_html(content, unique_id), height=50)
            else:
                # USER on RIGHT
                col1, col2, col3 = st.columns([0.25, 0.05, 0.7])
                with col3:
                    st.markdown(f"""
                    <div class="chat-bubble chat-bubble-right">
                        <div class="chat-content-right">{content}</div>
                        <div class="user-avatar">👤</div>
                    </div>
                    """, unsafe_allow_html=True)

        # File Upload
        uploaded_file = st.file_uploader(
            "📎 Upload file (optional)",
            type=["pdf", "jpg", "png", "jpeg", "txt", "docx", "xlsx", "mp4"]
        )

        # Chat Input
        user_input = st.chat_input("Type your message...")
        
        if user_input:
            save_chat_message(st.session_state["session_id"], st.session_state["username"], "user", user_input)
            st.rerun()

        # Generate Response
        if db_messages and db_messages[-1][0] == 'user':
            current_prompt = db_messages[-1][1]
            
            col1, col2, col3 = st.columns([0.7, 0.05, 0.25])
            with col1:
                with st.spinner("Thinking..."):
                    try:
                        import streamlit.components.v1 as components
                        
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
                        
                        st.markdown(f"""
                        <div class="chat-bubble chat-bubble-left">
                            <img src="{BOT_AVATAR}" class="chat-avatar">
                            <div class="chat-content-left">{final_text}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        unique_id = f"latest_{st.session_state['session_id'][:8]}"
                        components.html(create_copy_button_html(final_text, unique_id), height=50)
                        
                        save_chat_message(st.session_state["session_id"], st.session_state["username"], "assistant", final_text)
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    main()
