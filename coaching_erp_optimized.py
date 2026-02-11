import streamlit as st
from datetime import datetime
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
import qrcode
import urllib.parse
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time

# ================= UI CONFIG =================
st.set_page_config(
    page_title="Coaching ERP",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================= CUSTOM CSS (Same as before) =================
st.markdown("""
<style>
    .block-container {padding: 1rem 1rem 3rem 1rem; max-width: 1200px;}
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem; border-radius: 20px; box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        margin-bottom: 1rem; transition: transform 0.3s ease;
    }
    .metric-card:hover {transform: translateY(-5px); box-shadow: 0 12px 32px rgba(0,0,0,0.18);}
    .metric-value {font-size: 2rem; font-weight: 800; color: white; margin: 0;}
    .metric-label {font-size: 0.9rem; color: rgba(255,255,255,0.8); text-transform: uppercase; letter-spacing: 1px; margin-top: 0.5rem;}
    
    .investor-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1.5rem; border-radius: 20px; box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        margin-bottom: 1rem;
    }
    
    .login-container {
        max-width: 400px; margin: 4rem auto; padding: 2rem;
        background: white; border-radius: 24px; box-shadow: 0 20px 60px rgba(0,0,0,0.1);
    }
    .login-title {text-align: center; font-size: 2rem; font-weight: 800; color: #667eea; margin-bottom: 2rem;}
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; border: none; border-radius: 12px; padding: 0.75rem 2rem;
        font-weight: 600; width: 100%; transition: all 0.3s ease;
    }
    .stButton > button:hover {transform: translateY(-2px); box-shadow: 0 8px 16px rgba(102,126,234,0.3);}
    
    .stTextInput > div > div > input, .stNumberInput > div > div > input, .stSelectbox > div > div > select {
        border-radius: 12px; border: 2px solid #e5e7eb; padding: 0.75rem; font-size: 1rem;
        transition: border-color 0.3s ease;
    }
    .stTextInput > div > div > input:focus, .stNumberInput > div > div > input:focus, .stSelectbox > div > div > select:focus {
        border-color: #667eea; box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
    }
    
    .whatsapp-link {
        display: inline-block; background: #25D366; color: white;
        padding: 0.75rem 1.5rem; border-radius: 12px; text-decoration: none;
        font-weight: 600; margin-top: 1rem; transition: all 0.3s ease;
    }
    .whatsapp-link:hover {background: #20ba5a; transform: translateY(-2px);}
    
    @media (max-width: 768px) {
        .block-container {padding: 0.5rem 0.5rem 3rem 0.5rem;}
        .metric-value {font-size: 1.5rem;}
        .login-container {margin: 2rem 1rem; padding: 1.5rem;}
    }
</style>
""", unsafe_allow_html=True)

# ================= CACHING SETUP =================

# Initialize cache in session state
if 'cache_timestamp' not in st.session_state:
    st.session_state.cache_timestamp = {}
    st.session_state.cached_data = {}

CACHE_DURATION = 30  # Cache data for 30 seconds

def is_cache_valid(key):
    """Check if cache is still valid"""
    if key not in st.session_state.cache_timestamp:
        return False
    return (time.time() - st.session_state.cache_timestamp[key]) < CACHE_DURATION

def get_cached_data(key):
    """Get data from cache"""
    if is_cache_valid(key):
        return st.session_state.cached_data[key]
    return None

def set_cached_data(key, data):
    """Store data in cache"""
    st.session_state.cached_data[key] = data
    st.session_state.cache_timestamp[key] = time.time()

def clear_cache():
    """Clear all cached data"""
    st.session_state.cache_timestamp = {}
    st.session_state.cached_data = {}

# ================= GOOGLE SHEETS SETUP =================

@st.cache_resource(ttl=3600)  # Cache for 1 hour
def init_google_sheets():
    """Initialize Google Sheets connection with caching"""
    try:
        credentials_dict = dict(st.secrets["gcp_service_account"])
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
        client = gspread.authorize(credentials)
        spreadsheet_id = st.secrets["spreadsheet_id"]
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        # Initialize sheets
        sheet_names = ['students', 'payments', 'expenses', 'investments']
        headers = {
            'students': ['id', 'name', 'phone', 'course', 'fee', 'paid', 'status', 'date'],
            'payments': ['id', 'student_id', 'amount', 'mode', 'date'],
            'expenses': ['id', 'title', 'amount', 'category', 'date'],
            'investments': ['id', 'investor', 'amount', 'date', 'notes']
        }
        
        sheets = {}
        for name in sheet_names:
            try:
                sheet = spreadsheet.worksheet(name)
            except:
                sheet = spreadsheet.add_worksheet(title=name, rows="1000", cols="10")
                sheet.update('A1', [headers[name]])
            sheets[name] = sheet
        
        return sheets
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

sheets = init_google_sheets()

# ================= DATABASE OPERATIONS WITH CACHING =================

def get_all_data(sheet_name):
    """Get all data with caching"""
    cache_key = f"data_{sheet_name}"
    
    # Try cache first
    cached = get_cached_data(cache_key)
    if cached is not None:
        return cached
    
    # Fetch from Google Sheets
    try:
        sheet = sheets[sheet_name]
        data = sheet.get_all_records()
        set_cached_data(cache_key, data)
        return data
    except Exception as e:
        st.error(f"Error fetching {sheet_name}: {e}")
        return []

def get_students_df():
    """Get students as DataFrame with caching"""
    data = get_all_data('students')
    if not data:
        return pd.DataFrame(columns=['id', 'name', 'phone', 'course', 'fee', 'paid', 'status', 'date'])
    df = pd.DataFrame(data)
    df['id'] = pd.to_numeric(df['id'], errors='coerce')
    df['fee'] = pd.to_numeric(df['fee'], errors='coerce')
    df['paid'] = pd.to_numeric(df['paid'], errors='coerce')
    return df

def get_payments_df():
    """Get payments as DataFrame with caching"""
    data = get_all_data('payments')
    if not data:
        return pd.DataFrame(columns=['id', 'student_id', 'amount', 'mode', 'date'])
    df = pd.DataFrame(data)
    df['id'] = pd.to_numeric(df['id'], errors='coerce')
    df['student_id'] = pd.to_numeric(df['student_id'], errors='coerce')
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    return df

def get_expenses_df():
    """Get expenses as DataFrame with caching"""
    data = get_all_data('expenses')
    if not data:
        return pd.DataFrame(columns=['id', 'title', 'amount', 'category', 'date'])
    df = pd.DataFrame(data)
    df['id'] = pd.to_numeric(df['id'], errors='coerce')
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    return df

def get_investments_df():
    """Get investments as DataFrame with caching"""
    data = get_all_data('investments')
    if not data:
        return pd.DataFrame(columns=['id', 'investor', 'amount', 'date', 'notes'])
    df = pd.DataFrame(data)
    df['id'] = pd.to_numeric(df['id'], errors='coerce')
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    return df

def get_next_id(sheet_name):
    """Get next ID with caching"""
    data = get_all_data(sheet_name)
    if not data:
        return 1
    max_id = max([int(record['id']) for record in data if record.get('id')])
    return max_id + 1

def add_student(name, phone, course, fee):
    """Add student and clear cache"""
    try:
        sheet = sheets['students']
        student_id = get_next_id('students')
        date = datetime.now().strftime("%Y-%m-%d")
        sheet.append_row([student_id, name, phone, course, fee, 0, 'active', date])
        clear_cache()  # Clear cache after modification
        return student_id
    except Exception as e:
        st.error(f"Error adding student: {e}")
        return None

def add_payment(student_id, amount, mode):
    """Add payment and clear cache"""
    try:
        # Add to payments
        sheet = sheets['payments']
        payment_id = get_next_id('payments')
        date = datetime.now().strftime("%Y-%m-%d")
        sheet.append_row([payment_id, student_id, amount, mode, date])
        
        # Update student paid amount
        students_sheet = sheets['students']
        all_records = students_sheet.get_all_records()
        for idx, record in enumerate(all_records, start=2):
            if int(record['id']) == student_id:
                current_paid = float(record.get('paid', 0))
                new_paid = current_paid + amount
                students_sheet.update_cell(idx, 6, new_paid)
                break
        
        clear_cache()  # Clear cache
        return payment_id
    except Exception as e:
        st.error(f"Error adding payment: {e}")
        return None

def add_expense(title, amount, category):
    """Add expense and clear cache"""
    try:
        sheet = sheets['expenses']
        expense_id = get_next_id('expenses')
        date = datetime.now().strftime("%Y-%m-%d")
        sheet.append_row([expense_id, title, amount, category, date])
        clear_cache()
        return expense_id
    except Exception as e:
        st.error(f"Error adding expense: {e}")
        return None

def add_investment(investor, amount, notes=""):
    """Add investment and clear cache"""
    try:
        sheet = sheets['investments']
        investment_id = get_next_id('investments')
        date = datetime.now().strftime("%Y-%m-%d")
        sheet.append_row([investment_id, investor, amount, date, notes])
        clear_cache()
        return investment_id
    except Exception as e:
        st.error(f"Error adding investment: {e}")
        return None

def delete_row(sheet_name, row_id):
    """Delete a row and clear cache"""
    try:
        sheet = sheets[sheet_name]
        all_records = sheet.get_all_records()
        for idx, record in enumerate(all_records, start=2):
            if int(record['id']) == row_id:
                sheet.delete_rows(idx)
                clear_cache()
                return True
        return False
    except Exception as e:
        st.error(f"Error deleting: {e}")
        return False

def get_student_by_id(student_id):
    """Get student by ID from cached data"""
    students_df = get_students_df()
    if students_df.empty:
        return None
    student = students_df[students_df['id'] == student_id]
    return student.iloc[0].to_dict() if not student.empty else None

# ================= CONFIG =================
USERS = {"Arghya": "Arghya@9382", "Tapan": "Tapan@6296", "Suman": "Suman@8348"}
UPI_ID = "yourupi@bank"
INVESTORS = ["arghya", "friend1", "friend2"]

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

# ================= HELPER FUNCTIONS =================

def generate_receipt(student_id, amount, mode):
    """Generate PDF receipt"""
    student = get_student_by_id(student_id)
    if not student:
        return None
    
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    elems = []
    
    title = Paragraph("<b>COACHING FEE RECEIPT</b>", styles["Title"])
    elems.append(title)
    elems.append(Spacer(1, 30))
    
    data = [
        ["Receipt ID:", f"RCP-{student_id}-{datetime.now().strftime('%Y%m%d%H%M')}"],
        ["Student Name:", str(student['name'])],
        ["Course:", str(student['course'])],
        ["Phone:", str(student['phone'])],
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
    clean_phone = str(phone).replace("+", "").replace("-", "").replace(" ", "")
    if not clean_phone.startswith("91"):
        clean_phone = "91" + clean_phone
    return f"https://wa.me/{clean_phone}?text={urllib.parse.quote(msg)}"

def metric_card(label, value, icon="📊"):
    return f"""<div class="metric-card">
        <div style="font-size: 2rem;">{icon}</div>
        <p class="metric-value">{value}</p>
        <p class="metric-label">{label}</p>
    </div>"""

def investor_card(name, amount, icon="💼"):
    return f"""<div class="investor-card">
        <div style="font-size: 2rem;">{icon}</div>
        <p class="metric-value">₹{amount:,.0f}</p>
        <p class="metric-label">{name}</p>
    </div>"""

# ================= LOGIN PAGE =================

def login_page():
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
    st.markdown("---")
    st.markdown("*Demo: arghya / 1234*")

# ================= DASHBOARD PAGES =================

def overview_page():
    if not sheets:
        st.error("⚠️ Google Sheets not connected.")
        return
    
    st.markdown("# 🏠 Dashboard Overview")
    
    # Add refresh button
    if st.button("🔄 Refresh Data"):
        clear_cache()
        st.rerun()
    
    students_df = get_students_df()
    payments_df = get_payments_df()
    expenses_df = get_expenses_df()
    investments_df = get_investments_df()
    
    total_students = len(students_df[students_df['status'] == 'active']) if not students_df.empty else 0
    total_income = float(payments_df['amount'].sum()) if not payments_df.empty else 0
    total_expense = float(expenses_df['amount'].sum()) if not expenses_df.empty else 0
    total_investment = float(investments_df['amount'].sum()) if not investments_df.empty else 0
    profit = total_income - total_expense
    
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
    
    st.markdown("---")
    st.markdown("### 💼 Investment Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(metric_card("Total Investment", f"₹{total_investment:,.0f}", "💼"), unsafe_allow_html=True)
    
    if not investments_df.empty:
        investor_totals = investments_df.groupby('investor')['amount'].sum().to_dict()
        cols = [col2, col3, col4]
        for idx, investor in enumerate(INVESTORS):
            if idx < len(cols):
                amount = investor_totals.get(investor, 0)
                with cols[idx]:
                    st.markdown(investor_card(investor.title(), amount, "👤"), unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📊 Recent Payments")
    
    if not payments_df.empty and not students_df.empty:
        recent = payments_df.tail(5).copy()
        recent['student_name'] = recent['student_id'].apply(
            lambda x: get_student_by_id(int(x))['name'] if get_student_by_id(int(x)) else 'Unknown'
        )
        recent = recent[['date', 'student_name', 'amount', 'mode']]
        recent.columns = ['Date', 'Student', 'Amount', 'Mode']
        st.dataframe(recent, use_container_width=True, hide_index=True)
    else:
        st.info("No payments recorded yet")

def students_page():
    if not sheets:
        st.error("⚠️ Google Sheets not connected.")
        return
    
    st.markdown("# 🎓 Student Management")
    
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
                    student_id = add_student(name, phone, course, fee)
                    if student_id:
                        st.success(f"✅ Student '{name}' added! ID: {student_id}")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("Please fill all required fields")
    
    st.markdown("### 📋 All Students")
    students_df = get_students_df()
    
    if not students_df.empty:
        display_df = students_df.copy()
        display_df['pending'] = display_df['fee'] - display_df['paid']
        display_df = display_df[['id', 'name', 'phone', 'course', 'fee', 'paid', 'pending', 'status', 'date']]
        display_df.columns = ['ID', 'Name', 'Phone', 'Course', 'Total Fee', 'Paid', 'Pending', 'Status', 'Enrolled']
        
        search = st.text_input("🔍 Search students", placeholder="Search by name or phone")
        if search:
            display_df = display_df[
                display_df['Name'].astype(str).str.contains(search, case=False, na=False) |
                display_df['Phone'].astype(str).str.contains(search, case=False, na=False)
            ]
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("### 🗑️ Delete Student")
        col1, col2 = st.columns([2, 2])
        with col1:
            delete_id = st.number_input("Student ID to Delete", min_value=1, step=1)
        with col2:
            st.write("")
            st.write("")
            if st.button("🗑️ Delete Student", type="secondary", use_container_width=True):
                if delete_row('students', int(delete_id)):
                    st.success(f"✅ Student ID {delete_id} deleted!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ Student ID {delete_id} not found!")
        
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Students", len(students_df))
        col2.metric("Total Fees", f"₹{students_df['fee'].sum():,.0f}")
        col3.metric("Pending", f"₹{(students_df['fee'] - students_df['paid']).sum():,.0f}")
    else:
        st.info("No students added yet.")

def payments_page():
    if not sheets:
        st.error("⚠️ Google Sheets not connected.")
        return
    
    st.markdown("# 💰 Payment Collection")
    
    students_df = get_students_df()
    active_students = students_df[students_df['status'] == 'active'] if not students_df.empty else pd.DataFrame()
    
    if active_students.empty:
        st.warning("⚠️ No active students found.")
        return
    
    with st.form("payment_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            student_options = {}
            for _, student in active_students.iterrows():
                pending = student['fee'] - student['paid']
                label = f"{int(student['id'])} - {student['name']} (Pending: ₹{pending:.0f})"
                student_options[label] = int(student['id'])
            
            selected_student = st.selectbox("Select Student*", options=list(student_options.keys()))
            student_id = student_options[selected_student] if selected_student else None
            amount = st.number_input("Amount (₹)*", min_value=0.0, step=100.0)
        
        with col2:
            mode = st.selectbox("Payment Mode*", ["Cash", "UPI", "Online Transfer", "Cheque"])
            st.write("")
            st.write("")
            submit = st.form_submit_button("💳 Record Payment", use_container_width=True)
        
        if mode == "UPI" and amount > 0:
            st.markdown("---")
            st.markdown("### 📱 Scan to Pay")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(upi_qr(amount), caption=f"Pay ₹{amount:.2f}")
        
        if submit and student_id and amount > 0:
            payment_id = add_payment(student_id, amount, mode.lower())
            if payment_id:
                st.success(f"✅ Payment of ₹{amount:.2f} recorded!")
                
                receipt = generate_receipt(student_id, amount, mode)
                if receipt:
                    st.download_button("📄 Download Receipt", receipt,
                        f"receipt_{student_id}_{datetime.now().strftime('%Y%m%d')}.pdf",
                        "application/pdf", use_container_width=True)
                
                student = get_student_by_id(student_id)
                if student:
                    msg = f"Dear {student['name']}, your payment of ₹{amount:.2f} has been received. Thank you!"
                    wa_link = whatsapp_link(student['phone'], msg)
                    st.markdown(f'<a href="{wa_link}" target="_blank" class="whatsapp-link">📱 Send WhatsApp Receipt</a>', unsafe_allow_html=True)
                
                time.sleep(1)
                st.rerun()
    
    st.markdown("---")
    st.markdown("### 📊 Recent Payments")
    
    payments_df = get_payments_df()
    if not payments_df.empty:
        recent = payments_df.tail(20).copy()
        recent['student_name'] = recent['student_id'].apply(
            lambda x: get_student_by_id(int(x))['name'] if get_student_by_id(int(x)) else 'Unknown'
        )
        recent = recent[['id', 'date', 'student_name', 'amount', 'mode']]
        recent.columns = ['ID', 'Date', 'Student', 'Amount', 'Mode']
        st.dataframe(recent, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("### 🗑️ Delete Payment")
        col1, col2 = st.columns([2, 2])
        with col1:
            delete_id = st.number_input("Payment ID to Delete", min_value=1, step=1, key="del_pay")
        with col2:
            st.write("")
            st.write("")
            if st.button("🗑️ Delete Payment", type="secondary", use_container_width=True):
                if delete_row('payments', int(delete_id)):
                    st.success(f"✅ Payment ID {delete_id} deleted!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ Payment ID {delete_id} not found!")
    else:
        st.info("No payments recorded yet")

def expenses_page():
    if not sheets:
        st.error("⚠️ Google Sheets not connected.")
        return
    
    st.markdown("# 📉 Expense Management")
    
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
                expense_id = add_expense(title, amount, category)
                if expense_id:
                    st.success(f"✅ Expense '{title}' added!")
                    time.sleep(1)
                    st.rerun()
    
    st.markdown("### 📋 All Expenses")
    expenses_df = get_expenses_df()
    
    if not expenses_df.empty:
        display_df = expenses_df[['id', 'date', 'title', 'category', 'amount']].copy()
        display_df.columns = ['ID', 'Date', 'Title', 'Category', 'Amount']
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("### 🗑️ Delete Expense")
        col1, col2 = st.columns([2, 2])
        with col1:
            delete_id = st.number_input("Expense ID to Delete", min_value=1, step=1, key="del_exp")
        with col2:
            st.write("")
            st.write("")
            if st.button("🗑️ Delete Expense", type="secondary", use_container_width=True):
                if delete_row('expenses', int(delete_id)):
                    st.success(f"✅ Expense ID {delete_id} deleted!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ Expense ID {delete_id} not found!")
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        col1.metric("Total Expenses", f"₹{expenses_df['amount'].sum():,.0f}")
        current_month = datetime.now().strftime('%Y-%m')
        month_expenses = expenses_df[expenses_df['date'].astype(str).str.startswith(current_month)]
        col2.metric("This Month", f"₹{month_expenses['amount'].sum():,.0f}")
    else:
        st.info("No expenses recorded yet")

def investments_page():
    if not sheets:
        st.error("⚠️ Google Sheets not connected.")
        return
    
    st.markdown("# 💼 Investment Management")
    
    with st.expander("➕ Add New Investment", expanded=False):
        with st.form("investment_form"):
            col1, col2 = st.columns(2)
            with col1:
                investor = st.selectbox("Investor*", INVESTORS)
                amount = st.number_input("Investment Amount (₹)*", min_value=0.0, step=1000.0)
            with col2:
                notes = st.text_area("Notes (Optional)", placeholder="Purpose, bank details, etc.")
            
            submitted = st.form_submit_button("Add Investment", use_container_width=True)
            
            if submitted and investor and amount > 0:
                investment_id = add_investment(investor, amount, notes)
                if investment_id:
                    st.success(f"✅ Investment of ₹{amount:,.0f} from {investor} recorded!")
                    time.sleep(1)
                    st.rerun()
    
    st.markdown("### 📋 All Investments")
    investments_df = get_investments_df()
    
    if not investments_df.empty:
        display_df = investments_df[['id', 'date', 'investor', 'amount', 'notes']].copy()
        display_df.columns = ['ID', 'Date', 'Investor', 'Amount', 'Notes']
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("### 💰 Investment Summary by Partner")
        
        investor_summary = investments_df.groupby('investor')['amount'].agg(['sum', 'count']).reset_index()
        investor_summary.columns = ['Investor', 'Total Investment', 'Number of Investments']
        
        col1, col2, col3 = st.columns(3)
        for idx, investor in enumerate(INVESTORS):
            investor_data = investor_summary[investor_summary['Investor'] == investor]
            total = float(investor_data.iloc[0]['Total Investment']) if not investor_data.empty else 0
            count = int(investor_data.iloc[0]['Number of Investments']) if not investor_data.empty else 0
            
            with [col1, col2, col3][idx]:
                st.markdown(f"""<div class="investor-card">
                    <div style="font-size: 2rem;">👤</div>
                    <p class="metric-value">₹{total:,.0f}</p>
                    <p class="metric-label">{investor.upper()}</p>
                    <p style="color: white; margin-top: 0.5rem; font-size: 0.9rem;">{count} investments</p>
                </div>""", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 🗑️ Delete Investment")
        col1, col2 = st.columns([2, 2])
        with col1:
            delete_id = st.number_input("Investment ID to Delete", min_value=1, step=1, key="del_inv")
        with col2:
            st.write("")
            st.write("")
            if st.button("🗑️ Delete Investment", type="secondary", use_container_width=True):
                if delete_row('investments', int(delete_id)):
                    st.success(f"✅ Investment ID {delete_id} deleted!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ Investment ID {delete_id} not found!")
        
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Investment", f"₹{investments_df['amount'].sum():,.0f}")
        col2.metric("Total Entries", len(investments_df))
        col3.metric("Average Investment", f"₹{investments_df['amount'].mean():,.0f}")
    else:
        st.info("No investments recorded yet")

def analytics_page():
    if not sheets:
        st.error("⚠️ Google Sheets not connected.")
        return
    
    st.markdown("# 📊 Financial Analytics")
    
    payments_df = get_payments_df()
    expenses_df = get_expenses_df()
    investments_df = get_investments_df()
    
    st.markdown("### 📈 Income vs Expense Trend")
    
    if not payments_df.empty or not expenses_df.empty:
        income_by_date = payments_df.groupby('date')['amount'].sum().reset_index() if not payments_df.empty else pd.DataFrame(columns=['date', 'amount'])
        income_by_date.columns = ['date', 'income'] if not income_by_date.empty else ['date', 'income']
        
        expense_by_date = expenses_df.groupby('date')['amount'].sum().reset_index() if not expenses_df.empty else pd.DataFrame(columns=['date', 'amount'])
        expense_by_date.columns = ['date', 'expense'] if not expense_by_date.empty else ['date', 'expense']
        
        df = pd.merge(income_by_date, expense_by_date, on="date", how="outer").fillna(0)
        df['profit'] = df['income'] - df['expense']
        
        st.line_chart(df.set_index("date")[['income', 'expense', 'profit']])
        
        col1, col2, col3, col4 = st.columns(4)
        total_income = float(df['income'].sum())
        total_expense = float(df['expense'].sum())
        total_investment = float(investments_df['amount'].sum()) if not investments_df.empty else 0
        
        col1.metric("Total Income", f"₹{total_income:,.0f}")
        col2.metric("Total Expense", f"₹{total_expense:,.0f}")
        col3.metric("Total Investment", f"₹{total_investment:,.0f}")
        col4.metric("Net Profit", f"₹{(total_income - total_expense):,.0f}")
    else:
        st.info("Not enough data for analysis yet")
    
    st.markdown("---")
    st.markdown("### 📊 Expense Breakdown by Category")
    
    if not expenses_df.empty:
        category_total = expenses_df.groupby('category')['amount'].sum().reset_index()
        category_total.columns = ['category', 'total']
        st.bar_chart(category_total.set_index('category'))
    else:
        st.info("No expense data available")
    
    if not investments_df.empty:
        st.markdown("---")
        st.markdown("### 💼 Investment Distribution by Partner")
        investor_total = investments_df.groupby('investor')['amount'].sum().reset_index()
        investor_total.columns = ['investor', 'total']
        st.bar_chart(investor_total.set_index('investor'))

# ================= MAIN APP =================

def main():
    if not st.session_state.logged_in:
        login_page()
    else:
        col1, col2, col3 = st.columns([2, 3, 1])
        
        with col1:
            st.markdown(f"### 👋 Welcome, **{st.session_state.user}**")
        
        with col3:
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.user = None
                clear_cache()
                st.rerun()
        
        st.markdown("---")
        
        tabs = st.tabs(["🏠 Overview", "🎓 Students", "💰 Payments", "📉 Expenses", "💼 Investments", "📊 Analytics"])
        
        with tabs[0]:
            overview_page()
        with tabs[1]:
            students_page()
        with tabs[2]:
            payments_page()
        with tabs[3]:
            expenses_page()
        with tabs[4]:
            investments_page()
        with tabs[5]:
            analytics_page()

if __name__ == "__main__":
    main()
