import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
import qrcode
import urllib.parse

# ---------------- DATABASE ----------------
conn = sqlite3.connect("coaching.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT,
    course TEXT,
    fee REAL,
    paid REAL,
    status TEXT,
    date TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    amount REAL,
    mode TEXT,
    date TEXT
)
""")

conn.commit()

# ---------------- LOGIN ----------------
USERS = {"arghya": "1234", "friend1": "1234", "friend2": "1234"}

UPI_ID = "yourupi@bank"  # CHANGE THIS

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None


def login():
    st.title("Coaching Centre ERP Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in USERS and USERS[username] == password:
            st.session_state.logged_in = True
            st.session_state.user = username
            st.rerun()
        else:
            st.error("Wrong username or password")


# ---------------- STUDENT FUNCTIONS ----------------

def add_student(name, phone, course, fee, paid):
    c.execute(
        "INSERT INTO students (name, phone, course, fee, paid, status, date) VALUES (?, ?, ?, ?, ?, 'active', ?)",
        (name, phone, course, fee, paid, datetime.now().strftime("%Y-%m-%d")),
    )
    student_id = c.lastrowid

    if paid > 0:
        c.execute(
            "INSERT INTO payments (student_id, amount, mode, date) VALUES (?, ?, 'offline', ?)",
            (student_id, paid, datetime.now().strftime("%Y-%m-%d")),
        )

    conn.commit()


def get_students():
    return c.execute(
        "SELECT id, name, phone, course, fee, paid, status, date FROM students"
    ).fetchall()


def add_payment(student_id, amount, mode):
    c.execute(
        "INSERT INTO payments (student_id, amount, mode, date) VALUES (?, ?, ?, ?)",
        (student_id, amount, mode, datetime.now().strftime("%Y-%m-%d")),
    )

    c.execute("UPDATE students SET paid = paid + ? WHERE id=?", (amount, student_id))

    conn.commit()


def get_payments(student_id):
    return c.execute(
        "SELECT amount, mode, date FROM payments WHERE student_id=?", (student_id,)
    ).fetchall()


def get_student_phone(student_id):
    row = c.execute("SELECT phone, name FROM students WHERE id=?", (student_id,)).fetchone()
    return row if row else (None, None)


# ---------------- RECEIPT GENERATOR ----------------

def generate_receipt(student_id, amount, mode):
    student = c.execute("SELECT name, course FROM students WHERE id=?", (student_id,)).fetchone()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    elements = []
    elements.append(Paragraph("Coaching Centre Payment Receipt", styles["Title"]))
    elements.append(Spacer(1, 20))

    data = [
        ["Student ID", str(student_id)],
        ["Name", student[0]],
        ["Course", student[1]],
        ["Amount Paid", f"₹ {amount}"],
        ["Payment Mode", mode],
        ["Date", datetime.now().strftime("%Y-%m-%d")],
    ]

    elements.append(Table(data))

    doc.build(elements)
    buffer.seek(0)
    return buffer


# ---------------- UPI QR ----------------

def generate_upi_qr(amount, name="Coaching Centre"):
    upi_link = f"upi://pay?pa={UPI_ID}&pn={name}&am={amount}&cu=INR"
    qr = qrcode.make(upi_link)

    buf = BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ---------------- WHATSAPP LINK ----------------

def whatsapp_link(student_id, amount, mode):
    phone, name = get_student_phone(student_id)
    if not phone:
        return None

    message = f"Hello {name}, your payment of ₹{amount} via {mode} is received. Thank you!"
    encoded = urllib.parse.quote(message)

    return f"https://wa.me/91{phone}?text={encoded}"


# ---------------- DASHBOARD ----------------

def dashboard():
    st.set_page_config(page_title="Coaching ERP", layout="wide")

    st.sidebar.title(f"Welcome, {st.session_state.user}")
    page = st.sidebar.radio(
        "Menu",
        ["Add Student", "Students List", "Payments", "UPI Collect", "Summary", "Logout"],
    )

    if page == "Logout":
        st.session_state.logged_in = False
        st.rerun()

    # -------- ADD STUDENT --------
    if page == "Add Student":
        st.header("Add New Student")

        name = st.text_input("Student Name")
        phone = st.text_input("Phone Number")
        course = st.text_input("Course Name")
        fee = st.number_input("Total Fee", min_value=0.0)
        paid = st.number_input("Initial Payment", min_value=0.0)

        if st.button("Add Student") and name:
            add_student(name, phone, course, fee, paid)
            st.success("Student added successfully")

    # -------- PAYMENTS --------
    if page == "Payments":
        st.header("Offline Payment Entry")

        sid = st.number_input("Student ID", min_value=1, step=1)
        amount = st.number_input("Payment Amount", min_value=0.0)

        if st.button("Add Offline Payment"):
            add_payment(sid, amount, "offline")
            receipt = generate_receipt(sid, amount, "offline")
            st.download_button("Download Receipt", receipt, "receipt.pdf")

            link = whatsapp_link(sid, amount, "offline")
            if link:
                st.markdown(f"[Send Receipt via WhatsApp]({link})")

    # -------- UPI --------
    if page == "UPI Collect":
        st.header("Collect via UPI")

        sid = st.number_input("Student ID", min_value=1, step=1)
        amount = st.number_input("Amount", min_value=0.0)

        if amount > 0:
            st.image(generate_upi_qr(amount))

        if st.button("Confirm UPI Payment"):
            add_payment(sid, amount, "upi")
            receipt = generate_receipt(sid, amount, "upi")
            st.download_button("Download Receipt", receipt, "upi_receipt.pdf")

            link = whatsapp_link(sid, amount, "upi")
            if link:
                st.markdown(f"[Send Receipt via WhatsApp]({link})")

    # -------- SUMMARY --------
    if page == "Summary":
        st.header("Business Summary")

        df = pd.DataFrame(
            get_students(),
            columns=["ID", "Name", "Phone", "Course", "Fee", "Paid", "Status", "Date"],
        )

        if not df.empty:
            total_fee = df["Fee"].sum()
            total_paid = df["Paid"].sum()
            total_due = total_fee - total_paid

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Fees", f"₹ {total_fee:.0f}")
            c2.metric("Collected", f"₹ {total_paid:.0f}")
            c3.metric("Due", f"₹ {total_due:.0f}")


# ---------------- RUN ----------------
if not st.session_state.logged_in:
    login()
else:
    dashboard()

