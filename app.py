import streamlit as st
import google.generativeai as genai
import sqlite3
import hashlib
import uuid
from datetime import datetime
import os
import streamlit.components.v1 as components

# ---------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------

# Load API Key from environment variable or Streamlit secrets
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    API_KEY = os.getenv("GEMINI_API_KEY", "")

if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.error("⚠️ API Key not found! Please set GEMINI_API_KEY in secrets or environment variables.")

# Bot Avatar URL
BOT_AVATAR = "https://raw.githubusercontent.com/Joseph1997-eng/Joseph-AI/main/joseph.JPG"


# Load System Prompt from Streamlit secrets or file
def load_system_prompt():
    # Try to load from Streamlit secrets first (for Streamlit Cloud)
    try:
        return st.secrets["SYSTEM_PROMPT"]
    except Exception:
        pass

    # Try to load from file (for local development)
    try:
        with open("system_prompt.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        pass

    # Fallback default prompt
    return """You are a helpful AI assistant named Leoliver (Joseph). 
You communicate in Lai language (Hakha dialect) and are wise, friendly, and caring."""


# --- CSS Loader ---
def load_css(file_name):
    try:
        with open(file_name, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("style.css file not found! Running with default styles.")


# ---------------------------------------------------------
# 2. DATABASE FUNCTIONS
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect("users.db", check_same_thread=False)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS userstable(username TEXT PRIMARY KEY, password TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS chathistory(session_id TEXT, username TEXT, role TEXT, content TEXT, timestamp TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS feedback(username TEXT, message TEXT, timestamp TEXT)"
    )
    conn.commit()
    conn.close()


def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()


def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text


def add_userdata(username, password):
    conn = sqlite3.connect("users.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO userstable(username,password) VALUES (?,?)", (username, password)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def login_user(username, password):
    conn = sqlite3.connect("users.db", check_same_thread=False)
    c = conn.cursor()
    c.execute(
        "SELECT * FROM userstable WHERE username =? AND password = ?",
        (username, password),
    )
    data = c.fetchall()
    conn.close()
    return data


def save_chat_message(session_id, username, role, content):
    conn = sqlite3.connect("users.db", check_same_thread=False)
    c = conn.cursor()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        "INSERT INTO chathistory(session_id, username, role, content, timestamp) VALUES (?,?,?,?,?)",
        (session_id, username, role, content, ts),
    )
    conn.commit()
    conn.close()


def get_chat_history(session_id):
    conn = sqlite3.connect("users.db", check_same_thread=False)
    c = conn.cursor()
    c.execute(
        "SELECT role, content FROM chathistory WHERE session_id=? ORDER BY timestamp",
        (session_id,),
    )
    data = c.fetchall()
    conn.close()
    return data


def get_user_sessions(username):
    conn = sqlite3.connect("users.db", check_same_thread=False)
    c = conn.cursor()
    c.execute(
        """
        SELECT session_id, MAX(timestamp) as last_time
        FROM chathistory 
        WHERE username=? 
        GROUP BY session_id 
        ORDER BY last_time DESC
        LIMIT 20
    """,
        (username,),
    )
    data = c.fetchall()
    conn.close()
    return data


def delete_chat_session(session_id):
    conn = sqlite3.connect("users.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM chathistory WHERE session_id=?", (session_id,))
    conn.commit()
    conn.close()


def delete_all_sessions(username):
    conn = sqlite3.connect("users.db", check_same_thread=False)
    c = conn.cursor()
    c.execute("DELETE FROM chathistory WHERE username=?", (username,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------
# 3. MODEL SETTINGS (Gemini 2.5 Flash)
# ---------------------------------------------------------
system_prompt = load_system_prompt()

# Use latest model: gemini-2.5-flash
if API_KEY:
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=system_prompt,
        generation_config=genai.GenerationConfig(
            temperature=0.8,
            max_output_tokens=4000,
        ),
    )
else:
    model = None  # Avoid crashes if no key


# ---------------------------------------------------------
# 4. COPY TO CLIPBOARD FUNCTION
# ---------------------------------------------------------
def create_copy_button_html(text, unique_id):
    """Creates a working copy button with proper JavaScript"""
    import json

    text_json = json.dumps(text)

    copy_button_html = f"""
    <div style="margin-bottom: 10px; text-align: right;">
        <button id="copy_btn_{unique_id}" 
                onclick="copyText_{unique_id}()" 
                class="copy-button"
                style="
                    background: linear-gradient(90deg, #6a5acd, #8a2be2);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 16px;
                    cursor: pointer;
                    font-size: 13px;
                    font-weight: 500;
                    transition: all 0.3s;
                    box-shadow: 0 2px 8px rgba(138, 43, 226, 0.3);
                "
                onmouseover="this.style.transform='scale(1.05)'; this.style.boxShadow='0 4px 12px rgba(138, 43, 226, 0.5)';"
                onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 2px 8px rgba(138, 43, 226, 0.3)';">
            📋 Copy Text
        </button>
    </div>
    
    <script>
    function copyText_{unique_id}() {{
        const textToCopy = {text_json};
        
        if (navigator.clipboard && navigator.clipboard.writeText) {{
            navigator.clipboard.writeText(textToCopy).then(function() {{
                const btn = document.getElementById('copy_btn_{unique_id}');
                const originalHTML = btn.innerHTML;
                btn.innerHTML = '✅ Copied!';
                btn.style.background = 'linear-gradient(90deg, #2ecc71, #27ae60)';
                
                setTimeout(function() {{
                    btn.innerHTML = originalHTML;
                    btn.style.background = 'linear-gradient(90deg, #6a5acd, #8a2be2)';
                }}, 2000);
            }}).catch(function(err) {{
                fallbackCopy_{unique_id}(textToCopy);
            }});
        }} else {{
            fallbackCopy_{unique_id}(textToCopy);
        }}
    }}
    
    function fallbackCopy_{unique_id}(text) {{
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();
        
        try {{
            document.execCommand('copy');
            const btn = document.getElementById('copy_btn_{unique_id}');
            btn.innerHTML = '✅ Copied!';
            btn.style.background = 'linear-gradient(90deg, #2ecc71, #27ae60)';
            setTimeout(function() {{
                btn.innerHTML = '📋 Copy Text';
                btn.style.background = 'linear-gradient(90deg, #6a5acd, #8a2be2)';
            }}, 2000);
        }} catch (err) {{
            console.error('Copy failed:', err);
        }}
        
        document.body.removeChild(textArea);
    }}
    </script>
    """
    return copy_button_html


# ---------------------------------------------------------
# 5. APP INTERFACE
# ---------------------------------------------------------
def main():
    st.set_page_config(
        page_title="Joseph's Assistant - LAI AI",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="collapsed",  # Start with sidebar collapsed
    )

    load_css("style.css")
    init_db()

    # Session State Initialization
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "username" not in st.session_state:
        st.session_state["username"] = ""
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())
    if "show_welcome" not in st.session_state:
        st.session_state["show_welcome"] = True

    # ---------------------------------------------------------
    # LOGIN PAGE
    # ---------------------------------------------------------
    if not st.session_state["logged_in"]:
        # Animated background
        st.markdown(
            """
        <div class="login-background">
            <div class="floating-shapes">
                <div class="shape shape-1"></div>
                <div class="shape shape-2"></div>
                <div class="shape shape-3"></div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            # Animated Logo
            st.markdown(
                f"""
            <div style='display: flex; justify-content: center; margin-top: 30px; margin-bottom: 20px;'>
                <div class='login-logo animate-fade-in'>
                    <img src='{BOT_AVATAR}' alt='Logo'>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            # Title and Subtitle
            st.markdown(
                "<h1 style='text-align: center; color: #a8c0ff; font-size: 2.5rem; margin-bottom: 10px; font-weight: 700;'>Joseph's Assistant</h1>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<p style='text-align: center; color: #888; font-size: 1.1rem; margin-bottom: 30px;'>LAI HOLH AI - Your Intelligent Companion</p>",
                unsafe_allow_html=True,
            )

            # Info Box
            st.markdown(
                """
            <div class="info-box animate-fade-in">
                <h3>🎯 Kan Hmuitinh</h3>
                <p>Lai holh tein bia ruah khawh le fimnak hrawmh.</p>
                <p><strong>Account Info:</strong> Account ser law na lut kho colh, asiloah na ngeih cia mi hmang in lut.</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

            tab1, tab2 = st.tabs(["🔐 Sign In", "📝 Register"])

            # ---- Sign In ----
            with tab1:
                with st.form("login_form"):
                    u = st.text_input("👤 User Name", placeholder="Enter your username")
                    p = st.text_input(
                        "🔒 Password",
                        type="password",
                        placeholder="Enter your password",
                    )
                    submitted = st.form_submit_button(
                        "🚀 Lut (Login)", use_container_width=True
                    )

                    if submitted:
                        if u and p:
                            hp = make_hashes(p)
                            if login_user(u, hp):
                                st.session_state["logged_in"] = True
                                st.session_state["username"] = u
                                st.success("✅ Login successful!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("❌ Invalid username or password!")
                        else:
                            st.warning("⚠️ Please fill in all fields!")

            # ---- Register ----
            with tab2:
                with st.form("register_form"):
                    nu = st.text_input(
                        "👤 Min Thar", placeholder="Choose a username"
                    )
                    np = st.text_input(
                        "🔒 Password Thar",
                        type="password",
                        placeholder="Create a password",
                    )
                    np2 = st.text_input(
                        "🔒 Confirm Password",
                        type="password",
                        placeholder="Confirm your password",
                    )
                    submitted = st.form_submit_button(
                        "✨ Account Ser (Register)", use_container_width=True
                    )

                    if submitted:
                        if nu and np and np2:
                            if np != np2:
                                st.error("❌ Passwords don't match!")
                            elif len(np) < 6:
                                st.error("❌ Password must be at least 6 characters!")
                            else:
                                if add_userdata(nu, make_hashes(np)):
                                    st.success(
                                        "✅ Account created successfully! Please sign in."
                                    )
                                    st.balloons()
                                else:
                                    st.error("❌ Username already exists!")
                        else:
                            st.warning("⚠️ Please fill in all fields!")

            # Footer
            st.markdown(
                """
            <div class='login-footer animate-fade-in'>
                <p>Need help? Contact us:</p>
                <p>
                    <a href='https://github.com/Joseph1997-eng' target='_blank'>
                        <i class="fab fa-github"></i> GitHub
                    </a> | 
                    <a href='mailto:josephsaimonn@gmail.com'>
                        <i class="fas fa-envelope"></i> Email
                    </a>
                </p>
                <p class="copyright">© 2024 Joseph's Assistant. All rights reserved.</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

    # ---------------------------------------------------------
    # CHAT PAGE
    # ---------------------------------------------------------
    else:
        # ---------------- Sidebar ----------------
        with st.sidebar:
            # User Profile
            st.markdown(
                f"""
            <div class="user-profile">
                <div class="profile-avatar">👤</div>
                <div class="profile-name">{st.session_state['username']}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            # New Chat Button
            if st.button("➕ New Chat", use_container_width=True, key="new_chat_btn"):
                st.session_state["session_id"] = str(uuid.uuid4())
                st.session_state["show_welcome"] = True
                st.rerun()

            st.markdown("---")

            # Objective Box
            st.markdown(
                """
            <div class="sidebar-section">
                <h4>🎯 KAN HMUITINH</h4>
                <p>Lai holh tein bia ruah khawh le fimnak hrawmh.</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

            st.markdown("---")

            # Chat History
            st.markdown("### 🕒 History")

            sessions = get_user_sessions(st.session_state["username"])
            if sessions:
                # Delete All Button
                if st.button(
                    "🗑️ Clear All History", use_container_width=True, type="secondary"
                ):
                    delete_all_sessions(st.session_state["username"])
                    st.session_state["session_id"] = str(uuid.uuid4())
                    st.success("✅ All chat history cleared!")
                    st.rerun()

                st.markdown("<div class='chat-history'>", unsafe_allow_html=True)
                for sess_id, ts in sessions:
                    is_current = sess_id == st.session_state["session_id"]
                    col1, col2 = st.columns([4, 1])

                    with col1:
                        button_type = "primary" if is_current else "secondary"
                        label = f"{'📍' if is_current else '📅'} {ts[:16]}"
                        if st.button(
                            label,
                            key=f"load_{sess_id}",
                            use_container_width=True,
                            type=button_type,
                        ):
                            st.session_state["session_id"] = sess_id
                            st.session_state["show_welcome"] = False
                            st.rerun()

                    with col2:
                        if st.button(
                            "🗑️", key=f"del_{sess_id}", use_container_width=True
                        ):
                            delete_chat_session(sess_id)
                            if st.session_state["session_id"] == sess_id:
                                st.session_state["session_id"] = str(uuid.uuid4())
                            st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("💬 No chat history yet. Start a conversation!")

            # Admin Dashboard
            if st.session_state["username"] == "Joe":
                st.markdown("---")
                st.markdown("### 📊 Admin Panel")

                conn = sqlite3.connect("users.db", check_same_thread=False)
                c = conn.cursor()
                c.execute("SELECT count(username) FROM userstable")
                total_users = c.fetchone()[0]

                st.metric("Total Users", total_users)

                with st.expander("👥 View All Users"):
                    c.execute("SELECT username FROM userstable")
                    all_users = c.fetchall()
                    for u in all_users:
                        st.write(f"• {u[0]}")
                conn.close()

            st.markdown("---")

            # Contact Section
            st.markdown(
                """
            <div class="sidebar-contact">
                <h4>📞 PEHTLAIHNAK</h4>
                <p><a href='https://github.com/Joseph1997-eng' target='_blank'>🔗 GitHub</a></p>
                <p><a href='mailto:josephsaimonn@gmail.com'>📧 Email</a></p>
            </div>
            """,
                unsafe_allow_html=True,
            )

            # Logout Button
            if st.button("🚪 Logout", use_container_width=True, type="secondary"):
                st.session_state["logged_in"] = False
                st.session_state["username"] = ""
                st.rerun()

        # ---------------- Main Chat Area ----------------

        # Scroll to bottom button
        st.markdown(
            """
        <style>
        /* Scroll to Bottom Button */
        .scroll-bottom-btn {
            position: fixed;
            bottom: 120px;
            right: 30px;
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #6a5acd, #8a2be2);
            border-radius: 50%;
            display: none;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 4px 16px rgba(138, 43, 226, 0.5);
            z-index: 999;
            transition: all 0.3s;
            animation: pulse 2s ease-in-out infinite;
        }
        
        .scroll-bottom-btn:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 24px rgba(138, 43, 226, 0.7);
        }
        
        .scroll-bottom-btn::before {
            content: "⬇";
            font-size: 24px;
            color: white;
        }
        
        @media (max-width: 768px) {
            .scroll-bottom-btn {
                right: 15px;
                bottom: 100px;
                width: 45px;
                height: 45px;
            }
        }
        </style>
        
        <script>
        function scrollToBottom() {
            window.scrollTo({
                top: document.body.scrollHeight,
                behavior: 'smooth'
            });
        }
        
        window.addEventListener('scroll', function() {
            const scrollBtn = document.querySelector('.scroll-bottom-btn');
            if (scrollBtn) {
                if (window.scrollY > 300) {
                    scrollBtn.style.display = 'flex';
                } else {
                    scrollBtn.style.display = 'none';
                }
            }
        });
        </script>
        
        <div class="scroll-bottom-btn" onclick="scrollToBottom()" title="Scroll to bottom"></div>
        """,
            unsafe_allow_html=True,
        )

        # Header
        st.markdown(
            f"""
        <div class="title-container animate-slide-down">
            <div class="title-logo">
                <img src='{BOT_AVATAR}' alt='Logo'>
            </div>
            <div class="title-text">
                <h1>Joseph's Assistant</h1>
                <h3>🤝 Na dam maw, {st.session_state['username']}?</h3>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Chat history from DB
        db_messages = get_chat_history(st.session_state["session_id"]) or []

        # Welcome Message
        if not db_messages and st.session_state.get("show_welcome", True):
            st.markdown(
                """
            <div class="welcome-message animate-fade-in">
                <h2>👋 Welcome to Joseph's Assistant!</h2>
                <p>I'm here to help you in Lai language. Feel free to ask me anything!</p>
                <div class="feature-grid">
                    <div class="feature-card">
                        <div class="feature-icon">💬</div>
                        <h4>Natural Conversation</h4>
                        <p>Chat naturally in Lai language</p>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon">📚</div>
                        <h4>Knowledge Base</h4>
                        <p>Ask about any topic</p>
                    </div>
                    <div class="feature-card">
                        <div class="feature-icon">🎯</div>
                        <h4>Helpful & Wise</h4>
                        <p>Get thoughtful responses</p>
                    </div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # Display Chat Messages - WhatsApp Style
        for idx, (role, content) in enumerate(db_messages):
            if role == "assistant":
                # AI messages on LEFT side
                col1, col2, col3 = st.columns([0.7, 0.05, 0.25])
                with col1:
                    st.markdown(
                        f"""
                    <div class="chat-bubble chat-bubble-assistant">
                        <div class="chat-avatar">
                            <img src="{BOT_AVATAR}" alt="AI">
                        </div>
                        <div class="chat-content">
                            <div class="chat-message-text">{content}</div>
                        </div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                    unique_id = f"msg_{st.session_state['session_id'][:8]}_{idx}"
                    components.html(
                        create_copy_button_html(content, unique_id), height=60
                    )
            else:
                # User messages on RIGHT side
                col1, col2, col3 = st.columns([0.25, 0.05, 0.7])
                with col3:
                    st.markdown(
                        f"""
                    <div class="chat-bubble chat-bubble-user">
                        <div class="chat-content">
                            <div class="chat-message-text">{content}</div>
                        </div>
                        <div class="chat-avatar">
                            <div class="user-avatar">👤</div>
                        </div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

        # -------- File Upload Floating Button --------
        upload_container = st.container()
        with upload_container:
            if "show_upload" not in st.session_state:
                st.session_state.show_upload = False

            col1, col2 = st.columns([0.85, 0.15])

            with col2:
                if st.button("📎", key="upload_toggle", help="Upload file"):
                    st.session_state.show_upload = not st.session_state.show_upload
                    st.experimental_rerun if hasattr(st, "experimental_rerun") else None

            uploaded_file = None
            if st.session_state.show_upload:
                with st.expander("📁 Upload File", expanded=True):
                    uploaded_file = st.file_uploader(
                        "Choose a file",
                        type=[
                            "pdf",
                            "jpg",
                            "png",
                            "jpeg",
                            "mp3",
                            "txt",
                            "docx",
                            "xlsx",
                            "pptx",
                            "mp4",
                        ],
                        help="Upload any supported file",
                        key="file_uploader",
                    )
                    if uploaded_file:
                        st.success(
                            f"✅ {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)"
                        )

        # Fix floating style only for this button (not all buttons)
        st.markdown(
            """
        <style>
        button[kind="secondary"]#upload_toggle {
            position: fixed !important;
            bottom: 60px !important;
            right: 30px !important;
            width: 56px !important;
            height: 56px !important;
            border-radius: 50% !important;
            background: linear-gradient(135deg, #8a2be2, #6a5acd) !important;
            border: none !important;
            font-size: 24px !important;
            box-shadow: 0 6px 20px rgba(138, 43, 226, 0.6) !important;
            z-index: 1000 !important;
            transition: all 0.3s !important;
        }
        
        button[kind="secondary"]#upload_toggle:hover {
            transform: rotate(90deg) scale(1.15) !important;
            box-shadow: 0 8px 28px rgba(138, 43, 226, 0.8) !important;
        }
        </style>
        """,
            unsafe_allow_html=True,
        )

        # -------- Chat Input --------
        user_input = st.chat_input("💭 Type your message here...")

        if user_input:
            st.session_state["show_welcome"] = False
            save_chat_message(
                st.session_state["session_id"],
                st.session_state["username"],
                "user",
                user_input,
            )
            st.rerun()

        # -------------------------------------------------
        # GEMINI RESPONSE GENERATION (2.5 Flash)
        # -------------------------------------------------
        last_db_role = db_messages[-1][0] if db_messages else None

        if last_db_role == "user" and model is not None:
            current_prompt = db_messages[-1][1]

            with st.chat_message("assistant", avatar=BOT_AVATAR):
                # Loading animation
                loading_placeholder = st.empty()
                loading_placeholder.markdown(
                    """
                <div class="loading-text" style="color: #a8c0ff; font-size: 16px; font-weight: 500; padding: 10px;">
                    <span>Ka</span> <span>ruat</span> <span>ta</span> <span>lio...</span>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                try:
                    # Build Gemini history from DB
                    gemini_hist = []
                    for r, c in db_messages[:-1]:
                        role_name = "model" if r == "assistant" else "user"
                        gemini_hist.append({"role": role_name, "parts": [c]})

                    user_context = f"[User Min: {st.session_state['username']}]. "
                    full_prompt_to_send = user_context + current_prompt

                    # Build contents for Gemini 2.5
                    contents = gemini_hist + [
                        {"role": "user", "parts": [full_prompt_to_send]}
                    ]

                    if uploaded_file:
                        # If file attached, send as first part of user message
                        file_part = {
                            "inline_data": {
                                "mime_type": uploaded_file.type,
                                "data": uploaded_file.getvalue(),
                            }
                        }
                        contents = gemini_hist + [
                            {
                                "role": "user",
                                "parts": [file_part, full_prompt_to_send],
                            }
                        ]

                    response = model.generate_content(contents=contents)

                    # Clear loading
                    loading_placeholder.empty()

                    raw_text = response.text
                    final_text = raw_text.replace("*", "")

                    unique_id = f"latest_{st.session_state['session_id'][:8]}"
                    components.html(
                        create_copy_button_html(final_text, unique_id), height=60
                    )
                    st.markdown(
                        f'<div class="chat-message-content animate-fade-in">{final_text}</div>',
                        unsafe_allow_html=True,
                    )

                    # Save assistant reply
                    save_chat_message(
                        st.session_state["session_id"],
                        st.session_state["username"],
                        "assistant",
                        final_text,
                    )

                except Exception as e:
                    loading_placeholder.empty()
                    st.error(f"❌ Error: {str(e)}")
                    st.info("💡 Please check your API key or try again later.")


if __name__ == "__main__":
    main()
