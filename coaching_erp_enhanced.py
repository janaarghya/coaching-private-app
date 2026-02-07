import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
import qrcode
import urllib.parse

# ================= UI CONFIG =================
st.set_page_config(
    page_title="Coaching ERP",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================= CUSTOM CSS =================
st.markdown("""
<style>
    /* Mobile-first responsive design */
    .block-container {
        padding: 1rem 1rem 3rem 1rem;
        max-width: 1200px;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Modern Card Design */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 20px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        margin-bottom: 1rem;
        transition: transform 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 32px rgba(0,0,0,0.18);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        color: white;
        margin: 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: rgba(255,255,255,0.8);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 0.5rem;
    }
    
    /* Section Headers */
    .section-header {
        font-size: 1.8rem;
        font-weight: 700;
        margin: 2rem 0 1rem 0;
        color: #1f2937;
        border-bottom: 3px solid #667eea;
        padding-bottom: 0.5rem;
    }
    
    /* Login Container */
    .login-container {
        max-width: 400px;
        margin: 4rem auto;
        padding: 2rem;
        background: white;
        border-radius: 24px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.1);
    }
    
    .login-title {
        text-align: center;
        font-size: 2rem;
        font-weight: 800;
        color: #667eea;
        margin-bottom: 2rem;
    }
    
    /* Button Styles */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        width: 100%;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(102,126,234,0.3);
    }
    
    /* Input Fields */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select {
        border-radius: 12px;
        border: 2px solid #e5e7eb;
        padding: 0.75rem;
        font-size: 1rem;
        transition: border-color 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
    }
    
    /* Navigation Tabs */
    .nav-container {
        background: white;
        border-radius: 16px;
        padding: 0.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        overflow-x: auto;
        display: flex;
        gap: 0.5rem;
    }
    
    .nav-tab {
        padding: 0.75rem 1.5rem;
        border-radius: 12px;
        background: transparent;
        border: none;
        cursor: pointer;
        font-weight: 600;
        color: #6b7280;
        transition: all 0.3s ease;
        white-space: nowrap;
    }
    
    .nav-tab:hover {
        background: #f3f4f6;
        color: #667eea;
    }
    
    .nav-tab.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* Data Tables */
    .dataframe {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    
    /* Success/Error Messages */
    .stSuccess, .stError, .stWarning {
        border-radius: 12px;
        padding: 1rem;
    }
    
    /* QR Code Container */
    .qr-container {
        background: white;
        padding: 2rem;
        border-radius: 16px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin: 1rem 0;
    }
    
    /* Mobile Responsive */
    @media (max-width: 768px) {
        .block-container {
            padding: 0.5rem 0.5rem 3rem 0.5rem;
        }
        
        .metric-value {
            font-size: 1.5rem;
        }
        
        .section-header {
            font-size: 1.4rem;
        }
        
        .login-container {
            margin: 2rem 1rem;
            padding: 1.5rem;
        }
    }
    
    /* Status Badge */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .status-active {
        background: #d1fae5;
        color: #065f46;
    }
    
    .status-pending {
        background: #fef3c7;
        color: #92400e;
    }
    
    /* WhatsApp Link */
    .whatsapp-link {
        display: inline-block;
        background: #25D366;
        color: white;
        padding: 0.75rem 1.5rem;
        border-radius: 12px;
        text-decoration: none;
        font-weight: 600;
        margin-top: 1rem;
        transition: all 0.3s ease;
    }
    
    .whatsapp-link:hover {
        background: #20ba5a;
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)

# ================= DATABASE =================
conn = sqlite3.connect("coaching.db", check_same_thread=False)
c = conn.cursor()

# Create tables
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

# ================= CONFIG =================
USERS = {"Arghya": "Arghya@9382", "Suman": "Suman@8348", "Tapan": "Tapan@6296"}
UPI_ID = "yourupi@bank"  # CHANGE THIS

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.page = "🏠 Overview"

# ================= HELPER FUNCTIONS =================

def generate_receipt(student_id, amount, mode):
    """Generate PDF receipt"""
    student = c.execute("SELECT name, course, phone FROM students WHERE id=?", (student_id,)).fetchone()
    
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    
    elems = []
    
    # Title
    title = Paragraph("<b>COACHING FEE RECEIPT</b>", styles["Title"])
    elems.append(title)
    elems.append(Spacer(1, 30))
    
    # Receipt details
    data = [
        ["Receipt ID:", f"RCP-{student_id}-{datetime.now().strftime('%Y%m%d%H%M')}"],
        ["Student Name:", student[0]],
        ["Course:", student[1]],
        ["Phone:", student[2]],
        ["Amount Paid:", f"₹ {amount:.2f}"],
        ["Payment Mode:", mode.upper()],
        ["Date:", datetime.now().strftime("%d-%m-%Y %I:%M %p")],
    ]
    
    table = Table(data, colWidths=[150, 300])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#667eea')),
    ]))
    
    elems.append(table)
    elems.append(Spacer(1, 40))
    
    # Footer
    footer = Paragraph("<i>Thank you for your payment!</i>", styles["Normal"])
    elems.append(footer)
    
    doc.build(elems)
    buf.seek(0)
    return buf


def upi_qr(amount):
    """Generate UPI QR code"""
    link = f"upi://pay?pa={UPI_ID}&pn=CoachingCentre&am={amount}&cu=INR"
    img = qrcode.make(link)
    img = img.resize((300, 300))
    b = BytesIO()
    img.save(b, format="PNG")
    b.seek(0)
    return b


def whatsapp_link(phone, msg):
    """Generate WhatsApp link"""
    clean_phone = phone.replace("+", "").replace("-", "").replace(" ", "")
    if not clean_phone.startswith("91"):
        clean_phone = "91" + clean_phone
    return f"https://wa.me/{clean_phone}?text={urllib.parse.quote(msg)}"


def metric_card(label, value, icon="📊"):
    """Create a metric card"""
    return f"""
    <div class="metric-card">
        <div style="font-size: 2rem;">{icon}</div>
        <p class="metric-value">{value}</p>
        <p class="metric-label">{label}</p>
    </div>
    """

# ================= LOGIN PAGE =================

def login_page():
    """Login interface"""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    st.markdown('<h1 class="login-title">🎓 Coaching ERP</h1>', unsafe_allow_html=True)
    st.markdown("### Welcome Back!")
    
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", type="password", placeholder="Enter password")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submit = st.form_submit_button("LOGIN", use_container_width=True)
        
        if submit:
            if username in USERS and USERS[username] == password:
                st.session_state.logged_in = True
                st.session_state.user = username
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid credentials")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Demo credentials hint
    st.markdown("---")
    st.markdown("*Demo: arghya / 1234*")


# ================= DASHBOARD PAGES =================

def overview_page():
    """Overview dashboard"""
    st.markdown("# 🏠 Dashboard Overview")
    
    # Fetch metrics
    try:
        total_students = c.execute("SELECT COUNT(*) FROM students WHERE status='active'").fetchone()[0]
    except:
        total_students = c.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    
    total_income = c.execute("SELECT SUM(amount) FROM payments").fetchone()[0] or 0
    total_expense = c.execute("SELECT SUM(amount) FROM expenses").fetchone()[0] or 0
    profit = total_income - total_expense
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(metric_card("Active Students", total_students, "👥"), unsafe_allow_html=True)
    
    with col2:
        st.markdown(metric_card("Total Income", f"₹{total_income:,.0f}", "💰"), unsafe_allow_html=True)
    
    with col3:
        st.markdown(metric_card("Total Expense", f"₹{total_expense:,.0f}", "📉"), unsafe_allow_html=True)
    
    with col4:
        color = "🟢" if profit >= 0 else "🔴"
        st.markdown(metric_card("Net Profit", f"₹{profit:,.0f}", color), unsafe_allow_html=True)
    
    # Recent activity
    st.markdown("---")
    st.markdown("### 📊 Recent Payments")
    
    recent_payments = pd.read_sql_query("""
        SELECT p.date, s.name, p.amount, p.mode 
        FROM payments p
        JOIN students s ON p.student_id = s.id
        ORDER BY p.id DESC LIMIT 5
    """, conn)
    
    if not recent_payments.empty:
        st.dataframe(recent_payments, use_container_width=True, hide_index=True)
    else:
        st.info("No payments recorded yet")


def students_page():
    """Student management"""
    st.markdown("# 🎓 Student Management")
    
    # Add student form
    with st.expander("➕ Add New Student", expanded=False):
        with st.form("add_student_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Student Name*", placeholder="Enter full name")
                phone = st.text_input("Phone Number*", placeholder="10-digit mobile")
            
            with col2:
                course = st.text_input("Course*", placeholder="e.g., JEE/NEET")
                fee = st.number_input("Total Fee (₹)*", min_value=0.0, step=100.0)
            
            submitted = st.form_submit_button("Add Student", use_container_width=True)
            
            if submitted:
                if name and phone and course and fee > 0:
                    c.execute("INSERT INTO students VALUES (NULL,?,?,?,?,?,'active',?)",
                             (name, phone, course, fee, 0, datetime.now().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success(f"✅ Student '{name}' added successfully!")
                    st.rerun()
                else:
                    st.error("Please fill all required fields")
    
    # Display students
    st.markdown("### 📋 All Students")
    
    students_df = pd.read_sql_query("""
        SELECT 
            id as 'ID',
            name as 'Name',
            phone as 'Phone',
            course as 'Course',
            fee as 'Total Fee',
            paid as 'Paid',
            (fee - paid) as 'Pending',
            status as 'Status',
            date as 'Enrolled'
        FROM students
        ORDER BY id DESC
    """, conn)
    
    if not students_df.empty:
        # Search filter
        search = st.text_input("🔍 Search students", placeholder="Search by name or phone")
        if search:
            students_df = students_df[
                students_df['Name'].str.contains(search, case=False, na=False) |
                students_df['Phone'].str.contains(search, case=False, na=False)
            ]
        
        st.dataframe(students_df, use_container_width=True, hide_index=True)
        
        # Statistics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Students", len(students_df))
        col2.metric("Total Fees", f"₹{students_df['Total Fee'].sum():,.0f}")
        col3.metric("Pending", f"₹{students_df['Pending'].sum():,.0f}")
    else:
        st.info("No students added yet. Add your first student above!")


def payments_page():
    """Payment collection"""
    st.markdown("# 💰 Payment Collection")
    
    # Payment form
    with st.form("payment_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Get student list
            students = c.execute("SELECT id, name, (fee - paid) as pending FROM students WHERE status='active'").fetchall()
            student_options = {f"{s[0]} - {s[1]} (Pending: ₹{s[2]:.0f})": s[0] for s in students}
            
            selected_student = st.selectbox("Select Student*", options=list(student_options.keys()))
            student_id = student_options[selected_student] if selected_student else None
            
            amount = st.number_input("Amount (₹)*", min_value=0.0, step=100.0)
        
        with col2:
            mode = st.selectbox("Payment Mode*", ["Cash", "UPI", "Online Transfer", "Cheque"])
            st.write("")  # Spacing
            st.write("")  # Spacing
            submit = st.form_submit_button("💳 Record Payment", use_container_width=True)
        
        # Show UPI QR if selected
        if mode == "UPI" and amount > 0:
            st.markdown("---")
            st.markdown("### 📱 Scan to Pay")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(upi_qr(amount), caption=f"Pay ₹{amount:.2f}")
        
        if submit and student_id and amount > 0:
            # Record payment
            c.execute("INSERT INTO payments VALUES (NULL,?,?,?,?)",
                     (student_id, amount, mode.lower(), datetime.now().strftime("%Y-%m-%d")))
            c.execute("UPDATE students SET paid = paid + ? WHERE id=?", (amount, student_id))
            conn.commit()
            
            st.success(f"✅ Payment of ₹{amount:.2f} recorded successfully!")
            
            # Generate receipt
            receipt = generate_receipt(student_id, amount, mode)
            st.download_button(
                "📄 Download Receipt",
                receipt,
                f"receipt_{student_id}_{datetime.now().strftime('%Y%m%d')}.pdf",
                "application/pdf",
                use_container_width=True
            )
            
            # WhatsApp notification
            student_data = c.execute("SELECT name, phone FROM students WHERE id=?", (student_id,)).fetchone()
            msg = f"Dear {student_data[0]}, your payment of ₹{amount:.2f} has been received. Thank you!"
            wa_link = whatsapp_link(student_data[1], msg)
            
            st.markdown(f'<a href="{wa_link}" target="_blank" class="whatsapp-link">📱 Send WhatsApp Receipt</a>', unsafe_allow_html=True)
    
    # Recent payments
    st.markdown("---")
    st.markdown("### 📊 Recent Payments")
    
    payments_df = pd.read_sql_query("""
        SELECT 
            p.id as 'ID',
            p.date as 'Date',
            s.name as 'Student',
            p.amount as 'Amount',
            p.mode as 'Mode'
        FROM payments p
        JOIN students s ON p.student_id = s.id
        ORDER BY p.id DESC
        LIMIT 20
    """, conn)
    
    if not payments_df.empty:
        st.dataframe(payments_df, use_container_width=True, hide_index=True)
    else:
        st.info("No payments recorded yet")


def expenses_page():
    """Expense management"""
    st.markdown("# 📉 Expense Management")
    
    # Add expense
    with st.expander("➕ Add New Expense", expanded=False):
        with st.form("expense_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                title = st.text_input("Expense Title*", placeholder="e.g., Rent, Salary")
                amount = st.number_input("Amount (₹)*", min_value=0.0, step=100.0)
            
            with col2:
                category = st.selectbox("Category*", [
                    "Rent", "Salary", "Utilities", "Stationery", 
                    "Marketing", "Maintenance", "Other"
                ])
            
            submitted = st.form_submit_button("Add Expense", use_container_width=True)
            
            if submitted and title and amount > 0:
                c.execute("INSERT INTO expenses VALUES (NULL,?,?,?,?)",
                         (title, amount, category, datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                st.success(f"✅ Expense '{title}' added successfully!")
                st.rerun()
    
    # Display expenses
    st.markdown("### 📋 All Expenses")
    
    expenses_df = pd.read_sql_query("""
        SELECT 
            id as 'ID',
            date as 'Date',
            title as 'Title',
            category as 'Category',
            amount as 'Amount'
        FROM expenses
        ORDER BY id DESC
    """, conn)
    
    if not expenses_df.empty:
        st.dataframe(expenses_df, use_container_width=True, hide_index=True)
        
        # Summary
        col1, col2 = st.columns(2)
        col1.metric("Total Expenses", f"₹{expenses_df['Amount'].sum():,.0f}")
        col2.metric("This Month", f"₹{expenses_df[expenses_df['Date'].str.startswith(datetime.now().strftime('%Y-%m'))]['Amount'].sum():,.0f}")
    else:
        st.info("No expenses recorded yet")


def analytics_page():
    """Finance analytics"""
    st.markdown("# 📊 Financial Analytics")
    
    # Date-wise analysis
    st.markdown("### 📈 Income vs Expense Trend")
    
    income_df = pd.read_sql_query("""
        SELECT date, SUM(amount) as income 
        FROM payments 
        GROUP BY date 
        ORDER BY date
    """, conn)
    
    expense_df = pd.read_sql_query("""
        SELECT date, SUM(amount) as expense 
        FROM expenses 
        GROUP BY date 
        ORDER BY date
    """, conn)
    
    if not income_df.empty or not expense_df.empty:
        # Merge dataframes
        df = pd.merge(income_df, expense_df, on="date", how="outer").fillna(0)
        df['profit'] = df['income'] - df['expense']
        
        # Line chart
        st.line_chart(df.set_index("date")[['income', 'expense', 'profit']])
        
        # Summary
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"₹{df['income'].sum():,.0f}")
        col2.metric("Total Expense", f"₹{df['expense'].sum():,.0f}")
        col3.metric("Net Profit", f"₹{df['profit'].sum():,.0f}")
    else:
        st.info("Not enough data for analysis yet")
    
    # Category-wise expenses
    st.markdown("---")
    st.markdown("### 📊 Expense Breakdown by Category")
    
    category_df = pd.read_sql_query("""
        SELECT category, SUM(amount) as total
        FROM expenses
        GROUP BY category
        ORDER BY total DESC
    """, conn)
    
    if not category_df.empty:
        st.bar_chart(category_df.set_index('category'))
    else:
        st.info("No expense data available")


# ================= MAIN APP =================

def main():
    if not st.session_state.logged_in:
        login_page()
    else:
        # Top bar with user info and logout
        col1, col2, col3 = st.columns([2, 3, 1])
        
        with col1:
            st.markdown(f"### 👋 Welcome, **{st.session_state.user}**")
        
        with col3:
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.user = None
                st.rerun()
        
        st.markdown("---")
        
        # Navigation tabs
        tabs = st.tabs(["🏠 Overview", "🎓 Students", "💰 Payments", "📉 Expenses", "📊 Analytics"])
        
        with tabs[0]:
            overview_page()
        
        with tabs[1]:
            students_page()
        
        with tabs[2]:
            payments_page()
        
        with tabs[3]:
            expenses_page()
        
        with tabs[4]:
            analytics_page()


if __name__ == "__main__":
    main()
