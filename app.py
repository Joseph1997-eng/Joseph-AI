import streamlit as st
import google.generativeai as genai
import sqlite3
import hashlib
import uuid
from datetime import datetime

# ---------------------------------------------------------
# 1. CONFIGURATION & CSS (DARK GLASS THEME)
# ---------------------------------------------------------

# ⚠️ NA API KEY HIKA AH CHIAH
#genai.configure(api_key="AIzaSyBf1O2hE9y9dBtJwCnch2s0vW3ggmHebG4")
# ⚠️ A HLAN: genai.configure(api_key="AIzaSy...") <-- HIHI GITHUB AH CHIAH HLAH

# ✅ A TU: Secrets in laak ding
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("API Key a tlau! Streamlit Secrets ah chiah a hau.")
BOT_AVATAR = "joseph.JPG" 

# --- CSS: COLORS & GLASS UI ---
page_bg_img = """
<style>
/* 1. Main Background - Dark Purple Gradient */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #1e1e2f, #2a2a40, #1e1e2f);
    color: #e0e0e0; /* Ca color a rang niam te */
}

/* 2. Sidebar */
[data-testid="stSidebar"] {
    background-color: rgba(30, 30, 47, 0.95);
    border-right: 1px solid rgba(255, 255, 255, 0.1);
}

/* 3. Chat Message Colors */

/* USER (Nangmah) - Blue Glass */
[data-testid="stChatMessage"][data-testid="user"] {
    background: rgba(50, 100, 255, 0.15); /* Blue niam te */
    border: 1px solid rgba(100, 150, 255, 0.3);
    border-radius: 15px;
    color: #ffffff;
}

/* ASSISTANT (AI) - Purple Glass */
[data-testid="stChatMessage"][data-testid="assistant"] {
    background: rgba(100, 50, 255, 0.1); /* Purple niam te */
    border: 1px solid rgba(180, 130, 255, 0.3);
    border-radius: 15px;
    color: #ffffff;
}

/* 4. Buttons */
div.stButton > button {
    background: linear-gradient(90deg, #6a5acd, #8a2be2);
    color: white;
    border: none;
    border-radius: 8px;
    transition: transform 0.1s;
}
div.stButton > button:hover {
    transform: scale(1.05);
    background: linear-gradient(90deg, #8a2be2, #6a5acd);
}

/* 5. Text Input Fields */
.stTextInput > div > div > input {
    background-color: rgba(255, 255, 255, 0.05);
    color: white;
    border: 1px solid #555;
}
</style>
"""

