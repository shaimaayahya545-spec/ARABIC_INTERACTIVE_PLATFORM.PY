import base64
from datetime import datetime
import os
import random
import sqlite3
import time
from fpdf import FPDF
import pandas as pd
import streamlit as st

# --- Page Configuration ---
st.set_page_config(
    page_title="منصة اللغة العربية التفاعلية - المعلمة شيماء يحيى",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS for RTL & Pink/Purple Theme ---
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
        background-color: #FAF5FC;
        color: #2D1B36;
    }

    /* Main Container */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    /* Headers & Typography */
    h1, h2, h3, h4 {
        color: #6A1B9A !important;
        font-family: 'Cairo', sans-serif;
        font-weight: 700;
    }

    /* Custom Header Card */
    .header-card {
        background: linear-gradient(135deg, #8E24AA 0%, #D81B60 100%);
        color: white !important;
        padding: 25px;
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 10px 25px rgba(142, 36, 170, 0.2);
        margin-bottom: 25px;
    }
    .header-card h1 {
        color: white !important;
        margin-bottom: 5px;
        font-size: 2.2rem;
    }
    .header-card h3 {
        color: #F8BBD0 !important;
        margin-top: 0;
        font-weight: 600;
    }

    /* Card Box */
    .content-box {
        background: #FFFFFF;
        border-radius: 15px;
        padding: 20px;
        border: 2px solid #F3E5F5;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
        margin-bottom: 20px;
    }

    /* Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #8E24AA, #D81B60);
        color: white !important;
        border: none;
        border-radius: 12px;
        padding: 10px 24px;
        font-size: 1.05rem;
        font-weight: 700;
        transition: all 0.3s ease;
        box-shadow: 0 4px 10px rgba(216, 27, 96, 0.2);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(216, 27, 96, 0.35);
    }

    /* Hide Streamlit Menu / Footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)

# --- SQLite Database Connection & Setup ---
DB_FILE = "arabic_platform.db"

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            xp INTEGER DEFAULT 0,
            level TEXT DEFAULT 'مبتدئ',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            student_id INTEGER,
            lesson_id INTEGER,
            completed INTEGER DEFAULT 0,
            score REAL DEFAULT 0,
            PRIMARY KEY(student_id, lesson_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            lesson_id INTEGER,
            score REAL,
            total_questions INTEGER,
            time_taken_sec INTEGER,
            skills_needed TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('pass_score_pct', '70')")
    conn.commit()
    conn.close()

init_db()

def get_or_create_student(name):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM students WHERE name = ?", (name,))
    student = c.fetchone()
    if not student:
        c.execute("INSERT INTO students (name, xp, level) VALUES (?, 0, 'مبتدئ')", (name,))
        conn.commit()
        c.execute("SELECT * FROM students WHERE name = ?", (name,))
        student = c.fetchone()
    conn.close()
    return dict(student)

def get_leaderboard():
    conn = get_db()
    df = pd.read_sql_query("""
        SELECT s.name AS "اسم الطالب", s.xp AS "النقاط (XP)", s.level AS "المستوى",
               COALESCE(COUNT(p.lesson_id), 0) AS "الدروس المكتملة"
        FROM students s
        LEFT JOIN progress p ON s.id = p.student_id AND p.completed = 1
        GROUP BY s.id
        ORDER BY s.xp DESC
    """, conn)
    conn.close()
    return df

LESSONS_DATA = [
    {
        "id": 1,
        "title": "الدرس الأول: حرف الراء (ر)",
        "unit": "الوحدة الأولى: الحروف (ر، د، ب)",
        "explanation": "نستمع إلى قصة حرف الراء (رامي وراما في الحديقة)، وننطق صوت حرف الراء الممدود بالألف (را)."
    }
]

# --- Session State Initialization ---
if "current_student" not in st.session_state:
    st.session_state.current_student = None

# --- Main App Layout ---
st.markdown("""
<div class="header-card">
    <h1>منصة اللغة العربية التفاعلية للصف الأول الأساسي 🇵🇸</h1>
    <h3>إعداد وتصاميم المعلمة: شيماء يحيى | الجزء الأول 2020</h3>
</div>
""", unsafe_allow_html=True)

if not st.session_state.current_student:
    st.markdown('<div class="content-box">', unsafe_allow_html=True)
    st.subheader("👋 أهلاً بك يا بطل العربية! سجل اسمك للبدء")
    student_name_input = st.text_input("ادخل اسم الطالب / الطالبة الثلاثي:", placeholder="مثال: أحمد رامي محمود")
    if st.button("ابدأ التعلّم 🚀"):
        if student_name_input.strip():
            student = get_or_create_student(student_name_input.strip())
            st.session_state.current_student = student
            st.success(f"مرحباً بك يا {student['name']}! نتمنى لك رحلة ممتعة 🌟")
            st.rerun()
        else:
            st.warning("يرجى إدخال اسم الطالب قبل المتابعة.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

student = get_or_create_student(st.session_state.current_student['name'])
st.session_state.current_student = student

with st.sidebar:
    st.title(f"👤 {student['name']}")
    col_sb1, col_sb2 = st.columns(2)
    col_sb1.metric("النقاط (XP)", f"⭐ {student['xp']}")
    col_sb2.metric("المستوى", student['level'])
    st.markdown("---")
    menu_choice = st.radio("القائمة الرئيسية:", [
        "📖 قائمة الدروس والشرح",
        "🏆 لوحة المتصدرين",
        "👩‍🏫 لوحة إدارة المعلمة"
    ])
    st.markdown("---")
    if st.button("🚪 تسجيل الخروج / تغيير الطالب"):
        st.session_state.current_student = None
        st.rerun()

if menu_choice == "📖 قائمة الدروس والشرح":
    st.subheader("📚 دروس كتاب لغتنا الجميلة - الصف الأول")
    lesson = LESSONS_DATA[0]
    st.markdown(f"### {lesson['title']}")
    st.write(lesson['explanation'])

elif menu_choice == "🏆 لوحة المتصدرين":
    st.subheader("🏆 لوحة المتصدرين العامة للطلاب")
    df_lb = get_leaderboard()
    st.dataframe(df_lb, use_container_width=True)

elif menu_choice == "👩‍🏫 لوحة إدارة المعلمة":
    st.subheader("👩‍🏫 لوحة الإدارة والتحكم - المعلمة شيماء يحيى")
    st.write("أهلاً بكِ معلمة شيماء! يمكنكِ متابعة أداء الطلاب وتحديث شرط الشهادة وتصدير البيانات.")
