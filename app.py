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
import plotly.express as px
import plotly.graph_objects as go

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="LogicRoot ERP",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🎓"
)

# ================= CSS =================
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

  /* ---- Base ---- */
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* Light mode tokens */
  :root {
    --bg:        #F8FAFC;
    --surface:   #FFFFFF;
    --border:    #E2E8F0;
    --text:      #1E293B;
    --text-muted:#64748B;
    --primary:   #4F46E5;
    --primary-l: #EEF2FF;
    --success:   #10B981;
    --success-l: #D1FAE5;
    --warning:   #F59E0B;
    --warning-l: #FEF3C7;
    --danger:    #EF4444;
    --danger-l:  #FEE2E2;
    --purple:    #7C3AED;
    --purple-l:  #EDE9FE;
    --shadow:    0 1px 3px rgba(0,0,0,.06), 0 4px 16px rgba(0,0,0,.06);
    --shadow-md: 0 4px 6px rgba(0,0,0,.07), 0 10px 30px rgba(0,0,0,.08);
    --radius:    16px;
    --radius-sm: 10px;
  }

  /* Dark mode tokens */
  [data-theme="dark"] {
    --bg:        #0F172A;
    --surface:   #1E293B;
    --border:    #334155;
    --text:      #F1F5F9;
    --text-muted:#94A3B8;
    --primary-l: #1E1B4B;
    --success-l: #064E3B;
    --warning-l: #78350F;
    --danger-l:  #7F1D1D;
    --purple-l:  #2E1065;
    --shadow:    0 1px 3px rgba(0,0,0,.3), 0 4px 16px rgba(0,0,0,.3);
    --shadow-md: 0 4px 6px rgba(0,0,0,.4), 0 10px 30px rgba(0,0,0,.4);
  }

  /* Apply background */
  .stApp { background: var(--bg) !important; color: var(--text); }

  /* ---- Sidebar ---- */
  section[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
    padding: 0 !important;
  }
  section[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }
  [data-testid="stSidebarNav"] { display: none; }

  /* ---- Remove default streamlit chrome ---- */
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding: 2rem 2rem 4rem 2rem; max-width: 1400px; }

  /* ---- KPI Cards ---- */
  .kpi-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.5rem;
    box-shadow: var(--shadow);
    transition: box-shadow .2s, transform .2s;
    position: relative;
    overflow: hidden;
  }
  .kpi-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
  .kpi-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0;
    height: 3px;
  }
  .kpi-card.blue::before  { background: var(--primary); }
  .kpi-card.green::before { background: var(--success); }
  .kpi-card.amber::before { background: var(--warning); }
  .kpi-card.red::before   { background: var(--danger); }
  .kpi-card.purple::before{ background: var(--purple); }

  .kpi-icon {
    width: 44px; height: 44px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.25rem; margin-bottom: 1rem;
  }
  .kpi-icon.blue   { background: var(--primary-l); }
  .kpi-icon.green  { background: var(--success-l); }
  .kpi-icon.amber  { background: var(--warning-l); }
  .kpi-icon.red    { background: var(--danger-l); }
  .kpi-icon.purple { background: var(--purple-l); }

  .kpi-value {
    font-size: 1.75rem; font-weight: 800;
    color: var(--text); line-height: 1.1; margin: 0;
  }
  .kpi-label {
    font-size: 0.8rem; font-weight: 500;
    color: var(--text-muted); text-transform: uppercase;
    letter-spacing: .05em; margin-top: .35rem;
  }
  .kpi-change {
    font-size: 0.78rem; font-weight: 600;
    margin-top: .5rem; display: inline-block;
    padding: .15rem .5rem; border-radius: 20px;
  }
  .kpi-change.up   { color: var(--success); background: var(--success-l); }
  .kpi-change.down { color: var(--danger);  background: var(--danger-l);  }

  /* ---- Partner Cards ---- */
  .partner-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.25rem 1.5rem;
    box-shadow: var(--shadow);
    display: flex; align-items: center; gap: 1rem;
  }
  .partner-avatar {
    width: 48px; height: 48px; border-radius: 50%;
    background: var(--primary-l);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.3rem; font-weight: 700; color: var(--primary);
    flex-shrink: 0;
  }
  .partner-name  { font-size: 1rem; font-weight: 600; color: var(--text); }
  .partner-amt   { font-size: 1.4rem; font-weight: 800; color: var(--primary); }
  .partner-label { font-size: 0.75rem; color: var(--text-muted); }

  /* ---- Badges ---- */
  .badge {
    display: inline-block;
    padding: .2rem .65rem;
    border-radius: 20px;
    font-size: 0.75rem; font-weight: 600;
    line-height: 1.6;
  }
  .badge-green  { background: var(--success-l); color: var(--success); }
  .badge-amber  { background: var(--warning-l); color: #B45309; }
  .badge-red    { background: var(--danger-l);  color: var(--danger); }
  .badge-blue   { background: var(--primary-l); color: var(--primary); }
  .badge-purple { background: var(--purple-l);  color: var(--purple); }
  .badge-gray   { background: var(--border);    color: var(--text-muted); }

  /* ---- Section title ---- */
  .section-title {
    font-size: 1.15rem; font-weight: 700;
    color: var(--text); margin-bottom: 1rem;
    display: flex; align-items: center; gap: .5rem;
  }

  /* ---- Page header ---- */
  .page-header {
    margin-bottom: 2rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
  }
  .page-title {
    font-size: 1.9rem; font-weight: 800;
    color: var(--text); margin: 0; line-height: 1.2;
  }
  .page-subtitle { font-size: 0.9rem; color: var(--text-muted); margin-top: .3rem; }

  /* ---- Card container ---- */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.5rem;
    box-shadow: var(--shadow);
    margin-bottom: 1.25rem;
  }

  /* ---- Sidebar logo / nav ---- */
  .sidebar-logo {
    padding: 1.5rem 1.5rem 1rem;
    border-bottom: 1px solid var(--border);
  }
  .sidebar-logo-text {
    font-size: 1.25rem; font-weight: 800;
    color: var(--primary); letter-spacing: -.02em;
  }
  .sidebar-logo-sub { font-size: 0.72rem; color: var(--text-muted); letter-spacing: .06em; text-transform: uppercase; }

  .sidebar-user {
    padding: .75rem 1.5rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: .5rem;
  }
  .sidebar-user-name { font-size: .85rem; font-weight: 600; color: var(--text); }
  .sidebar-user-role { font-size: .73rem; color: var(--text-muted); }

  .sidebar-nav-item {
    display: flex; align-items: center; gap: .75rem;
    padding: .6rem 1.25rem;
    border-radius: var(--radius-sm);
    margin: .15rem .75rem;
    cursor: pointer; transition: background .15s;
    font-size: .875rem; font-weight: 500; color: var(--text-muted);
    text-decoration: none;
  }
  .sidebar-nav-item:hover   { background: var(--primary-l); color: var(--primary); }
  .sidebar-nav-item.active  { background: var(--primary-l); color: var(--primary); font-weight: 600; }
  .sidebar-nav-icon { font-size: 1.05rem; width: 20px; text-align: center; }

  /* ---- Stacked metrics ---- */
  .mini-stat {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: .75rem 1rem;
    text-align: center;
  }
  .mini-stat-val  { font-size: 1.3rem; font-weight: 700; color: var(--text); }
  .mini-stat-lbl  { font-size: .72rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: .05em; }

  /* ---- Button overrides ---- */
  .stButton > button {
    background: var(--primary) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important; font-size: .875rem !important;
    padding: .55rem 1.25rem !important;
    transition: opacity .15s, transform .15s !important;
    box-shadow: 0 1px 3px rgba(79,70,229,.3) !important;
  }
  .stButton > button:hover { opacity: .88 !important; transform: translateY(-1px) !important; }
  .stButton > button[kind="secondary"] {
    background: transparent !important;
    color: var(--danger) !important;
    border: 1.5px solid var(--danger) !important;
    box-shadow: none !important;
  }
  .stButton > button[kind="secondary"]:hover { background: var(--danger-l) !important; opacity: 1 !important; }

  /* ---- Form inputs ---- */
  .stTextInput > div > div > input,
  .stNumberInput > div > div > input,
  .stTextArea > div > div > textarea,
  .stSelectbox > div > div {
    border-radius: var(--radius-sm) !important;
    border: 1.5px solid var(--border) !important;
    background: var(--surface) !important;
    color: var(--text) !important;
    font-size: .875rem !important;
    transition: border-color .2s !important;
  }
  .stTextInput > div > div > input:focus,
  .stNumberInput > div > div > input:focus,
  .stTextArea > div > div > textarea:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(79,70,229,.12) !important;
  }
  label { color: var(--text) !important; font-size: .825rem !important; font-weight: 500 !important; }

  /* ---- WhatsApp button ---- */
  .wa-btn {
    display: inline-flex; align-items: center; gap: .5rem;
    background: #22C55E; color: white;
    padding: .55rem 1.25rem; border-radius: var(--radius-sm);
    text-decoration: none; font-weight: 600; font-size: .875rem;
    transition: opacity .15s, transform .15s;
  }
  .wa-btn:hover { opacity: .85; transform: translateY(-1px); color: white; }

  /* ---- Login ---- */
  .login-wrap {
    max-width: 420px; margin: 5rem auto;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 24px;
    box-shadow: var(--shadow-md);
    padding: 2.5rem;
  }
  .login-logo { text-align: center; margin-bottom: 2rem; }
  .login-title { font-size: 1.75rem; font-weight: 800; color: var(--primary); margin: 0; }
  .login-sub   { font-size: .85rem; color: var(--text-muted); margin-top: .25rem; }

  /* ---- Dataframe tweaks ---- */
  .stDataFrame, [data-testid="stDataFrame"] {
    border-radius: var(--radius-sm) !important;
    border: 1px solid var(--border) !important;
    overflow: hidden;
  }

  /* ---- Divider ---- */
  .divider { border: none; border-top: 1px solid var(--border); margin: 1.5rem 0; }

  /* ---- Tab nav for sub-pages ---- */
  .stTabs [data-baseweb="tab-list"] { gap: .25rem; border-bottom: 2px solid var(--border); }
  .stTabs [data-baseweb="tab"] {
    background: transparent; border: none;
    padding: .5rem 1rem; border-radius: 8px 8px 0 0;
    font-weight: 500; color: var(--text-muted);
  }
  .stTabs [aria-selected="true"] { background: transparent; color: var(--primary); border-bottom: 2px solid var(--primary) !important; }

  /* ---- Mobile ---- */
  @media (max-width: 768px) {
    .block-container { padding: .75rem .75rem 3rem .75rem; }
    .kpi-value { font-size: 1.4rem; }
    .page-title { font-size: 1.4rem; }
    .partner-amt { font-size: 1.15rem; }
  }

  /* ---- Animations ---- */
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  .kpi-card, .card, .partner-card { animation: fadeUp .3s ease both; }

  /* expander */
  details[data-testid="stExpander"] > summary {
    border-radius: var(--radius-sm) !important;
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    padding: .85rem 1rem !important;
    font-weight: 600 !important;
    color: var(--text) !important;
  }
  details[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    overflow: hidden;
    box-shadow: var(--shadow);
  }