# ---------------------------------------------------------
# 2. DATABASE FUNCTIONS
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS userstable(username TEXT, password TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS chathistory(session_id TEXT, username TEXT, role TEXT, content TEXT, timestamp TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS feedback(username TEXT, message TEXT, timestamp TEXT)')
    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password,hashed_text):
    if make_hashes(password) == hashed_text: return True
    return False

def add_userdata(username,password):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('INSERT INTO userstable(username,password) VALUES (?,?)',(username,password))
    conn.commit()
    conn.close()

def login_user(username,password):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('SELECT * FROM userstable WHERE username =? AND password = ?',(username,password))
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
    c.execute('SELECT role, content FROM chathistory WHERE session_id=?', (session_id,))
    data = c.fetchall()
    conn.close()
    return data

def get_user_sessions(username):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        SELECT session_id, MAX(timestamp) 
        FROM chathistory 
        WHERE username=? 
        GROUP BY session_id 
        ORDER BY MAX(timestamp) DESC
    ''', (username,))
    data = c.fetchall()
    conn.close()
    return data

def save_feedback(username, message):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('INSERT INTO feedback(username, message, timestamp) VALUES (?,?,?)', (username, message, ts))
    conn.commit()
    conn.close()

# ---------------------------------------------------------
# 3. MODEL SETTINGS (REFINED PROMPT)
# ---------------------------------------------------------
system_prompt = """
**Role & Persona:**
Na min cu 'Leoliver' (Joseph). Nangmah cu Lai holh a thiam mi, a lung a thiang mi, le mifim na si.

**Zulhphung (Style & Tone Guide):**

1. **Holh (Language):** - Biaruahnak kip ah **Lai holh (Hakha)** lawngte hmang. 
   - English in an in hal zong ah Lai holh in leh ding.

2. **Tone (Aw-suaisam) - "Mifim, Hawikom, Dawtmi":**
   - **Mifim (Wise):** Thil na fianter tikah biafang hmaan le fiang tein chim. "Maivan" (Internet), "Zatlangbu" (Community), "Pehtlaihnak" (Connection).
   - **Hawikom (Friendly):** "Na dam maw," "Ka hawi," "Bawmh na herh maw" ti bantuk in ṭhian a fawi tein chawn.
   - **Dawtmi (Caring/Ram King Style):** Hnemhnak le lungthin kong ah "Ram King" le "Muko" biafang hmang. **"Siaherh", "Lung hna a hno", "Lemsoi", "Hmaithlak"**.

3. **Tahchunhnak (Examples - DATA TRAINING):**
   - *User:* "Ka lung a chia."
   - *Joseph:* "A poi ka ti tuk, ka hawi. Na lungretheihnak cu kan in hrawmpi ve. Na lung hna a hno nak ding a si ahcun, kan in biahalnak in hnemh ka duh. Kan in siaherh tuk."
   - *User:* "Internet kong ka chim tuah."
   - *Joseph:* "Maivan (Internet) timi cu vawleicung hmun khat le hmun khat pehtlaihnak a si. Inn in maivan hmannak dingah computer le maivan pehtlaitu (ISP) na herh lai."
   - *User:* "Na ka thei maw?"
   - *Joseph:* "Ka in hngalh ko. Na min cu {Username} a si. Nangmah he biaruah hi ka caah lunglawmhnak a si."

4. **Spelling & Grammar:** - Tone marker (á, ṭ, etc.) hman i zuam. 
   - '*' (asterisk) asiloah '#' hmang hlah. Ca pang tein ṭial.
   - **Correction:** "Ka rel zo cang" ti hman lo ding, "**Ka rel dih cang**" ti tu hman ding.

5. **Behavior:** - Nangmah cu robot na si lo, Leoliver na si. Na bia a thiang, na lung a sau, i na biaruah mi cungah zangfahnak le dawtnak na ngei.
"""

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=system_prompt,
    generation_config=genai.GenerationConfig(temperature=0.8, max_output_tokens=4000)
)

# ---------------------------------------------------------
# 4. APP INTERFACE
# ---------------------------------------------------------
def main():
    st.set_page_config(page_title="Joseph Assistant - LAI AI", page_icon="🤖", layout="wide")
    st.markdown(page_bg_img, unsafe_allow_html=True)
    init_db()

    if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
    if "username" not in st.session_state: st.session_state["username"] = ""
    if "session_id" not in st.session_state: st.session_state["session_id"] = str(uuid.uuid4())

    # --- LOGIN ---
    if not st.session_state["logged_in"]:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.markdown("<h1 style='text-align: center; color: #a8c0ff;'>Joseph Assistant - LAI AI</h1>", unsafe_allow_html=True)
            tab1, tab2 = st.tabs(["Sign In", "Register"])
            
            with tab1:
                u = st.text_input("User Name")
                p = st.text_input("Password", type='password')
                if st.button("Lut (Login)"):
                    hp = make_hashes(p)
                    if login_user(u, hp):
                        st.session_state["logged_in"] = True
                        st.session_state["username"] = u
                        st.rerun()
                    else: st.error("A hmaan lo.")
            
            with tab2:
                nu = st.text_input("Min Thar")
                np = st.text_input("Password Thar", type='password')
                if st.button("Create Account"):
                    if nu and np:
                        add_userdata(nu, make_hashes(np))
                        st.success("Na ser cang!")

# --- CHAT PAGE ---
    else:
        with st.sidebar:
            st.write(f"👤 **{st.session_state['username']}**")
            
            if st.button("➕ New Chat"):
                st.session_state["session_id"] = str(uuid.uuid4())
                st.rerun()
            
            st.markdown("---")
            sessions = get_user_sessions(st.session_state["username"])
            for sess_id, ts in sessions:
                if st.button(f"📅 {ts[:16]}", key=sess_id):
                    st.session_state["session_id"] = sess_id
                    st.rerun()
            
            # --- ADMIN DASHBOARD START ---
            if st.session_state["username"] == "Rose": # <-- NA MIN THLENG HIKA AH
                st.markdown("---")
                st.caption("📊 ADMIN ONLY")
                
                # Database Connection Check
                conn = sqlite3.connect('users.db', check_same_thread=False)
                c = conn.cursor()
                
                # User Count
                c.execute('SELECT count(username) FROM userstable')
                total_users = c.fetchone()[0]
                st.write(f"Total Users: **{total_users}**")
                
                # List
                with st.expander("View Users"):
                    c.execute('SELECT username FROM userstable')
                    all_users = c.fetchall()
                    for u in all_users:
                        st.write(f"• {u[0]}")
                conn.close()
            # --- ADMIN DASHBOARD END ---

            st.markdown("---")
            if st.button("🚪 Logout"):
                st.session_state["logged_in"] = False
                st.rerun()

        # --- MAIN CHAT HEADER ---
        st.title("Joseph Assistant - LAI AI")
        st.markdown(f"### 👋 Na dam maw, {st.session_state['username']}?")
        
        db_messages = get_chat_history(st.session_state["session_id"])
        for role, content in db_messages:
            av = BOT_AVATAR if role == "assistant" else "👤"
            with st.chat_message(role, avatar=av):
                st.markdown(content)
                if role == "assistant":
                     with st.expander("📋 Copy"):
                        st.code(content, language=None)

        with st.expander("📎 File Upload", expanded=False):
            uploaded_file = st.file_uploader("Thim...", type=["pdf", "jpg", "png", "mp3", "txt", "docx", "xlsx", "pptx","mp4"])

        user_input = st.chat_input("Biahalnak...")
        
        if user_input:
            save_chat_message(st.session_state["session_id"], st.session_state["username"], "user", user_input)
            st.rerun()

        last_db_role = db_messages[-1][0] if db_messages else None
        
        if (last_db_role == 'user'):
            current_prompt = db_messages[-1][1]
            
            with st.chat_message("assistant", avatar=BOT_AVATAR):
                with st.spinner("Ka ruat ta lio ..."):
                    try:
                        # --- REMH MI (CRITICAL FIX) ---
                        # Database 'assistant' kha Gemini 'model' ah kan thlen
                        gemini_hist = []
                        for r, c in db_messages[:-1]:
                            role_name = "model" if r == "assistant" else "user"
                            gemini_hist.append({"role": role_name, "parts": [c]})
                        
                        # Context Injection
                        user_context = f"[User Min: {st.session_state['username']}]. "
                        full_prompt_to_send = user_context + current_prompt

                        inputs = [full_prompt_to_send]
                        if uploaded_file:
                             inputs = [{"mime_type": uploaded_file.type, "data": uploaded_file.getvalue()}, full_prompt_to_send]

                        if uploaded_file:
                            response = model.generate_content(inputs)
                        else:
                            chat = model.start_chat(history=gemini_hist)
                            response = chat.send_message(full_prompt_to_send)
                        
                        # Symbol Hloh
                        raw_text = response.text
                        final_text = raw_text.replace("*", "") 
                        
                        st.markdown(final_text)
                        
                        with st.expander("📋 Copy"):
                            st.code(final_text, language=None)
                        
                        save_chat_message(st.session_state["session_id"], st.session_state["username"], "assistant", final_text)
                        
                    except Exception as e:
                        st.error(f"Error: {e}")

if __name__ == '__main__':
    main()
