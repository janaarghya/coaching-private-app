import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

# ---------------- DATABASE ----------------
conn = sqlite3.connect("coaching.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    type TEXT,
    amount REAL,
    note TEXT,
    date TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT,
    done INTEGER
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    fee REAL,
    paid REAL,
    date TEXT
)
""")

conn.commit()

# ---------------- LOGIN ----------------
USERS = {"arghya": "1234", "friend1": "1234", "friend2": "1234"}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None


def login():
    st.title("Coaching Centre Private Dashboard")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in USERS and USERS[username] == password:
            st.session_state.logged_in = True
            st.session_state.user = username
            st.rerun()
        else:
            st.error("Wrong username or password")


# ---------------- FINANCE ----------------

def add_transaction(user, ttype, amount, note):
    c.execute(
        "INSERT INTO transactions (user, type, amount, note, date) VALUES (?, ?, ?, ?, ?)",
        (user, ttype, amount, note, datetime.now().strftime("%Y-%m-%d")),
    )
    conn.commit()


def get_transactions():
    return c.execute("SELECT user, type, amount, note, date FROM transactions").fetchall()


# ---------------- TASKS ----------------

def add_task(text):
    c.execute("INSERT INTO tasks (text, done) VALUES (?, 0)", (text,))
    conn.commit()


def toggle_task(task_id, done):
    c.execute("UPDATE tasks SET done=? WHERE id=?", (done, task_id))
    conn.commit()


def get_tasks():
    return c.execute("SELECT id, text, done FROM tasks").fetchall()


# ---------------- STUDENTS ----------------

def add_student(name, fee, paid):
    c.execute(
        "INSERT INTO students (name, fee, paid, date) VALUES (?, ?, ?, ?)",
        (name, fee, paid, datetime.now().strftime("%Y-%m-%d")),
    )
    conn.commit()


def get_students():
    return c.execute("SELECT name, fee, paid, date FROM students").fetchall()


# ---------------- DASHBOARD ----------------

def dashboard():
    st.set_page_config(page_title="Coaching Dashboard", layout="wide")

    st.sidebar.title(f"Welcome, {st.session_state.user}")
    page = st.sidebar.radio(
        "Go to",
        ["Finance", "Students", "Planning", "Summary", "Reports", "Logout"],
    )

    if page == "Logout":
        st.session_state.logged_in = False
        st.rerun()

    # -------- FINANCE --------
    if page == "Finance":
        st.header("Add Transaction")

        col1, col2 = st.columns(2)
        amount = col1.number_input("Amount", min_value=0.0, step=100.0)
        note = col2.text_input("Note")

        b1, b2 = st.columns(2)
        if b1.button("Add Inflow"):
            add_transaction(st.session_state.user, "in", amount, note)
            st.success("Inflow added")

        if b2.button("Add Outflow"):
            add_transaction(st.session_state.user, "out", amount, note)
            st.success("Outflow added")

        st.subheader("Transaction History")
        st.dataframe(pd.DataFrame(get_transactions(), columns=["User", "Type", "Amount", "Note", "Date"]))

    # -------- STUDENTS --------
    if page == "Students":
        st.header("Student Fee Tracking")

        col1, col2, col3 = st.columns(3)
        name = col1.text_input("Student Name")
        fee = col2.number_input("Total Fee", min_value=0.0)
        paid = col3.number_input("Amount Paid", min_value=0.0)

        if st.button("Add Student Record") and name:
            add_student(name, fee, paid)
            add_transaction(st.session_state.user, "in", paid, f"Fee from {name}")
            st.success("Student added & payment recorded")

        st.subheader("Student Records")
        students_df = pd.DataFrame(get_students(), columns=["Name", "Fee", "Paid", "Date"])
        st.dataframe(students_df)

    # -------- PLANNING --------
    if page == "Planning":
        st.header("Tasks & Future Planning")

        new_task = st.text_input("New Task")
        if st.button("Add Task") and new_task:
            add_task(new_task)
            st.success("Task added")

        for task_id, text, done in get_tasks():
            checked = st.checkbox(text, value=bool(done))
            if checked != bool(done):
                toggle_task(task_id, int(checked))
                st.rerun()

    # -------- SUMMARY --------
    if page == "Summary":
        st.header("Business Summary")

        data = get_transactions()

        total_in = sum(a for u, t, a, n, d in data if t == "in")
        total_out = sum(a for u, t, a, n, d in data if t == "out")
        balance = total_in - total_out

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Inflow", f"₹ {total_in:.2f}")
        m2.metric("Total Outflow", f"₹ {total_out:.2f}")
        m3.metric("Net Profit", f"₹ {balance:.2f}")

        st.subheader("Partner-wise Profit Split")
        partners = {"arghya": 0, "friend1": 0, "friend2": 0}
        for u, t, a, n, d in data:
            partners[u] += a if t == "in" else -a

        split_df = pd.DataFrame(
            {"Partner": partners.keys(), "Amount": partners.values()}
        )
        st.table(split_df)

    # -------- REPORTS --------
    if page == "Reports":
        st.header("Download Reports")

        tx_df = pd.DataFrame(get_transactions(), columns=["User", "Type", "Amount", "Note", "Date"])
        st.dataframe(tx_df)

        csv = tx_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Transactions CSV", csv, "transactions.csv", "text/csv")


# ---------------- RUN ----------------
if not st.session_state.logged_in:
    login()
else:
    dashboard()