</style>
""", unsafe_allow_html=True)

# ---- Dark mode JS injection ----
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

if st.session_state.dark_mode:
    st.markdown("<script>document.documentElement.setAttribute('data-theme','dark')</script>", unsafe_allow_html=True)
    st.markdown("""<style>
    .stApp { background: #0F172A !important; }
    section[data-testid="stSidebar"] { background: #1E293B !important; }
    .card, .kpi-card, .partner-card { background: #1E293B !important; border-color: #334155 !important; }
    .kpi-value, .partner-name, .page-title, label, p { color: #F1F5F9 !important; }
    .kpi-label, .partner-label, .page-subtitle, .sidebar-user-role, .sidebar-nav-item { color: #94A3B8 !important; }
    .stTextInput > div > div > input, .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea, .stSelectbox > div > div {
      background: #0F172A !important; color: #F1F5F9 !important; border-color: #334155 !important;
    }
    .mini-stat { background: #0F172A !important; border-color: #334155 !important; }
    .stDataFrame { background: #1E293B !important; }
    </style>""", unsafe_allow_html=True)

# ================= CACHE SETUP =================
if 'cache_timestamp' not in st.session_state:
    st.session_state.cache_timestamp = {}
    st.session_state.cached_data = {}

CACHE_DURATION = 30

def is_cache_valid(key):
    if key not in st.session_state.cache_timestamp:
        return False
    return (time.time() - st.session_state.cache_timestamp[key]) < CACHE_DURATION

def get_cached_data(key):
    return st.session_state.cached_data[key] if is_cache_valid(key) else None

def set_cached_data(key, data):
    st.session_state.cached_data[key] = data
    st.session_state.cache_timestamp[key] = time.time()

def clear_cache():
    st.session_state.cache_timestamp = {}
    st.session_state.cached_data = {}

# ================= GOOGLE SHEETS =================
@st.cache_resource(ttl=3600)
def init_google_sheets():
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
        sheet_names = ['students', 'payments', 'expenses', 'investments']
        headers = {
            'students':    ['id', 'name', 'phone', 'course', 'fee', 'paid', 'status', 'date'],
            'payments':    ['id', 'student_id', 'amount', 'mode', 'date'],
            'expenses':    ['id', 'title', 'amount', 'category', 'date'],
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
        st.error(f"Google Sheets connection error: {e}")
        return None

sheets = init_google_sheets()

# ================= DATA OPERATIONS =================
def get_all_data(sheet_name):
    cached = get_cached_data(f"data_{sheet_name}")
    if cached is not None:
        return cached
    try:
        data = sheets[sheet_name].get_all_records()
        set_cached_data(f"data_{sheet_name}", data)
        return data
    except Exception as e:
        st.error(f"Error fetching {sheet_name}: {e}")
        return []

def _to_df(data, cols, numeric_cols):
    if not data:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(data)
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    return df

def get_students_df():
    return _to_df(get_all_data('students'),
                  ['id','name','phone','course','fee','paid','status','date'],
                  ['id','fee','paid'])

def get_payments_df():
    return _to_df(get_all_data('payments'),
                  ['id','student_id','amount','mode','date'],
                  ['id','student_id','amount'])

def get_expenses_df():
    return _to_df(get_all_data('expenses'),
                  ['id','title','amount','category','date'],
                  ['id','amount'])

def get_investments_df():
    return _to_df(get_all_data('investments'),
                  ['id','investor','amount','date','notes'],
                  ['id','amount'])

def get_next_id(sheet_name):
    data = get_all_data(sheet_name)
    if not data:
        return 1
    return max(int(r['id']) for r in data if r.get('id')) + 1

def get_student_by_id(student_id):
    df = get_students_df()
    if df.empty:
        return None
    row = df[df['id'] == student_id]
    return row.iloc[0].to_dict() if not row.empty else None

def add_student(name, phone, course, fee):
    try:
        sid = get_next_id('students')
        sheets['students'].append_row([sid, name, phone, course, fee, 0, 'active',
                                        datetime.now().strftime("%Y-%m-%d")])
        clear_cache()
        return sid
    except Exception as e:
        st.error(f"Error adding student: {e}"); return None

def add_payment(student_id, amount, mode):
    try:
        pid = get_next_id('payments')
        sheets['payments'].append_row([pid, student_id, amount, mode,
                                        datetime.now().strftime("%Y-%m-%d")])
        all_records = sheets['students'].get_all_records()
        for idx, record in enumerate(all_records, start=2):
            if int(record['id']) == student_id:
                new_paid = float(record.get('paid', 0)) + amount
                sheets['students'].update_cell(idx, 6, new_paid)
                break
        clear_cache()
        return pid
    except Exception as e:
        st.error(f"Error adding payment: {e}"); return None

def add_expense(title, amount, category):
    try:
        eid = get_next_id('expenses')
        sheets['expenses'].append_row([eid, title, amount, category,
                                        datetime.now().strftime("%Y-%m-%d")])
        clear_cache()
        return eid
    except Exception as e:
        st.error(f"Error adding expense: {e}"); return None

def add_investment(investor, amount, notes=""):
    try:
        iid = get_next_id('investments')
        sheets['investments'].append_row([iid, investor, amount,
                                           datetime.now().strftime("%Y-%m-%d"), notes])
        clear_cache()
        return iid
    except Exception as e:
        st.error(f"Error adding investment: {e}"); return None

def delete_row(sheet_name, row_id):
    try:
        all_records = sheets[sheet_name].get_all_records()
        for idx, record in enumerate(all_records, start=2):
            if int(record['id']) == row_id:
                sheets[sheet_name].delete_rows(idx)
                clear_cache()
                return True
        return False
    except Exception as e:
        st.error(f"Error deleting: {e}"); return False

# ================= CONFIG =================
USERS     = {"Arghya": "Arghya@9382", "Tapan": "Tapan@6296", "Suman": "Suman@8348"}
UPI_ID    = "yourupi@bank"
INVESTORS = ["Arghya", "Tapan", "Suman"]

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

# ================= HELPERS =================
def generate_receipt(student_id, amount, mode):
    student = get_student_by_id(student_id)
    if not student:
        return None
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    elems = []
    elems.append(Paragraph("<b>COACHING FEE RECEIPT</b>", styles["Title"]))
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
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#4F46E5')),
        ('TEXTCOLOR',  (0, 0), (0, -1), colors.whitesmoke),
        ('ALIGN',      (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME',   (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE',   (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING',    (0, 0), (-1, -1), 12),
        ('GRID',       (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
        ('BOX',        (0, 0), (-1, -1), 2, colors.HexColor('#4F46E5')),
    ]))
    elems.append(table)
    elems.append(Spacer(1, 40))
    elems.append(Paragraph("<i>Thank you for your payment — LogicRoot Coaching</i>", styles["Normal"]))
    doc.build(elems)
    buf.seek(0)
    return buf

def upi_qr(amount):
    link = f"upi://pay?pa={UPI_ID}&pn=LogicRootCoaching&am={amount}&cu=INR"
    img  = qrcode.make(link).resize((280, 280))
    b    = BytesIO()
    img.save(b, format="PNG")
    b.seek(0)
    return b

def whatsapp_link(phone, msg):
    clean = str(phone).replace("+", "").replace("-", "").replace(" ", "")
    if not clean.startswith("91"):
        clean = "91" + clean
    return f"https://wa.me/{clean}?text={urllib.parse.quote(msg)}"

def kpi_card(label, value, icon, color="blue", change=None, change_dir="up"):
    change_html = ""
    if change:
        arrow = "↑" if change_dir == "up" else "↓"
        change_html = f'<div class="kpi-change {change_dir}">{arrow} {change}</div>'
    return f"""<div class="kpi-card {color}">
        <div class="kpi-icon {color}">{icon}</div>
        <p class="kpi-value">{value}</p>
        <p class="kpi-label">{label}</p>
        {change_html}
    </div>"""

def partner_card(name, amount, count):
    initials = name[0].upper()
    return f"""<div class="partner-card">
        <div class="partner-avatar">{initials}</div>
        <div>
            <div class="partner-name">{name}</div>
            <div class="partner-amt">₹{amount:,.0f}</div>
            <div class="partner-label">{count} investment{'s' if count != 1 else ''}</div>
        </div>
    </div>"""

def plotly_defaults(fig):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter', size=12, color='#64748B'),
        margin=dict(l=0, r=0, t=32, b=0),
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        hovermode='x unified',
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor='#F1F5F9', zeroline=False)
    return fig

PALETTE = ['#4F46E5', '#10B981', '#F59E0B', '#EF4444', '#7C3AED', '#06B6D4']

# ================= LOGIN PAGE =================
def login_page():
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    st.markdown("""<div class="login-logo">
        <p class="login-title">LogicRoot</p>
        <p class="login-sub">Coaching Management System</p>
    </div>""", unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Sign in", use_container_width=True)
        if submitted:
            if username in USERS and USERS[username] == password:
                st.session_state.logged_in = True
                st.session_state.user = username
                st.rerun()
            else:
                st.error("Incorrect username or password.")
    st.markdown('</div>', unsafe_allow_html=True)

# ================= SIDEBAR =================
def sidebar():
    with st.sidebar:
        # Logo
        st.markdown("""<div class="sidebar-logo">
            <div class="sidebar-logo-text">🎓 LogicRoot</div>
            <div class="sidebar-logo-sub">ERP Dashboard</div>
        </div>""", unsafe_allow_html=True)

        # User
        st.markdown(f"""<div class="sidebar-user">
            <div class="sidebar-user-name">👤 {st.session_state.user}</div>
            <div class="sidebar-user-role">Administrator</div>
        </div>""", unsafe_allow_html=True)

        nav_items = [
            ("🏠", "Dashboard"),
            ("👨‍🎓", "Students"),
            ("💰", "Payments"),
            ("📉", "Expenses"),
            ("💼", "Investments"),
            ("📊", "Analytics"),
        ]

        for icon, label in nav_items:
            active = "active" if st.session_state.page == label else ""
            if st.button(f"{icon}  {label}", key=f"nav_{label}",
                         use_container_width=True,
                         help=label):
                st.session_state.page = label
                st.rerun()

        st.markdown("<hr class='divider'>", unsafe_allow_html=True)

        # Dark mode
        col_dm, _ = st.columns([1, 2])
        with col_dm:
            dm_label = "☀️" if st.session_state.dark_mode else "🌙"
            if st.button(dm_label, key="darkmode_toggle", help="Toggle dark mode"):
                st.session_state.dark_mode = not st.session_state.dark_mode
                st.rerun()

        # Refresh
        if st.button("🔄  Refresh", key="sidebar_refresh", use_container_width=True):
            clear_cache()
            st.rerun()

        st.markdown("<br><br>", unsafe_allow_html=True)

        # Logout at bottom
        if st.button("🚪  Sign out", key="sidebar_logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user = None
            clear_cache()
            st.rerun()

# ================= DASHBOARD =================
def page_dashboard():
    if not sheets:
        st.error("⚠️ Google Sheets not connected.")
        return

    st.markdown("""<div class="page-header">
        <h1 class="page-title">Dashboard</h1>
        <p class="page-subtitle">Financial overview — """ + datetime.now().strftime("%B %Y") + """</p>
    </div>""", unsafe_allow_html=True)

    sdf = get_students_df()
    pdf = get_payments_df()
    edf = get_expenses_df()
    idf = get_investments_df()

    total_students  = len(sdf[sdf['status'] == 'active']) if not sdf.empty else 0
    total_income    = float(pdf['amount'].sum())    if not pdf.empty else 0
    total_expense   = float(edf['amount'].sum())    if not edf.empty else 0
    total_invest    = float(idf['amount'].sum())    if not idf.empty else 0
    net_profit      = total_income - total_expense
    profit_color    = "green" if net_profit >= 0 else "red"

    # KPI row
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(kpi_card("Active Students", total_students, "👥", "blue"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card("Total Income", f"₹{total_income:,.0f}", "💰", "green"), unsafe_allow_html=True)
    with c3:
        st.markdown(kpi_card("Total Expenses", f"₹{total_expense:,.0f}", "📉", "amber"), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("Net Profit", f"₹{net_profit:,.0f}", "📈", profit_color), unsafe_allow_html=True)
    with c5:
        st.markdown(kpi_card("Total Investment", f"₹{total_invest:,.0f}", "💼", "purple"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Partner overview + recent payments
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown('<p class="section-title">💼 Partner Contributions</p>', unsafe_allow_html=True)
        if not idf.empty:
            inv_totals = idf.groupby('investor')['amount'].agg(['sum', 'count'])
            for investor in INVESTORS:
                amt   = float(inv_totals.loc[investor, 'sum'])   if investor in inv_totals.index else 0
                cnt   = int(inv_totals.loc[investor, 'count'])   if investor in inv_totals.index else 0
                st.markdown(partner_card(investor, amt, cnt), unsafe_allow_html=True)
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        else:
            st.info("No investment records yet.")

    with col_right:
        st.markdown('<p class="section-title">🕐 Recent Payments</p>', unsafe_allow_html=True)
        if not pdf.empty and not sdf.empty:
            recent = pdf.sort_values('date', ascending=False).head(8).copy()
            recent['Student'] = recent['student_id'].apply(
                lambda x: get_student_by_id(int(x))['name'] if get_student_by_id(int(x)) else '—'
            )
            recent = recent[['date', 'Student', 'amount', 'mode']].rename(
                columns={'date': 'Date', 'amount': 'Amount (₹)', 'mode': 'Mode'})
            st.dataframe(recent, use_container_width=True, hide_index=True)
        else:
            st.info("No payments recorded yet.")

    st.markdown("<br>", unsafe_allow_html=True)

    # Quick income vs expense chart
    if not pdf.empty or not edf.empty:
        st.markdown('<p class="section-title">📈 Income vs Expenses</p>', unsafe_allow_html=True)
        inc = pdf.groupby('date')['amount'].sum().reset_index().rename(columns={'amount': 'Income'}) if not pdf.empty else pd.DataFrame(columns=['date', 'Income'])
        exp = edf.groupby('date')['amount'].sum().reset_index().rename(columns={'amount': 'Expenses'}) if not edf.empty else pd.DataFrame(columns=['date', 'Expenses'])
        trend = pd.merge(inc, exp, on='date', how='outer').fillna(0)
        trend['Profit'] = trend['Income'] - trend['Expenses']
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trend['date'], y=trend['Income'],   name='Income',   line=dict(color=PALETTE[1], width=2.5), fill='tozeroy', fillcolor='rgba(16,185,129,.08)'))
        fig.add_trace(go.Scatter(x=trend['date'], y=trend['Expenses'], name='Expenses', line=dict(color=PALETTE[2], width=2.5)))
        fig.add_trace(go.Scatter(x=trend['date'], y=trend['Profit'],   name='Profit',   line=dict(color=PALETTE[0], width=2, dash='dot')))
        st.plotly_chart(plotly_defaults(fig), use_container_width=True)

# ================= STUDENTS PAGE =================
def page_students():
    if not sheets:
        st.error("⚠️ Google Sheets not connected.")
        return

    st.markdown("""<div class="page-header">
        <h1 class="page-title">Students</h1>
        <p class="page-subtitle">Manage enrolled students and fee tracking</p>
    </div>""", unsafe_allow_html=True)

    sdf = get_students_df()

    # Stats bar
    if not sdf.empty:
        total_fee     = float(sdf['fee'].sum())
        total_paid    = float(sdf['paid'].sum())
        total_pending = total_fee - total_paid
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(kpi_card("Total Students", len(sdf), "👥", "blue"), unsafe_allow_html=True)
        with c2: st.markdown(kpi_card("Active",  len(sdf[sdf['status'] == 'active']),  "✅", "green"),  unsafe_allow_html=True)
        with c3: st.markdown(kpi_card("Total Fees Billed", f"₹{total_fee:,.0f}",    "🧾", "amber"),  unsafe_allow_html=True)
        with c4: st.markdown(kpi_card("Pending Collection", f"₹{total_pending:,.0f}", "⏳", "red"),   unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # Add student form
    with st.expander("➕  Enroll New Student", expanded=False):
        with st.form("add_student_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                name   = st.text_input("Full Name *",   placeholder="e.g. Priya Sharma")
                phone  = st.text_input("Phone Number *", placeholder="10-digit mobile")
            with c2:
                course = st.text_input("Course *",      placeholder="e.g. JEE Mains, NEET")
                fee    = st.number_input("Total Fee (₹) *", min_value=0.0, step=500.0)
            submitted = st.form_submit_button("Enroll Student", use_container_width=True)
            if submitted:
                if name and phone and course and fee > 0:
                    sid = add_student(name, phone, course, fee)
                    if sid:
                        st.success(f"Student '{name}' enrolled. ID: {sid}")
                        time.sleep(0.8); st.rerun()
                else:
                    st.error("Please complete all required fields.")

    st.markdown('<p class="section-title">📋 Student Roster</p>', unsafe_allow_html=True)

    if not sdf.empty:
        search = st.text_input("🔍  Search", placeholder="Search by name or phone", key="student_search", label_visibility="collapsed")
        disp = sdf.copy()
        disp['Pending'] = disp['fee'] - disp['paid']
        disp = disp[['id', 'name', 'phone', 'course', 'fee', 'paid', 'Pending', 'status', 'date']]
        disp.columns = ['ID', 'Name', 'Phone', 'Course', 'Total Fee', 'Paid', 'Pending', 'Status', 'Enrolled']
        if search:
            mask = (disp['Name'].astype(str).str.contains(search, case=False, na=False) |
                    disp['Phone'].astype(str).str.contains(search, case=False, na=False))
            disp = disp[mask]
        st.dataframe(disp, use_container_width=True, hide_index=True)

        with st.expander("🗑️  Delete Student", expanded=False):
            c1, c2 = st.columns([2, 1])
            with c1:
                del_id = st.number_input("Student ID to remove", min_value=1, step=1, key="del_student")
            with c2:
                st.write("")
                if st.button("Delete", key="do_del_student", type="secondary", use_container_width=True):
                    if delete_row('students', int(del_id)):
                        st.success(f"Student {del_id} removed."); time.sleep(0.8); st.rerun()
                    else:
                        st.error(f"ID {del_id} not found.")
    else:
        st.info("No students enrolled yet. Use the form above to add the first student.")

# ================= PAYMENTS PAGE =================
def page_payments():
    if not sheets:
        st.error("⚠️ Google Sheets not connected.")
        return

    st.markdown("""<div class="page-header">
        <h1 class="page-title">Payments</h1>
        <p class="page-subtitle">Record and track fee collections</p>
    </div>""", unsafe_allow_html=True)

    sdf = get_students_df()
    active = sdf[sdf['status'] == 'active'] if not sdf.empty else pd.DataFrame()

    if active.empty:
        st.warning("No active students found. Enroll students before recording payments.")
        return

    col_form, col_recent = st.columns([1, 1])

    with col_form:
        st.markdown('<p class="section-title">💳 Record Payment</p>', unsafe_allow_html=True)
        with st.form("payment_form"):
            student_options = {}
            for _, s in active.iterrows():
                pending = s['fee'] - s['paid']
                label   = f"{int(s['id'])} · {s['name']}  (₹{pending:.0f} due)"
                student_options[label] = int(s['id'])

            selected = st.selectbox("Select Student *", list(student_options.keys()))
            sid      = student_options.get(selected)
            amount   = st.number_input("Amount (₹) *", min_value=0.0, step=100.0)
            mode     = st.selectbox("Payment Mode *", ["Cash", "UPI", "Online Transfer", "Cheque"])
            submit   = st.form_submit_button("Record Payment", use_container_width=True)

            if mode == "UPI" and amount > 0:
                st.markdown("---")
                st.markdown("**Scan to Pay**")
                c1, _, c3 = st.columns([1, 0.2, 1])
                with c1:
                    st.image(upi_qr(amount), width=220, caption=f"₹{amount:.2f}")

            if submit and sid and amount > 0:
                pid = add_payment(sid, amount, mode.lower())
                if pid:
                    st.success(f"₹{amount:.2f} recorded via {mode}.")
                    receipt = generate_receipt(sid, amount, mode)
                    if receipt:
                        st.download_button("📄 Download Receipt", receipt,
                                           f"receipt_{sid}_{datetime.now().strftime('%Y%m%d')}.pdf",
                                           "application/pdf")
                    student = get_student_by_id(sid)
                    if student:
                        msg     = f"Dear {student['name']}, your payment of ₹{amount:.2f} to LogicRoot has been received. Thank you!"
                        wa_link = whatsapp_link(student['phone'], msg)
                        st.markdown(f'<a href="{wa_link}" target="_blank" class="wa-btn">📱 Send WhatsApp Receipt</a>', unsafe_allow_html=True)
                    time.sleep(0.8); st.rerun()

    with col_recent:
        st.markdown('<p class="section-title">🕐 Payment History</p>', unsafe_allow_html=True)
        pdf = get_payments_df()
        if not pdf.empty:
            recent = pdf.sort_values('date', ascending=False).head(20).copy()
            recent['Student'] = recent['student_id'].apply(
                lambda x: get_student_by_id(int(x))['name'] if get_student_by_id(int(x)) else '—'
            )
            recent = recent[['id', 'date', 'Student', 'amount', 'mode']].rename(
                columns={'id': 'ID', 'date': 'Date', 'amount': '₹', 'mode': 'Mode'})
            st.dataframe(recent, use_container_width=True, hide_index=True)

            with st.expander("🗑️  Delete Payment Record", expanded=False):
                c1, c2 = st.columns([2, 1])
                with c1:
                    del_pid = st.number_input("Payment ID", min_value=1, step=1, key="del_pay")
                with c2:
                    st.write("")
                    if st.button("Delete", key="do_del_pay", type="secondary", use_container_width=True):
                        if delete_row('payments', int(del_pid)):
                            st.success(f"Payment {del_pid} deleted."); time.sleep(0.8); st.rerun()
                        else:
                            st.error(f"ID {del_pid} not found.")
        else:
            st.info("No payments recorded yet.")

# ================= EXPENSES PAGE =================
def page_expenses():
    if not sheets:
        st.error("⚠️ Google Sheets not connected.")
        return

    st.markdown("""<div class="page-header">
        <h1 class="page-title">Expenses</h1>
        <p class="page-subtitle">Track operational costs and overhead</p>
    </div>""", unsafe_allow_html=True)

    edf = get_expenses_df()

    # Summary cards
    total_exp     = float(edf['amount'].sum()) if not edf.empty else 0
    curr_month    = datetime.now().strftime('%Y-%m')
    month_exp     = float(edf[edf['date'].astype(str).str.startswith(curr_month)]['amount'].sum()) if not edf.empty else 0
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(kpi_card("Total Expenses",    f"₹{total_exp:,.0f}",   "📉", "red"),   unsafe_allow_html=True)
    with c2: st.markdown(kpi_card("This Month",        f"₹{month_exp:,.0f}",   "📅", "amber"), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card("Categories",        len(edf['category'].unique()) if not edf.empty else 0, "🏷️", "blue"), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    with st.expander("➕  Add Expense", expanded=False):
        with st.form("expense_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                title    = st.text_input("Expense Title *", placeholder="e.g. Rent, Salary")
                amount   = st.number_input("Amount (₹) *",  min_value=0.0, step=100.0)
            with c2:
                category = st.selectbox("Category *", ["Rent", "Salary", "Utilities",
                                                         "Stationery", "Marketing", "Maintenance", "Other"])
            sub = st.form_submit_button("Add Expense", use_container_width=True)
            if sub and title and amount > 0:
                eid = add_expense(title, amount, category)
                if eid:
                    st.success(f"Expense '{title}' added."); time.sleep(0.8); st.rerun()

    col_table, col_chart = st.columns([1, 1])

    with col_table:
        st.markdown('<p class="section-title">📋 Expense Log</p>', unsafe_allow_html=True)
        if not edf.empty:
            disp = edf[['id', 'date', 'title', 'category', 'amount']].copy()
            disp.columns = ['ID', 'Date', 'Title', 'Category', '₹']
            st.dataframe(disp.sort_values('Date', ascending=False), use_container_width=True, hide_index=True)

            with st.expander("🗑️  Delete Expense", expanded=False):
                c1, c2 = st.columns([2, 1])
                with c1:
                    del_eid = st.number_input("Expense ID", min_value=1, step=1, key="del_exp")
                with c2:
                    st.write("")
                    if st.button("Delete", key="do_del_exp", type="secondary", use_container_width=True):
                        if delete_row('expenses', int(del_eid)):
                            st.success("Expense deleted."); time.sleep(0.8); st.rerun()
                        else:
                            st.error("ID not found.")
        else:
            st.info("No expenses recorded yet.")

    with col_chart:
        if not edf.empty:
            st.markdown('<p class="section-title">📊 Breakdown by Category</p>', unsafe_allow_html=True)
            cat_totals = edf.groupby('category')['amount'].sum().reset_index()
            fig = px.pie(cat_totals, names='category', values='amount',
                         color_discrete_sequence=PALETTE, hole=0.45)
            fig.update_traces(textposition='outside', textinfo='percent+label')
            st.plotly_chart(plotly_defaults(fig), use_container_width=True)

# ================= INVESTMENTS PAGE =================
def page_investments():
    if not sheets:
        st.error("⚠️ Google Sheets not connected.")
        return

    st.markdown("""<div class="page-header">
        <h1 class="page-title">Investments</h1>
        <p class="page-subtitle">Partner contributions and capital overview</p>
    </div>""", unsafe_allow_html=True)

    idf = get_investments_df()
    total_invest = float(idf['amount'].sum()) if not idf.empty else 0

    # KPI cards
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(kpi_card("Total Capital",     f"₹{total_invest:,.0f}", "💼", "purple"), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card("Total Entries",     len(idf) if not idf.empty else 0, "📋", "blue"), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card("Avg per Entry", f"₹{idf['amount'].mean():,.0f}" if not idf.empty else "—", "📐", "green"), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Partner summary
    if not idf.empty:
        inv_summary = idf.groupby('investor')['amount'].agg(['sum', 'count'])
        pc1, pc2, pc3 = st.columns(3)
        for idx, investor in enumerate(INVESTORS):
            amt = float(inv_summary.loc[investor, 'sum'])  if investor in inv_summary.index else 0
            cnt = int(inv_summary.loc[investor, 'count'])  if investor in inv_summary.index else 0
            with [pc1, pc2, pc3][idx]:
                st.markdown(partner_card(investor, amt, cnt), unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    with st.expander("➕  Record Investment", expanded=False):
        with st.form("investment_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                investor = st.selectbox("Partner *", INVESTORS)
                amount   = st.number_input("Amount (₹) *", min_value=0.0, step=1000.0)
            with c2:
                notes = st.text_area("Notes", placeholder="Purpose, bank ref, etc.")
            sub = st.form_submit_button("Add Investment", use_container_width=True)
            if sub and investor and amount > 0:
                iid = add_investment(investor, amount, notes)
                if iid:
                    st.success(f"₹{amount:,.0f} from {investor} recorded."); time.sleep(0.8); st.rerun()

    col_table, col_chart = st.columns([1, 1])
    with col_table:
        st.markdown('<p class="section-title">📋 Investment Log</p>', unsafe_allow_html=True)
        if not idf.empty:
            disp = idf[['id', 'date', 'investor', 'amount', 'notes']].copy()
            disp.columns = ['ID', 'Date', 'Partner', '₹', 'Notes']
            st.dataframe(disp.sort_values('Date', ascending=False), use_container_width=True, hide_index=True)

            with st.expander("🗑️  Delete Investment", expanded=False):
                c1, c2 = st.columns([2, 1])
                with c1:
                    del_iid = st.number_input("Investment ID", min_value=1, step=1, key="del_inv")
                with c2:
                    st.write("")
                    if st.button("Delete", key="do_del_inv", type="secondary", use_container_width=True):
                        if delete_row('investments', int(del_iid)):
                            st.success("Investment deleted."); time.sleep(0.8); st.rerun()
                        else:
                            st.error("ID not found.")
        else:
            st.info("No investments recorded yet.")

    with col_chart:
        if not idf.empty:
            st.markdown('<p class="section-title">📊 Capital by Partner</p>', unsafe_allow_html=True)
            inv_totals = idf.groupby('investor')['amount'].sum().reset_index()
            fig = px.bar(inv_totals, x='investor', y='amount',
                         color='investor', color_discrete_sequence=PALETTE,
                         labels={'investor': 'Partner', 'amount': 'Amount (₹)'})
            fig.update_layout(showlegend=False)
            st.plotly_chart(plotly_defaults(fig), use_container_width=True)

# ================= ANALYTICS PAGE =================
def page_analytics():
    if not sheets:
        st.error("⚠️ Google Sheets not connected.")
        return

    st.markdown("""<div class="page-header">
        <h1 class="page-title">Analytics</h1>
        <p class="page-subtitle">Financial performance at a glance</p>
    </div>""", unsafe_allow_html=True)

    pdf = get_payments_df()
    edf = get_expenses_df()
    idf = get_investments_df()
    sdf = get_students_df()

    total_income  = float(pdf['amount'].sum())  if not pdf.empty else 0
    total_expense = float(edf['amount'].sum())  if not edf.empty else 0
    total_invest  = float(idf['amount'].sum())  if not idf.empty else 0
    net_profit    = total_income - total_expense

    k1, k2, k3, k4 = st.columns(4)
    with k1: st.markdown(kpi_card("Income",     f"₹{total_income:,.0f}",  "💰", "green"),  unsafe_allow_html=True)
    with k2: st.markdown(kpi_card("Expenses",   f"₹{total_expense:,.0f}", "📉", "amber"),  unsafe_allow_html=True)
    with k3: st.markdown(kpi_card("Investment", f"₹{total_invest:,.0f}",  "💼", "purple"), unsafe_allow_html=True)
    with k4: st.markdown(kpi_card("Net Profit", f"₹{net_profit:,.0f}",    "📈", "green" if net_profit >= 0 else "red"), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # Income vs Expenses trend
    if not pdf.empty or not edf.empty:
        st.markdown('<p class="section-title">📈 Income vs Expenses Over Time</p>', unsafe_allow_html=True)
        inc   = pdf.groupby('date')['amount'].sum().reset_index().rename(columns={'amount': 'Income'})   if not pdf.empty else pd.DataFrame(columns=['date', 'Income'])
        exp   = edf.groupby('date')['amount'].sum().reset_index().rename(columns={'amount': 'Expenses'}) if not edf.empty else pd.DataFrame(columns=['date', 'Expenses'])
        trend = pd.merge(inc, exp, on='date', how='outer').fillna(0).sort_values('date')
        trend['Profit'] = trend['Income'] - trend['Expenses']
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=trend['date'], y=trend['Income'],   name='Income',   line=dict(color=PALETTE[1], width=2.5), fill='tozeroy', fillcolor='rgba(16,185,129,.1)'))
        fig.add_trace(go.Scatter(x=trend['date'], y=trend['Expenses'], name='Expenses', line=dict(color=PALETTE[2], width=2.5), fill='tozeroy', fillcolor='rgba(245,158,11,.07)'))
        fig.add_trace(go.Bar(    x=trend['date'], y=trend['Profit'],   name='Profit',   marker_color=[PALETTE[1] if v >= 0 else PALETTE[3] for v in trend['Profit']], opacity=0.6))
        st.plotly_chart(plotly_defaults(fig), use_container_width=True)

    col_l, col_r = st.columns(2)

    # Expense category breakdown
    with col_l:
        if not edf.empty:
            st.markdown('<p class="section-title">🏷️ Expense Categories</p>', unsafe_allow_html=True)
            cat_totals = edf.groupby('category')['amount'].sum().reset_index().sort_values('amount', ascending=True)
            fig = px.bar(cat_totals, x='amount', y='category', orientation='h',
                         color='category', color_discrete_sequence=PALETTE,
                         labels={'amount': 'Amount (₹)', 'category': ''})
            fig.update_layout(showlegend=False)
            st.plotly_chart(plotly_defaults(fig), use_container_width=True)

    # Investment distribution
    with col_r:
        if not idf.empty:
            st.markdown('<p class="section-title">💼 Investment by Partner</p>', unsafe_allow_html=True)
            inv_totals = idf.groupby('investor')['amount'].sum().reset_index()
            fig = px.pie(inv_totals, names='investor', values='amount',
                         color_discrete_sequence=PALETTE, hole=0.5)
            fig.update_traces(textposition='outside', textinfo='percent+label')
            st.plotly_chart(plotly_defaults(fig), use_container_width=True)

    # Fee collection status
    if not sdf.empty:
        st.markdown('<p class="section-title">🎓 Fee Collection Status</p>', unsafe_allow_html=True)
        fee_summary = sdf.copy()
        fee_summary['Pending'] = fee_summary['fee'] - fee_summary['paid']
        bar_df = pd.DataFrame({
            'Status': ['Collected', 'Pending'],
            'Amount': [float(fee_summary['paid'].sum()), float(fee_summary['Pending'].sum())]
        })
        fig = px.bar(bar_df, x='Status', y='Amount', color='Status',
                     color_discrete_map={'Collected': PALETTE[1], 'Pending': PALETTE[3]},
                     labels={'Amount': '₹'})
        fig.update_layout(showlegend=False)
        st.plotly_chart(plotly_defaults(fig), use_container_width=True)

# ================= MAIN =================
def main():
    if not st.session_state.logged_in:
        login_page()
        return

    sidebar()

    page = st.session_state.page
    if   page == "Dashboard":   page_dashboard()
    elif page == "Students":    page_students()
    elif page == "Payments":    page_payments()
    elif page == "Expenses":    page_expenses()
    elif page == "Investments": page_investments()
    elif page == "Analytics":   page_analytics()

if __name__ == "__main__":
    main()
