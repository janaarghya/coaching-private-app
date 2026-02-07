import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
import qrcode
import urllib.parse

# ================= UI CONFIG =================
st.set_page_config(page_title="Coaching ERP", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1rem;}
.metric-card {
    background: #111827;
    padding: 18px;
    border-radius: 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}
.section-title {font-size:22px;font-weight:700;margin-top:10px;}
</style>
""", unsafe_allow_html=True)

# ================= DATABASE =================
conn = sqlite3.connect("coaching.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT,
    course TEXT,
    fee REAL,
    paid REAL,
    status TEXT,
    date TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    amount REAL,
    mode TEXT,
    date TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    amount REAL,
    category TEXT,
    date TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS investments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    partner TEXT,
    amount REAL,
    date TEXT
)""")

conn.commit()

# ================= LOGIN =================
USERS = {"arghya": "1234", "friend1": "1234", "friend2": "1234"}
UPI_ID = "yourupi@bank"  # CHANGE

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None


def login():
    st.title("🏫 Coaching Centre ERP Login")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u in USERS and USERS[u] == p:
            st.session_state.logged_in = True
            st.session_state.user = u
            st.rerun()
        else:
            st.error("Wrong credentials")


# ================= HELPERS =================

def generate_receipt(student_id, amount, mode):
    student = c.execute("SELECT name, course FROM students WHERE id=?", (student_id,)).fetchone()

    buf = BytesIO()
    doc = SimpleDocTemplate(buf)
    styles = getSampleStyleSheet()

    elems = []
    elems.append(Paragraph("Coaching Fee Receipt", styles["Title"]))
    elems.append(Spacer(1, 20))

    table = Table([
        ["Student", student[0]],
        ["Course", student[1]],
        ["Amount", f"₹ {amount}"],
        ["Mode", mode],
        ["Date", datetime.now().strftime("%Y-%m-%d")],
    ])

    elems.append(table)
    doc.build(elems)
    buf.seek(0)
    return buf


def upi_qr(amount):
    link = f"upi://pay?pa={UPI_ID}&pn=Coaching&am={amount}&cu=INR"
    img = qrcode.make(link)
    b = BytesIO()
    img.save(b, format="PNG")
    b.seek(0)
    return b


def whatsapp_link(phone, msg):
    return f"https://wa.me/91{phone}?text={urllib.parse.quote(msg)}"


# ================= DASHBOARD =================

def dashboard():
    st.sidebar.title(f"👋 {st.session_state.user}")
    page = st.sidebar.radio("Menu", [
        "🏠 Overview",
        "🎓 Students",
        "💰 Payments",
        "📉 Expenses",
        "📊 Finance Analytics",
        "🚪 Logout",
    ])

    
    # ---------- OVERVIEW ----------
if page == "🏠 Overview":
    st.title("🏠 Business Overview")

    # Safe student count
    try:
        total_students = c.execute(
            "SELECT COUNT(*) FROM students WHERE status='active'"
        ).fetchone()[0]
    except:
        total_students = c.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]

    # Safe sums
    total_income = c.execute(
        "SELECT COALESCE(SUM(amount),0) FROM payments"
    ).fetchone()[0]

    total_expense = c.execute(
        "SELECT COALESCE(SUM(amount),0) FROM expenses"
    ).fetchone()[0]

    profit = total_income - total_expense

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Students", total_students)
    c2.metric("Income", f"₹ {total_income:.0f}")
    c3.metric("Expense", f"₹ {total_expense:.0f}")
    c4.metric("Profit", f"₹ {profit:.0f}")


    # ---------- STUDENTS ----------
    if page == "🎓 Students":
        st.subheader("Add Student")

        name = st.text_input("Name")
        phone = st.text_input("Phone")
        course = st.text_input("Course")
        fee = st.number_input("Total Fee", min_value=0.0)

        if st.button("Add Student") and name:
            c.execute("INSERT INTO students VALUES (NULL,?,?,?,?,?,'active',?)",
                      (name, phone, course, fee, 0, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            st.success("Student added")

        df = pd.read_sql_query("SELECT * FROM students", conn)
        st.dataframe(df)

    # ---------- PAYMENTS ----------
    if page == "💰 Payments":
        sid = st.number_input("Student ID", min_value=1)
        amt = st.number_input("Amount", min_value=0.0)
        mode = st.selectbox("Mode", ["cash", "upi", "online"])

        if mode == "upi" and amt > 0:
            st.image(upi_qr(amt))

        if st.button("Record Payment"):
            c.execute("INSERT INTO payments VALUES (NULL,?,?,?,?)",
                      (sid, amt, mode, datetime.now().strftime("%Y-%m-%d")))
            c.execute("UPDATE students SET paid = paid + ? WHERE id=?", (amt, sid))
            conn.commit()

            receipt = generate_receipt(sid, amt, mode)
            st.download_button("Download Receipt", receipt, "receipt.pdf")

            phone = c.execute("SELECT phone FROM students WHERE id=?", (sid,)).fetchone()[0]
            msg = f"Payment of ₹{amt} received. Thank you!"
            st.markdown(f"[Send WhatsApp]({whatsapp_link(phone,msg)})")

    # ---------- EXPENSES ----------
    if page == "📉 Expenses":
        title = st.text_input("Expense title")
        amt = st.number_input("Amount", min_value=0.0)
        cat = st.text_input("Category")

        if st.button("Add Expense") and title:
            c.execute("INSERT INTO expenses VALUES (NULL,?,?,?,?)",
                      (title, amt, cat, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            st.success("Expense added")

        df = pd.read_sql_query("SELECT * FROM expenses", conn)
        st.dataframe(df)

    # ---------- ANALYTICS ----------
    if page == "📊 Finance Analytics":
        st.subheader("Income vs Expense")

        income = pd.read_sql_query("SELECT date, SUM(amount) as income FROM payments GROUP BY date", conn)
        expense = pd.read_sql_query("SELECT date, SUM(amount) as expense FROM expenses GROUP BY date", conn)

        df = pd.merge(income, expense, on="date", how="outer").fillna(0)
        st.line_chart(df.set_index("date"))

    # ---------- LOGOUT ----------
    if page == "🚪 Logout":
        st.session_state.logged_in = False
        st.rerun()


# ================= RUN =================
if not st.session_state.logged_in:
    login()
else:
    dashboard()



