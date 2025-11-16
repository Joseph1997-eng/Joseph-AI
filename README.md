# 🤖 Joseph-AI — LAI AI Assistant

Joseph-AI is a personalized AI assistant built with **Streamlit**, **Google Gemini**, and a **local SQLite database**.  
It includes user authentication, chat history saving, file uploads, and a fully customized UI using a dark glass theme.

---

## 🌟 Features

### 🔐 User System
- User **registration & login**
- Passwords stored using **SHA-256 hashing**
- Session-based authentication

### 💬 AI Chat System
- Uses **Google Gemini 2.5 Flash**
- Supports **contextual conversations**
- Custom persona "Leoliver" with Hakha Lai style
- Chat history stored per user & per session

### 📁 File Upload Support
Upload and send:
- PDF  
- Images (JPG/PNG)  
- MP3  
- TXT  
- DOCX  
- XLSX  
- PPTX  
- MP4  

### 🗂 Chat History
- Saves every message in SQLite
- View old sessions from sidebar
- Click timestamps to reload conversations

### 🎨 Modern UI (Dark Glass Theme)
Custom CSS includes:
- Dark gradient background
- Glass-effect chat bubbles
- Animated buttons
- Clean text fields

---

## 🏗 Tech Stack

| Component | Technology |
|----------|------------|
| Frontend | Streamlit |
| Backend | Python |
| AI Model | Google Gemini 2.5 Flash |
| Database | SQLite |
| Auth | SHA-256 Password Hashing |
| File Upload | Streamlit File Uploader |

---

## 🚀 How to Run the Project

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Joseph1997-eng/Joseph-AI.git
cd Joseph-AI
```
## Install Dependencies
```bash
pip install -r requirement.txt
```

## Add Your Gemini API Key
```bash
.streamlit/secrets.toml
```

## ▶ Run the App
```bash
streamlit run app.py
```
The app will open automatically in your browser.

## 🗄 Database Structure
```bash
users.db automatically creates these tables:

userstable(username, password)

chathistory(session_id, username, role, content, timestamp)

feedback(username, message, timestamp)
```
---
##🔒 Security Notes
```bash
API keys must be stored inside Streamlit Secrets

Passwords are hashed using SHA-256

Never upload users.db publicly if real users are using the system
```
## 📌 Project Structure
```bash
📁 Joseph-AI
├── app.py
├── requirement.txt
├── users.db
├── joseph.JPG
├── LICENSE
└── README.md
```
## ❤️ Credits

Developed by Joseph (Leoliver).
Powered by Streamlit & Google Gemini.

If you like this project, please ★ star the repository!


---
