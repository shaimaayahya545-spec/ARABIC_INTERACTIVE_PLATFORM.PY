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

    .badge-box {
        background: #F8E1F4;
        border-right: 5px solid #8E24AA;
        padding: 12px 20px;
        border-radius: 10px;
        margin-bottom: 15px;
        font-weight: 600;
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

    /* Metric Cards */
    .metric-card {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        border: 2px solid #E1BEE7;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #8E24AA;
    }
    .metric-label {
        color: #666;
        font-size: 0.9rem;
    }

    /* Leaderboard Podium */
    .gold-medal { background-color: #FFF8E1; border: 2px solid #FFD54F; }
    .silver-medal { background-color: #F5F5F5; border: 2px solid #BDBDBD; }
    .bronze-medal { background-color: #FBE9E7; border: 2px solid #FFAB91; }

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
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            cert_id TEXT UNIQUE,
            score REAL,
            level TEXT,
            issue_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
  c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
  c.execute(
      "INSERT OR IGNORE INTO settings (key, value) VALUES ('pass_score_pct',"
      " '70')"
  )
  conn.commit()
  conn.close()


init_db()


# --- Helper DB Functions ---
def get_or_create_student(name):
  conn = get_db()
  c = conn.cursor()
  c.execute("SELECT * FROM students WHERE name = ?", (name,))
  student = c.fetchone()
  if not student:
    c.execute(
        "INSERT INTO students (name, xp, level) VALUES (?, 0, 'مبتدئ')",
        (name,),
    )
    conn.commit()
    c.execute("SELECT * FROM students WHERE name = ?", (name,))
    student = c.fetchone()
  conn.close()
  return dict(student)


def update_xp(student_id, added_xp):
  conn = get_db()
  c = conn.cursor()
  c.execute("SELECT xp FROM students WHERE id = ?", (student_id,))
  res = c.fetchone()
  if res:
    new_xp = res["xp"] + added_xp
    if new_xp >= 1000:
      level = "بطل اللغة 🏆"
    elif new_xp >= 600:
      level = "محترف اللغة 🌟"
    elif new_xp >= 300:
      level = "متقدم 🚀"
    elif new_xp >= 100:
      level = "متعلم 📖"
    else:
      level = "مبتدئ 🌱"
    c.execute(
        "UPDATE students SET xp = ?, level = ? WHERE id = ?",
        (new_xp, level, student_id),
    )
    conn.commit()
  conn.close()


def save_test_result(student_id, lesson_id, score, total_q, time_sec, skills):
  conn = get_db()
  c = conn.cursor()
  c.execute(
      """
        INSERT INTO test_results (student_id, lesson_id, score, total_questions, time_taken_sec, skills_needed)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
      (student_id, lesson_id, score, total_q, time_sec, skills),
  )
  c.execute(
      """
        INSERT OR REPLACE INTO progress (student_id, lesson_id, completed, score)
        VALUES (?, ?, 1, ?)
    """,
      (student_id, lesson_id, score),
  )
  conn.commit()
  conn.close()


def get_leaderboard():
  conn = get_db()
  df = pd.read_sql_query(
      """
        SELECT s.name AS "اسم الطالب", s.xp AS "النقاط (XP)", s.level AS "المستوى",
               COALESCE(COUNT(p.lesson_id), 0) AS "الدروس المكتملة",
               COALESCE(ROUND(AVG(t.score), 1), 0) AS "متوسط الدرجات %"
        FROM students s
        LEFT JOIN progress p ON s.id = p.student_id AND p.completed = 1
        LEFT JOIN test_results t ON s.id = t.student_id
        GROUP BY s.id
        ORDER BY s.xp DESC, "متوسط الدرجات %" DESC
    """,
      conn,
  )
  conn.close()
  return df


def get_setting(key, default):
  conn = get_db()
  c = conn.cursor()
  c.execute("SELECT value FROM settings WHERE key = ?", (key,))
  row = c.fetchone()
  conn.close()
  return row["value"] if row else default


def set_setting(key, value):
  conn = get_db()
  c = conn.cursor()
  c.execute(
      "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
      (key, str(value)),
  )
  conn.commit()
  conn.close()


# --- Curriculum Dataset from Palestinian First Grade Textbook ---
LESSONS_DATA = [{
    "id": 1,
    "title": "الدرس الأول: حرف الراء (ر)",
    "unit": "الوحدة الأولى: الحروف (ر، د، ب)",
    "letter": "ر",
    "objectives": [
        "التعرف على حرف الراء اسمًا وشكلاً وصوتًا.",
        "قراءة مقاطع تشتمل على الراء (را).",
        "كتابة حرف الراء بخط جميل.",
    ],
    "explanation": (
        "نستمع إلى قصة حرف الراء (رامي وراما في الحديقة)، وننطق صوت حرف"
        " الراء الممدود بالألف (را). حرف الراء لا يتصل بما بعده."
    ),
    "rules": (
        "حرف الراء من الحروف النارية (المنفصلة): يتصل بما قبله ولا يتصل بما"
        " بعده. مقطع المد الطويل: ر + ا = را."
    ),
    "examples": ["رامي", "راعي", "راما", "راس"],
    "common_mistakes": (
        "الخلط بين حرف الراء (ر) وحرف الزاي (ز) بسبب النقطة."
    ),
    "quick_questions": [
        {"q": "ما الصوت الأول في كلمة (رامي)؟", "a": "المقطع (را)"},
        {
            "q": "هل يتصل حرف الراء بالحرف الذي بعده؟",
            "a": "لا، حرف الراء حرف منفصل.",
        },
    ],
    "practice": [
        {
            "q": "اختر الكلمة التي تبدأ بمقطع (را):",
            "options": ["دار", "رامي", "دود", "باب"],
            "ans": "رامي",
            "exp": "كلمة رامي تبدأ بالمقطع (را).",
        },
        {
            "q": "حرف الراء في كلمة (راعي) يقع في:",
            "options": ["أول الكلمة", "وسط الكلمة", "آخر الكلمة"],
            "ans": "أول الكلمة",
            "exp": "جاء الحرف في بداية الكلمة.",
        },
        {
            "q": "أي من الكلمات التالية تحتوي على حرف الراء؟",
            "options": ["باب", "راس", "دانا", "توت"],
            "ans": "راس",
            "exp": "كلمة راس تحتوي حرف الراء.",
        },
        {
            "q": "تكوين المقطع (ر + ا) يعطينا:",
            "options": ["دا", "را", "با", "رو"],
            "ans": "را",
            "exp": "الراء مع ألف المد تشكل مقطع (را).",
        },
        {
            "q": "صح أو خطأ: حرف الراء يتصل بالحرُف التي تليها دائماً.",
            "options": ["صح", "خطأ"],
            "ans": "خطأ",
            "exp": "الراء حرف منفصل لا يتصل بما بعده.",
        },
    ],
    "test": [
        {
            "q": "ما الكلمة التي تشتمل على حرف الراء من التالي؟",
            "options": ["راما", "دانا", "باب", "توت"],
            "ans": "راما",
            "type": "mcq",
            "exp": "كلمة راما تحتوي حرف الراء.",
        },
        {
            "q": "حرف الراء مع مد الألف يُلفظ:",
            "options": ["رو", "ري", "را", "رَ"],
            "ans": "را",
            "type": "mcq",
            "exp": "ر + ا = را.",
        },
        {
            "q": "كلمة (راعي) تحتوي على المقطع:",
            "options": ["دا", "را", "با", "ما"],
            "ans": "را",
            "type": "mcq",
            "exp": "تبدأ بمقطع را.",
        },
        {
            "q": "صح أم خطأ: حرف الراء يشبه حرف الزاي ولكن بدون نقطة.",
            "options": ["صح", "خطأ"],
            "ans": "صح",
            "type": "tf",
            "exp": "الراء بدون نقطة والزاي بنقطة.",
        },
        {
            "q": "أكمل الفراغ: المقطع الأول في كلمة (رامي) هو ...",
            "options": ["ما", "را", "مي", "دا"],
            "ans": "را",
            "type": "fill",
            "exp": "را + مي = رامي.",
        },
        {
            "q": "رتب الحروف لتكوين كلمة مفيدة: (ا - ر - م - ي)",
            "options": ["رامي", "ماري", "يشار", "ريما"],
            "ans": "رامي",
            "type": "reorder",
            "exp": "تكوّن كلمة رامي.",
        },
        {
            "q": "ما عدد حروف كلمة (راس)؟",
            "options": ["2", "3", "4", "5"],
            "ans": "3",
            "type": "mcq",
            "exp": "ر - ا - س (3 حروف).",
        },
        {
            "q": "أي الكلمات التالية تشتمل على مقطع (را)؟",
            "options": ["داري", "دور", "دود", "توت"],
            "ans": "داري",
            "type": "mcq",
            "exp": "دا - ري تحتوي الراء.",
        },
        {
            "q": "صح أم خطأ: نكتب حرف الراء بنزول جزء منه تحت السطر.",
            "options": ["صح", "خطأ"],
            "ans": "صح",
            "type": "tf",
            "exp": "سن الراء على السطر وجسمه ينزل تحت السطر.",
        },
        {
            "q": (
                "ما الكلمة المختلفة بين الكلمات التالية؟ (رامي - راما - راعي -"
                " باب)"
            ),
            "options": ["رامي", "راما", "راعي", "باب"],
            "ans": "باب",
            "type": "mcq",
            "exp": "كلمة باب لا تحتوي على حرف الراء.",
        },
    ],
}]


# --- PDF Certificate Generation Function ---
def generate_pdf_cert(student_name, score, level, cert_id, issue_date):
  pdf = FPDF(orientation="L", unit="mm", format="A4")
  pdf.add_page()

  pdf.set_line_width(2)
  pdf.set_draw_color(142, 36, 170)
  pdf.rect(10, 10, 277, 190)

  pdf.set_line_width(0.1)
  pdf.set_draw_color(216, 27, 96)
  pdf.rect(14, 14, 269, 182)

  pdf.set_font("Helvetica", "B", 24)
  pdf.set_text_color(106, 27, 154)
  pdf.cell(
      0,
      25,
      "PALESTINIAN LANGUAGE CURRICULUM CERTIFICATE",
      new_x="LMARGIN",
      new_y="NEXT",
      align="C",
  )

  pdf.set_font("Helvetica", "B", 16)
  pdf.set_text_color(216, 27, 96)
  pdf.cell(
      0,
      12,
      "Interactive Arabic Platform - First Grade (Part 1)",
      new_x="LMARGIN",
      new_y="NEXT",
      align="C",
  )
  pdf.cell(
      0,
      10,
      "Teacher: Sheima Yahya",
      new_x="LMARGIN",
      new_y="NEXT",
      align="C",
  )

  pdf.ln(10)
  pdf.set_font("Helvetica", "", 14)
  pdf.set_text_color(0, 0, 0)
  pdf.cell(
      0,
      10,
      f"This is to certify that student: {student_name}",
      new_x="LMARGIN",
      new_y="NEXT",
      align="C",
  )
  pdf.cell(
      0,
      10,
      "has successfully passed the Final Arabic Examination with a score of:"
      f" {score:.1f}%",
      new_x="LMARGIN",
      new_y="NEXT",
      align="C",
  )
  pdf.cell(
      0,
      10,
      f"Achieved Title Level: {level}",
      new_x="LMARGIN",
      new_y="NEXT",
      align="C",
  )

  pdf.ln(15)
  pdf.set_font("Helvetica", "I", 11)
  pdf.set_text_color(100, 100, 100)
  pdf.cell(130, 8, f"Certificate ID: {cert_id}", align="L")
  pdf.cell(
      130,
      8,
      f"Date of Issue: {issue_date}",
      align="R",
      new_x="LMARGIN",
      new_y="NEXT",
  )

  cert_dir = "certs"
  os.makedirs(cert_dir, exist_ok=True)
  file_path = os.path.join(cert_dir, f"{cert_id}.pdf")
  pdf.output(file_path)
  return file_path


# --- Session State Initialization ---
if "current_student" not in st.session_state:
  st.session_state.current_student = None

# --- Main App Layout ---
st.markdown(
    """
<div class="header-card">
    <h1>منصة اللغة العربية التفاعلية للصف الأول الأساسي 🇵🇸</h1>
    <h3>إعداد وتصاميم المعلمة: شيماء يحيى | الجزء الأول 2020</h3>
</div>
""",
    unsafe_allow_html=True,
)

if not st.session_state.current_student:
  st.markdown('<div class="content-box">', unsafe_allow_html=True)
  st.subheader("👋 أهلاً بك يا بطل العربية! سجل اسمك للبدء")
  student_name_input = st.text_input(
      "ادخل اسم الطالب / الطالبة الثلاثي:", placeholder="مثال: أحمد رامي محمود"
  )
  if st.button("ابدأ التعلّم 🚀"):
    if student_name_input.strip():
      student = get_or_create_student(student_name_input.strip())
      st.session_state.current_student = student
      st.success(f"مرحباً بك يا {student['name']}! نتمنى لك رحلة ممتعة 🌟")
      st.rerun()
    else:
      st.warning("يرجى إدخال اسم الطالب قبل المتابعة.")
  st.markdown("</div>", unsafe_allow_html=True)
  st.stop()

student = get_or_create_student(st.session_state.current_student["name"])
st.session_state.current_student = student

with st.sidebar:
  st.title(f"👤 {student['name']}")
  col_sb1, col_sb2 = st.columns(2)
  col_sb1.metric("النقاط (XP)", f"⭐ {student['xp']}")
  col_sb2.metric("المستوى", student["level"])
  st.markdown("---")
  menu_choice = st.radio(
      "القائمة الرئيسية:", [
          "📖 قائمة الدروس والشرح",
          "🎮 زاوية الألعاب التفاعلية",
          "🏆 لوحة المتصدرين",
          "🎓 الشهادة الرقمية",
          "👩‍🏫 لوحة إدارة المعلمة",
      ]
  )
  st.markdown("---")
  if st.button("🚪 تسجيل الخروج / تغيير الطالب"):
    st.session_state.current_student = None
    st.rerun()

if menu_choice == "📖 قائمة الدروس والشرح":
  st.subheader("📚 دروس كتاب لغتنا الجميلة - الصف الأول")
  lesson_titles = [
      f"{l['id']}. {l['title']} ({l['unit']})" for l in LESSONS_DATA
  ]
  selected_lesson_idx = st.selectbox(
      "اختر الدرس المطلوب:",
      range(len(LESSONS_DATA)),
      format_func=lambda i: lesson_titles[i],
  )
  lesson = LESSONS_DATA[selected_lesson_idx]

  st.markdown(f"### {lesson['title']}")
  st.write(lesson["explanation"])

elif menu_choice == "🏆 لوحة المتصدرين":
  st.subheader("🏆 لوحة المتصدرين العامة للطلاب")
  df_lb = get_leaderboard()
  st.dataframe(df_lb, use_container_width=True)
    elif menu_choice == "👩‍🏫 لوحة إدارة المعلمة":)
    st.subheader("👩‍🏫 لوحة الإدارة والتحكم - المعلمة شيماء يحيى")
    st.write("أهلاً بكِ معلمة شيماء! يمكنكِ متابعة أداء الطلاب وتحديث شرط الشهادة وتصدير البيانات.")

