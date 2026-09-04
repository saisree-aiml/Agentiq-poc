"""
SAGILITY AGENTIQ — Intelligent Agent Routing & Performance Optimization Platform
(formerly "AHT Booster")

This file is an ENHANCEMENT of the original working "AHT Booster" application.

==============================================================================
IMPORTANT — READ BEFORE EDITING
==============================================================================
All sections marked "EXISTING FUNCTIONALITY" contain the original, already
-validated business logic (data validation, numeric coercion, min-max
normalization, weighted scoring formula, eligibility filter, recommendation,
time-saving calculation, Top 5 ranking). This logic is UNCHANGED from the
original AHT Booster app — only the surrounding UI/navigation/branding has
been added around it.

All sections marked "NEW FUNCTIONALITY" are additions for this release:
login / role-based access, Top 10 ranking view, Admin Console (data
management, validation, ranking/availability configuration), premium
enterprise UI, and session-based navigation.

The only behavioral change to the existing formula is *where the weight and
availability-threshold values are read from*: they now come from
st.session_state (defaulting to the exact original constants) instead of
hardcoded module-level constants, so an Admin can optionally override them.
Unless an Admin explicitly saves a new configuration, the numbers used are
identical to the original AHT Booster defaults.
==============================================================================
"""

import io
import pandas as pd
import numpy as np
import streamlit as st

# ==============================================================================
# PAGE CONFIG  (EXISTING FUNCTIONALITY — rebranded only)
# ==============================================================================
st.set_page_config(
    page_title="Sagility AgentIQ",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",  # sidebar (nav + Admin Console) opens by default
)

APP_NAME = "Sagility AgentIQ"
APP_SUBTITLE = "Intelligent Agent Routing & Performance Optimization Platform"

# ------------------------------------------------------------------------------
# EXISTING FUNCTIONALITY — core constants (unchanged values)
# ------------------------------------------------------------------------------
REQUIRED_COLUMNS = ["Agent ID", "Agent Name", "Call Category", "Average AHT (sec)"]
OPTIONAL_NUMERIC_COLUMNS = [
    "Calls Handled", "Target AHT (sec)", "Quality Score (%)",
    "FCR (%)", "Transfer Rate (%)", "Availability (%)", "Experience (Months)",
]

# Original scoring weights & threshold — these are the EXISTING DEFAULTS.
# They are never changed by this file. Admins can optionally override the
# *active* values (stored in session_state) from the Admin Console, but the
# defaults below are always available via "Reset to Existing Default".
DEFAULT_W_AHT = 0.60
DEFAULT_W_QUALITY = 0.15
DEFAULT_W_FCR = 0.15
DEFAULT_W_TRANSFER = 0.10
DEFAULT_AVAILABILITY_THRESHOLD = 80.0

# ==============================================================================
# NEW FUNCTIONALITY — session state initialization
# ==============================================================================
def init_session_state():
    defaults = {
        "authenticated": False,
        "username": None,
        "role": None,                    # "Manager" or "Admin"
        "nav_page": "Dashboard",
        "dataset": None,                 # shared, validated+processed dataframe (source of truth)
        "dataset_source": None,          # filename of the currently active dataset
        "has_run": False,                # existing recommendation "has the button been clicked" flag
        # Ranking configuration — defaults to the EXISTING values.
        "cfg_w_aht": DEFAULT_W_AHT,
        "cfg_w_quality": DEFAULT_W_QUALITY,
        "cfg_w_fcr": DEFAULT_W_FCR,
        "cfg_w_transfer": DEFAULT_W_TRANSFER,
        "cfg_availability_threshold": DEFAULT_AVAILABILITY_THRESHOLD,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session_state()

# ==============================================================================
# NEW FUNCTIONALITY — demo authentication
# ------------------------------------------------------------------------------
# For this POC, credentials are simple in-memory demonstration accounts.
# Structured as a lookup so it can later be swapped for enterprise SSO
# (e.g. SAML/OAuth) without touching the rest of the app — just replace
# authenticate() with a call to the enterprise identity provider.
# ==============================================================================
DEMO_ACCOUNTS = {
    "manager@sagility.com": {"password": "Manager@123", "role": "Manager", "display_name": "Priya Manager"},
    "admin@sagility.com":   {"password": "Admin@123",   "role": "Admin",   "display_name": "Arjun Admin"},
}


def authenticate(username: str, password: str):
    """Returns (role, display_name) on success, or (None, None) on failure."""
    account = DEMO_ACCOUNTS.get(username.strip().lower())
    if account and account["password"] == password:
        return account["role"], account["display_name"]
    return None, None


# ==============================================================================
# GLOBAL STYLE — premium corporate theme (NEW look, applied around existing UI)
# ==============================================================================
st.markdown("""
<style>
    .main .block-container {padding-top: 1.25rem; padding-bottom: 3rem; max-width: 1180px;}
    #MainMenu, footer, header {visibility: hidden;}

    /* ---------- Brand header ---------- */
    .app-header {
        background: linear-gradient(120deg, #0b1729 0%, #14263f 45%, #1c3a5e 100%);
        padding: 1.9rem 2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 1.5rem;
        border-bottom: 3px solid #c9a24b;
        position: relative;
    }
    .app-header h1 {
        margin: 0; font-size: 1.9rem; font-weight: 800; letter-spacing: 0.4px;
        color: #ffffff;
    }
    .app-header .subtitle {
        font-size: 0.98rem; font-weight: 500; color: #c9a24b; margin-top: 0.3rem;
        letter-spacing: 0.2px;
    }
    .app-header .desc {
        font-size: 0.88rem; color: #9fb2c8; margin-top: 0.55rem;
    }
    .role-badge {
        display: inline-block; background: rgba(201,162,75,0.14); color: #e8cf8c;
        border-left: 3px solid #c9a24b; border-radius: 4px;
        padding: 0.2rem 0.6rem; font-size: 0.7rem; font-weight: 700;
        letter-spacing: 0.4px; text-transform: uppercase; margin-top: 0.7rem;
    }

    /* ---------- Section titles ---------- */
    .section-title {
        font-size: 1.02rem; font-weight: 700; color: #0f2440;
        margin: 1.6rem 0 0.6rem 0; padding-bottom: 0.35rem;
        border-bottom: 2px solid #e3e9f2;
    }

    /* ---------- KPI cards ---------- */
    .kpi-card {
        background: white; border-radius: 14px; padding: 1.1rem 1rem;
        border: 1px solid #e3e9f2; box-shadow: 0 2px 10px rgba(15,36,64,0.05);
        text-align: center; height: 100%;
    }
    .kpi-label {
        font-size: 0.7rem; font-weight: 700; color: #6b7c93;
        text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 0.4rem;
    }
    .kpi-value {
        font-size: 1.6rem; font-weight: 800; color: #0f2440; line-height: 1.1;
    }
    .kpi-value.highlight { color: #1c8a4c; }
    .kpi-sub { font-size: 0.75rem; color: #8a97a8; margin-top: 0.25rem; }

    .impact-banner {
        background: linear-gradient(135deg, #eafaf1 0%, #dcf5e6 100%);
        border: 1px solid #b7ecc9; border-radius: 14px;
        padding: 1rem 1.3rem; margin: 1rem 0 1.4rem 0;
        font-size: 1.0rem; color: #0f5132; font-weight: 500;
    }

    .best-agent-card {
        background: linear-gradient(135deg, #fbf9f2 0%, #f7f0dd 100%);
        border: 1.5px solid #d9c07f; border-radius: 16px;
        padding: 1.5rem 1.6rem; margin-top: 0.5rem;
    }
    .best-agent-title { font-size: 0.78rem; font-weight: 700; color: #8a6a17;
        text-transform: uppercase; letter-spacing: 0.8px; }
    .best-agent-name { font-size: 1.5rem; font-weight: 800; color: #0f2440; margin-top: 0.2rem;}
    .best-agent-id { font-size: 0.85rem; color: #6b7c93; font-weight: 600;}

    .metric-row { display:flex; justify-content: space-between; margin: 0.55rem 0 0.15rem 0;
        font-size: 0.85rem; color: #33465e; font-weight: 600;}

    .footnote { font-size: 0.78rem; color: #8a97a8; margin-top: 1.8rem;
        border-top: 1px solid #e3e9f2; padding-top: 0.8rem; }

    div[data-testid="stMetricValue"] { font-size: 1.35rem; }
    .stButton>button {
        background: linear-gradient(120deg, #14263f 0%, #1c3a5e 100%);
        color: white; font-weight: 700; font-size: 1.0rem;
        padding: 0.65rem 1.4rem; border-radius: 9px; border: none; width: 100%;
    }
    .stButton>button:hover { background: linear-gradient(120deg, #0d1b30 0%, #163055 100%); color: white; }

    /* ---------- Sidebar / nav ---------- */
    section[data-testid="stSidebar"] {
        background: #0f2036;
    }
    section[data-testid="stSidebar"] * { color: #dbe4f0 !important; }
    .sidebar-brand { font-size: 1.15rem; font-weight: 800; color: #ffffff !important;
        letter-spacing: 0.3px; margin-bottom: 0.1rem; }
    .sidebar-sub { font-size: 0.72rem; color: #8fa3bd !important; margin-bottom: 1rem; }
    .sidebar-role { font-size: 0.72rem; color: #c9a24b !important; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.4px; }

    /* ---------- Login page ---------- */
    .login-wrap {
        max-width: 420px; margin: 3.5rem auto 0 auto;
        background: white; border-radius: 18px; padding: 2.4rem 2.2rem;
        border: 1px solid #e3e9f2; box-shadow: 0 10px 40px rgba(15,36,64,0.10);
    }
    .login-logo { font-size: 2rem; text-align: center; margin-bottom: 0.2rem; }
    .login-title { font-size: 1.35rem; font-weight: 800; color: #0f2440;
        text-align: center; margin-bottom: 0.15rem; }
    .login-subtitle { font-size: 0.82rem; color: #6b7c93; text-align: center;
        margin-bottom: 1.6rem; }
    .login-hint { font-size: 0.75rem; color: #8a97a8; background: #f4f6f9;
        border-radius: 10px; padding: 0.7rem 0.9rem; margin-top: 1.2rem; line-height: 1.5; }

    .admin-card {
        background: white; border-radius: 14px; padding: 1.3rem 1.4rem;
        border: 1px solid #e3e9f2; box-shadow: 0 2px 10px rgba(15,36,64,0.05);
        margin-bottom: 1rem;
    }
    .config-tag-default { display:inline-block; background:#eef3f8; color:#33465e;
        border-radius: 6px; padding: 0.1rem 0.5rem; font-size: 0.72rem; font-weight: 700; }
    .config-tag-active { display:inline-block; background:#eafaf1; color:#0f5132;
        border-radius: 6px; padding: 0.1rem 0.5rem; font-size: 0.72rem; font-weight: 700; }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# EXISTING FUNCTIONALITY — data validation, coercion, scoring
# (logic unchanged; weight/threshold values now sourced from session_state,
#  which defaults to the exact original constants)
# ==============================================================================
def validate_dataframe(df: pd.DataFrame):
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return False, f"The uploaded file is missing required column(s): {', '.join(missing)}"
    if df.empty:
        return False, "The uploaded file has no data rows."
    df = df.dropna(subset=REQUIRED_COLUMNS)
    if df.empty:
        return False, "No valid rows remain after removing rows with missing required fields."
    return True, ""


def coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = ["Average AHT (sec)"] + [c for c in OPTIONAL_NUMERIC_COLUMNS if c in df.columns]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def normalize(series: pd.Series, lower_is_better: bool) -> pd.Series:
    """Min-max normalize a series to 0-100. Handles constant / missing values safely."""
    s = series.astype(float)
    lo, hi = s.min(), s.max()
    if pd.isna(lo) or pd.isna(hi) or hi == lo:
        return pd.Series([70.0] * len(s), index=s.index)  # neutral score if no variation
    if lower_is_better:
        return 100 * (hi - s) / (hi - lo)
    return 100 * (s - lo) / (hi - lo)


def compute_scores(cat_df: pd.DataFrame) -> pd.DataFrame:
    """Compute a transparent 0-100 performance score for each agent row in a category.
    Formula and normalization logic is UNCHANGED from the original AHT Booster app.
    Weights are read from session_state (defaults to original 60/15/15/10)."""
    d = cat_df.copy()

    w_aht = st.session_state.cfg_w_aht
    w_quality = st.session_state.cfg_w_quality
    w_fcr = st.session_state.cfg_w_fcr
    w_transfer = st.session_state.cfg_w_transfer

    has_quality = "Quality Score (%)" in d.columns and d["Quality Score (%)"].notna().any()
    has_fcr = "FCR (%)" in d.columns and d["FCR (%)"].notna().any()
    has_transfer = "Transfer Rate (%)" in d.columns and d["Transfer Rate (%)"].notna().any()

    d["_aht_score"] = normalize(d["Average AHT (sec)"], lower_is_better=True)
    d["_quality_score"] = normalize(d["Quality Score (%)"], lower_is_better=False) if has_quality else 70.0
    d["_fcr_score"] = normalize(d["FCR (%)"], lower_is_better=False) if has_fcr else 70.0
    d["_transfer_score"] = normalize(d["Transfer Rate (%)"], lower_is_better=True) if has_transfer else 70.0

    # Re-normalize weights if some components are unavailable, so total is still 0-100
    weights = {"_aht_score": w_aht}
    if has_quality: weights["_quality_score"] = w_quality
    if has_fcr: weights["_fcr_score"] = w_fcr
    if has_transfer: weights["_transfer_score"] = w_transfer
    total_w = sum(weights.values())
    weights = {k: v / total_w for k, v in weights.items()}

    d["Performance Score"] = sum(d[col] * w for col, w in weights.items())
    d["Performance Score"] = d["Performance Score"].round(1)
    return d


def eligible_pool(cat_df: pd.DataFrame) -> pd.DataFrame:
    """Availability eligibility filter — logic unchanged; threshold sourced from
    session_state (defaults to the original 80%)."""
    threshold = st.session_state.cfg_availability_threshold
    if "Availability (%)" in cat_df.columns and cat_df["Availability (%)"].notna().any():
        pool = cat_df[cat_df["Availability (%)"] >= threshold]
        if pool.empty:  # fall back so the demo never dead-ends
            pool = cat_df
        return pool
    return cat_df


def bar(pct, color="#2563a8"):
    pct = max(0, min(100, pct))
    st.markdown(f"""
    <div style="background:#eef1f6; border-radius:6px; height:10px; width:100%; margin-bottom:2px;">
        <div style="background:{color}; width:{pct}%; height:10px; border-radius:6px;"></div>
    </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# NEW FUNCTIONALITY — shared upload/processing helper
# (wraps the exact original validate_dataframe + coerce_numeric sequence so it
#  can be reused identically from both the Recommendation page and the Admin
#  Console's Data Management tab)
# ==============================================================================
def process_uploaded_file(uploaded_file):
    """Returns (success: bool, result: DataFrame | error message str)."""
    try:
        raw_df = pd.read_excel(uploaded_file)
    except Exception as e:
        return False, f"Could not read the uploaded file. Please upload a valid Excel file. Details: {e}"

    ok, msg = validate_dataframe(raw_df)
    if not ok:
        return False, msg

    df = coerce_numeric(raw_df.dropna(subset=REQUIRED_COLUMNS).copy())
    df = df.dropna(subset=["Average AHT (sec)"])

    if df.empty:
        return False, "No valid numeric AHT data found after cleaning. Please check the file."

    return True, df


def get_active_dataset():
    """Returns the currently shared/active dataset (or None)."""
    return st.session_state.dataset


# ==============================================================================
# NEW FUNCTIONALITY — LOGIN PAGE
# ==============================================================================
def render_login():
    st.markdown(f"""
    <div class="login-wrap">
        <div class="login-logo">🧭</div>
        <div class="login-title">{APP_NAME}</div>
        <div class="login-subtitle">{APP_SUBTITLE}</div>
    </div>
    """, unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 1.3, 1])
    with mid:
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Email / Username", placeholder="you@sagility.com")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            role, display_name = authenticate(username, password)
            if role:
                st.session_state.authenticated = True
                st.session_state.role = role
                st.session_state.username = display_name
                st.session_state.nav_page = "Dashboard"
                st.rerun()
            else:
                st.error("⚠️ Invalid email or password. Please try again.")

        st.markdown("""
        <div class="login-hint">
            <b>Demo credentials</b><br>
            Manager — manager@sagility.com / Manager@123<br>
            Admin — admin@sagility.com / Admin@123
        </div>
        """, unsafe_allow_html=True)


# ==============================================================================
# NEW FUNCTIONALITY — SIDEBAR NAVIGATION
# ==============================================================================
def render_sidebar_nav():
    with st.sidebar:
        st.markdown(f'<div class="sidebar-brand">🧭 {APP_NAME}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sidebar-sub">{APP_SUBTITLE}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sidebar-role">{st.session_state.role} · {st.session_state.username}</div>',
                    unsafe_allow_html=True)
        st.markdown("---")

        pages = ["Dashboard", "Recommendation"]
        if st.session_state.role == "Admin":
            pages.append("Admin Console")

        icons = {
            "Dashboard": "🏠",
            "Recommendation": "🎯",
            "Admin Console": "🛠️",
        }

        for page in pages:
            is_active = st.session_state.nav_page == page
            if st.button(f"{icons[page]}  {page}", key=f"nav_{page}", use_container_width=True,
                         type="primary" if is_active else "secondary"):
                st.session_state.nav_page = page
                st.rerun()

        st.markdown("---")
        if st.button("🚪  Logout", use_container_width=True):
            for key in ["authenticated", "username", "role", "nav_page", "has_run"]:
                st.session_state[key] = False if key == "authenticated" else None
            st.session_state.nav_page = "Dashboard"
            st.rerun()


# ==============================================================================
# NEW FUNCTIONALITY — HEADER (rebranded)
# ==============================================================================
def render_header():
    st.markdown(f"""
    <div class="app-header">
        <h1>🧭 {APP_NAME.upper()}</h1>
        <div class="subtitle">{APP_SUBTITLE}</div>
        <div class="desc">Route calls to the right agent and reduce average handle time.</div>
        <div class="role-badge">{st.session_state.role} view</div>
    </div>
    """, unsafe_allow_html=True)


# ==============================================================================
# NEW FUNCTIONALITY — DASHBOARD PAGE
# ==============================================================================
def render_dashboard():
    render_header()
    st.markdown(f"### Welcome, {st.session_state.username.split()[0]} 👋")
    st.write("Use the navigation on the left to run agent recommendations "
             + ("or manage data and configuration in the Admin Console." if st.session_state.role == "Admin" else "."))
    if st.session_state.role == "Admin":
        st.caption("On a phone, if the left sidebar isn't visible, tap the small **›** arrow at the very "
                   "top-left corner of the app to open it — Admin Console is listed there.")

    ds = get_active_dataset()
    st.markdown('<div class="section-title">📊 Current Dataset</div>', unsafe_allow_html=True)
    if ds is None:
        st.info("No dataset loaded yet. Go to **Recommendation** to upload an Excel file"
                + (", or use **Admin Console → Data Management**." if st.session_state.role == "Admin" else "."))
    else:
        c1, c2, c3 = st.columns(3)
        c1.markdown(f'<div class="kpi-card"><div class="kpi-label">Agents Loaded</div>'
                    f'<div class="kpi-value">{ds["Agent ID"].nunique()}</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="kpi-card"><div class="kpi-label">Records Loaded</div>'
                    f'<div class="kpi-value">{len(ds)}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="kpi-card"><div class="kpi-label">Call Categories</div>'
                    f'<div class="kpi-value">{ds["Call Category"].nunique()}</div></div>', unsafe_allow_html=True)
        if st.session_state.dataset_source:
            st.caption(f"Source file: {st.session_state.dataset_source}")

    st.markdown('<div class="section-title">🚀 Quick Actions</div>', unsafe_allow_html=True)
    if st.button("🎯 Go to Recommendation", use_container_width=True):
        st.session_state.nav_page = "Recommendation"
        st.rerun()


# ==============================================================================
# EXISTING FUNCTIONALITY — RECOMMENDATION PAGE
# (Screens 2–7 from the original AHT Booster app, unchanged, now wrapped in a
#  function and using the shared session-level dataset so it persists across
#  page navigation.)
# ==============================================================================
def render_recommendation_page():
    render_header()

    # ---- SCREEN 2 — UPLOAD (existing) ----
    st.markdown('<div class="section-title">📤 Upload Agent Performance Data</div>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload the agent performance Excel file (.xlsx or .xls)",
        type=["xlsx", "xls"],
        label_visibility="collapsed",
        key="reco_uploader",
    )

    st.caption("Demo uses synthetic agent-performance data. Production implementation can use "
               "historical operational data and an ML-based AHT prediction model.")

    if uploaded_file is not None:
        ok, result = process_uploaded_file(uploaded_file)
        if not ok:
            st.error(f"⚠️ {result}")
            st.stop()
        st.session_state.dataset = result
        st.session_state.dataset_source = uploaded_file.name
        st.session_state.has_run = False

    df = get_active_dataset()

    if df is None:
        st.info("⬆️ Upload the AHT_Booster_Demo_Input.xlsx file (or your own agent performance "
                "file with the required columns) to begin.")
        with st.expander("Required columns"):
            st.write(REQUIRED_COLUMNS)
        st.stop()
    elif uploaded_file is None:
        st.caption(f"Using previously loaded dataset ({len(df)} records"
                   f"{' from ' + st.session_state.dataset_source if st.session_state.dataset_source else ''}). "
                   "Upload a new file above to replace it.")

    n_agents = df["Agent ID"].nunique()
    n_records = len(df)
    categories = sorted(df["Call Category"].dropna().unique().tolist())

    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="kpi-card"><div class="kpi-label">Agents Loaded</div>'
                f'<div class="kpi-value">{n_agents}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi-card"><div class="kpi-label">Records Loaded</div>'
                f'<div class="kpi-value">{n_records}</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi-card"><div class="kpi-label">Call Categories</div>'
                f'<div class="kpi-value">{len(categories)}</div></div>', unsafe_allow_html=True)

    st.success("✅ File loaded successfully.")

    # ---- SCREEN 3 — INPUTS (existing) ----
    st.markdown('<div class="section-title">⚙️ Configure Your Query</div>', unsafe_allow_html=True)

    in1, in2 = st.columns([1, 1.4])
    with in1:
        num_calls = st.number_input("Number of Calls", min_value=1, max_value=100000, value=8, step=1)
    with in2:
        selected_category = st.selectbox("Select Call Category", categories)

    # ---- SCREEN 4 — BUTTON (existing) ----
    run = st.button("🔍 FIND BEST AGENT", type="primary", use_container_width=True)

    if run:
        st.session_state.has_run = True

    if not st.session_state.has_run:
        st.stop()

    # ---- CORE ANALYSIS (existing, recomputed every run) ----
    cat_df = df[df["Call Category"] == selected_category].copy()

    if cat_df.empty:
        st.error(f"No records found for category '{selected_category}'.")
        st.stop()

    category_avg_aht = float(cat_df["Average AHT (sec)"].mean())

    pool = eligible_pool(cat_df)
    scored = compute_scores(pool)
    scored = scored.sort_values(["Performance Score", "Average AHT (sec)"], ascending=[False, True])

    best = scored.iloc[0]
    best_aht = float(best["Average AHT (sec)"])

    saving_per_call = category_avg_aht - best_aht
    total_seconds_saved = saving_per_call * num_calls
    total_minutes_saved = total_seconds_saved / 60.0

    # ---- SCREEN 5 — BUSINESS IMPACT (existing) ----
    st.markdown('<div class="section-title">📊 Business Impact</div>', unsafe_allow_html=True)

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f'<div class="kpi-card"><div class="kpi-label">Number of Calls</div>'
                f'<div class="kpi-value">{num_calls:,}</div></div>', unsafe_allow_html=True)
    k2.markdown(f'<div class="kpi-card"><div class="kpi-label">Category Avg AHT</div>'
                f'<div class="kpi-value">{category_avg_aht:.0f}<span style="font-size:0.9rem;"> sec</span></div></div>',
                unsafe_allow_html=True)
    k3.markdown(f'<div class="kpi-card"><div class="kpi-label">Recommended Agent AHT</div>'
                f'<div class="kpi-value">{best_aht:.0f}<span style="font-size:0.9rem;"> sec</span></div></div>',
                unsafe_allow_html=True)
    k4.markdown(f'<div class="kpi-card"><div class="kpi-label">Total Time Saved</div>'
                f'<div class="kpi-value highlight">{total_minutes_saved:.1f}<span style="font-size:0.9rem;"> min</span></div></div>',
                unsafe_allow_html=True)

    direction = "save" if total_minutes_saved >= 0 else "cost an additional"
    impact_sentence = (
        f"Routing <b>{num_calls}</b> {selected_category} calls to the recommended agent could "
        f"potentially {direction} approximately <b>{abs(total_minutes_saved):.1f} minutes</b> "
        f"compared with the category average."
    )
    st.markdown(f'<div class="impact-banner">💡 <b>Potential AHT Impact</b><br>{impact_sentence}</div>',
                unsafe_allow_html=True)

    # ---- SCREEN 6 — BEST AGENT (existing) ----
    st.markdown('<div class="section-title">🏆 Best Fit Agent</div>', unsafe_allow_html=True)

    bc1, bc2 = st.columns([1.3, 1])
    with bc1:
        st.markdown(f"""
        <div class="best-agent-card">
            <div class="best-agent-title">Best Fit Agent</div>
            <div class="best-agent-name">{best['Agent Name']}</div>
            <div class="best-agent-id">Agent ID: {best['Agent ID']}</div>
            <hr style="border-color:#ecdfb0; margin: 0.8rem 0;">
            <div class="metric-row"><span>Selected Call Category</span><span>{selected_category}</span></div>
            <div class="metric-row"><span>Average AHT</span><span>{best_aht:.0f} sec</span></div>
            <div class="metric-row"><span>Performance Score</span><span>{best['Performance Score']:.1f} / 100</span></div>
            <div class="metric-row"><span>Saving Per Call</span><span>{saving_per_call:.0f} sec</span></div>
            <div class="metric-row"><span>Total Estimated Saving</span><span>{total_minutes_saved:.1f} min ({num_calls} calls)</span></div>
        </div>
        """, unsafe_allow_html=True)

    with bc2:
        st.markdown("**Why this agent?**")
        aht_pct = float(best.get("_aht_score", 70))
        quality_val = best.get("Quality Score (%)", np.nan)
        fcr_val = best.get("FCR (%)", np.nan)
        transfer_val = best.get("Transfer Rate (%)", np.nan)
        avail_val = best.get("Availability (%)", np.nan)

        st.caption(f"AHT performance — {aht_pct:.0f}/100 (relative to category)")
        bar(aht_pct, "#2563a8")
        if pd.notna(quality_val):
            st.caption(f"Quality — {quality_val:.1f}%")
            bar(quality_val, "#1c8a4c")
        if pd.notna(fcr_val):
            st.caption(f"FCR — {fcr_val:.1f}%")
            bar(fcr_val, "#7c3aed")
        if pd.notna(transfer_val):
            st.caption(f"Transfer Rate — {transfer_val:.1f}% (lower is better)")
            bar(max(0, 100 - transfer_val * 3), "#e08d00")
        if pd.notna(avail_val):
            st.caption(f"Availability — {avail_val:.1f}%")
            bar(avail_val, "#0f9d8b")

    # ---- SCREEN 7 — TOP 10 AGENTS (was Top 5; extended per request, same ranking logic) ----
    st.markdown('<div class="section-title">📋 Top 10 Recommended Agents</div>', unsafe_allow_html=True)

    top10 = scored.head(10).reset_index(drop=True)
    top10.insert(0, "Rank", range(1, len(top10) + 1))

    display_cols = ["Rank", "Agent Name", "Agent ID", "Average AHT (sec)", "Performance Score"]
    for opt_col in ["Quality Score (%)", "FCR (%)", "Transfer Rate (%)", "Availability (%)"]:
        if opt_col in top10.columns:
            display_cols.append(opt_col)

    st.dataframe(
        top10[display_cols].rename(columns={"Average AHT (sec)": "AHT (sec)"}),
        use_container_width=True,
        hide_index=True,
    )

    if len(top10) < 10:
        st.caption(f"Only {len(top10)} eligible agent(s) available for {selected_category} — showing all of them.")

    # ---- HOW IT WORKS (existing, text now reflects active — possibly admin-adjusted — config) ----
    with st.expander("ℹ️ How it works — recommendation logic"):
        st.markdown(f"""
This is a transparent, rule-based scoring engine (no black box):

1. **Filter to the selected call category** from the uploaded Excel data.
2. **Eligibility filter:** agents with Availability below {st.session_state.cfg_availability_threshold:.0f}% are
   excluded when availability data is present (falls back to the full pool if everyone is below
   the threshold, so the demo always returns a result).
3. **Normalize each metric to a 0–100 scale** within the category (min–max normalization):
   - Lower **AHT** → higher score
   - Higher **Quality Score** → higher score
   - Higher **FCR** → higher score
   - Lower **Transfer Rate** → higher score
4. **Weighted final score:**
   - AHT: **{st.session_state.cfg_w_aht*100:.0f}%**
   - Quality: **{st.session_state.cfg_w_quality*100:.0f}%**
   - FCR: **{st.session_state.cfg_w_fcr*100:.0f}%**
   - Transfer Rate: **{st.session_state.cfg_w_transfer*100:.0f}%**
   (Weights are automatically re-balanced if a metric column is missing from the file. These are
   the platform's original default weights unless an Admin has saved a custom configuration.)
5. **Rank agents** by final score (ties broken by lower AHT) and recommend the top agent.
6. **Time savings:**
   `Saving per call = Category Average AHT − Recommended Agent AHT`
   `Total seconds saved = Saving per call × Number of Calls`
   `Total minutes saved = Total seconds saved / 60`

Every number on this page is recalculated live from the uploaded file — nothing is hardcoded.
Upload a different Excel file with the same required columns and the recommendation, ranking,
and savings will change accordingly.
        """)

    st.markdown(
        '<div class="footnote">Demo uses synthetic agent-performance data. Production implementation '
        'can use historical operational data and an ML-based AHT prediction model.</div>',
        unsafe_allow_html=True,
    )


# ==============================================================================
# NEW FUNCTIONALITY — ADMIN CONSOLE
# ==============================================================================
def render_admin_console():
    render_header()
    st.markdown('<div class="section-title">🛠️ Admin Console</div>', unsafe_allow_html=True)

    tab_data, tab_validate, tab_weights, tab_avail = st.tabs(
        ["📂 Data Management", "✅ Data Validation", "⚖️ Ranking Configuration", "🎚️ Availability Configuration"]
    )

    # ---- A. DATA MANAGEMENT ----
    with tab_data:
        st.markdown("#### Upload / Replace Dataset")
        st.caption("Uploading a new file here replaces the dataset used across the whole platform.")
        admin_file = st.file_uploader("Upload Excel file (.xlsx or .xls)", type=["xlsx", "xls"], key="admin_uploader")

        if admin_file is not None:
            ok, result = process_uploaded_file(admin_file)
            if ok:
                st.session_state.dataset = result
                st.session_state.dataset_source = admin_file.name
                st.session_state.has_run = False
                st.success(f"✅ Dataset replaced successfully — {len(result)} records loaded.")
            else:
                st.error(f"⚠️ {result}")

        ds = get_active_dataset()
        st.markdown("#### Current Active Dataset")
        if ds is None:
            st.info("No dataset currently loaded.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.markdown(f'<div class="kpi-card"><div class="kpi-label">Total Records</div>'
                        f'<div class="kpi-value">{len(ds)}</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="kpi-card"><div class="kpi-label">Unique Agents</div>'
                        f'<div class="kpi-value">{ds["Agent ID"].nunique()}</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="kpi-card"><div class="kpi-label">Call Categories</div>'
                        f'<div class="kpi-value">{ds["Call Category"].nunique()}</div></div>', unsafe_allow_html=True)
            if st.session_state.dataset_source:
                st.caption(f"Source file: {st.session_state.dataset_source}")
            st.markdown("**Preview (first 20 rows)**")
            st.dataframe(ds.head(20), use_container_width=True, hide_index=True)

    # ---- B. DATA VALIDATION ----
    with tab_validate:
        ds = get_active_dataset()
        if ds is None:
            st.info("Upload a dataset in the Data Management tab first.")
        else:
            st.markdown("#### Required Columns")
            for col in REQUIRED_COLUMNS:
                present = col in ds.columns
                st.write(f"{'✅' if present else '❌'} {col}")

            st.markdown("#### Missing Values")
            missing_counts = ds.isna().sum()
            missing_counts = missing_counts[missing_counts > 0]
            if missing_counts.empty:
                st.success("✅ No missing values found in the active dataset.")
            else:
                st.dataframe(missing_counts.rename("Missing Values").to_frame(),
                             use_container_width=True)

            st.markdown("#### Duplicate Records")
            key_cols = [c for c in ["Agent ID", "Call Category"] if c in ds.columns]
            if len(key_cols) == 2:
                dup_mask = ds.duplicated(subset=key_cols, keep=False)
                dup_count = int(dup_mask.sum())
                if dup_count == 0:
                    st.success("✅ No duplicate Agent ID + Call Category combinations found.")
                else:
                    st.warning(f"⚠️ {dup_count} duplicate row(s) found for the same Agent ID + Call Category.")
                    st.dataframe(ds[dup_mask].sort_values(key_cols), use_container_width=True, hide_index=True)
            else:
                st.caption("Duplicate check requires both 'Agent ID' and 'Call Category' columns.")

    # ---- C. RANKING CONFIGURATION ----
    with tab_weights:
        st.markdown("#### Existing Default Configuration")
        st.caption("These are the platform's original weights — unchanged unless you explicitly save a new configuration below.")
        st.markdown(f"""
        <div class="admin-card">
            AHT: <span class="config-tag-default">{DEFAULT_W_AHT*100:.0f}%</span> &nbsp;
            Quality: <span class="config-tag-default">{DEFAULT_W_QUALITY*100:.0f}%</span> &nbsp;
            FCR: <span class="config-tag-default">{DEFAULT_W_FCR*100:.0f}%</span> &nbsp;
            Transfer Rate: <span class="config-tag-default">{DEFAULT_W_TRANSFER*100:.0f}%</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Currently Active Configuration")
        active_default = (
            abs(st.session_state.cfg_w_aht - DEFAULT_W_AHT) < 1e-9 and
            abs(st.session_state.cfg_w_quality - DEFAULT_W_QUALITY) < 1e-9 and
            abs(st.session_state.cfg_w_fcr - DEFAULT_W_FCR) < 1e-9 and
            abs(st.session_state.cfg_w_transfer - DEFAULT_W_TRANSFER) < 1e-9
        )
        st.markdown(f"""
        <div class="admin-card">
            AHT: <span class="config-tag-active">{st.session_state.cfg_w_aht*100:.0f}%</span> &nbsp;
            Quality: <span class="config-tag-active">{st.session_state.cfg_w_quality*100:.0f}%</span> &nbsp;
            FCR: <span class="config-tag-active">{st.session_state.cfg_w_fcr*100:.0f}%</span> &nbsp;
            Transfer Rate: <span class="config-tag-active">{st.session_state.cfg_w_transfer*100:.0f}%</span>
            {'&nbsp; <i>(matches default)</i>' if active_default else '&nbsp; <i>(custom — differs from default)</i>'}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Adjust Weights (optional)")
        w1, w2 = st.columns(2)
        with w1:
            new_aht = st.number_input("AHT weight (%)", min_value=0, max_value=100,
                                       value=int(round(st.session_state.cfg_w_aht * 100)))
            new_fcr = st.number_input("FCR weight (%)", min_value=0, max_value=100,
                                       value=int(round(st.session_state.cfg_w_fcr * 100)))
        with w2:
            new_quality = st.number_input("Quality weight (%)", min_value=0, max_value=100,
                                           value=int(round(st.session_state.cfg_w_quality * 100)))
            new_transfer = st.number_input("Transfer Rate weight (%)", min_value=0, max_value=100,
                                            value=int(round(st.session_state.cfg_w_transfer * 100)))

        total_pct = new_aht + new_quality + new_fcr + new_transfer
        if total_pct != 100:
            st.caption(f"⚠️ Weights currently sum to {total_pct}%. They will be auto-normalized to total 100% on save.")

        save_col, reset_col = st.columns(2)
        with save_col:
            if st.button("💾 Save Configuration", use_container_width=True):
                total = max(total_pct, 1)  # avoid divide-by-zero
                st.session_state.cfg_w_aht = new_aht / total
                st.session_state.cfg_w_quality = new_quality / total
                st.session_state.cfg_w_fcr = new_fcr / total
                st.session_state.cfg_w_transfer = new_transfer / total
                st.success("✅ Ranking configuration saved and applied.")
                st.rerun()
        with reset_col:
            if st.button("↺ Reset to Existing Default Configuration", use_container_width=True):
                st.session_state.cfg_w_aht = DEFAULT_W_AHT
                st.session_state.cfg_w_quality = DEFAULT_W_QUALITY
                st.session_state.cfg_w_fcr = DEFAULT_W_FCR
                st.session_state.cfg_w_transfer = DEFAULT_W_TRANSFER
                st.success("✅ Reset to the existing default weights.")
                st.rerun()

    # ---- D. AVAILABILITY CONFIGURATION ----
    with tab_avail:
        st.markdown("#### Existing Default Threshold")
        st.markdown(f'<div class="admin-card">Availability threshold: '
                    f'<span class="config-tag-default">{DEFAULT_AVAILABILITY_THRESHOLD:.0f}%</span></div>',
                    unsafe_allow_html=True)

        st.markdown("#### Currently Active Threshold")
        is_default_avail = abs(st.session_state.cfg_availability_threshold - DEFAULT_AVAILABILITY_THRESHOLD) < 1e-9
        st.markdown(f'<div class="admin-card">Availability threshold: '
                    f'<span class="config-tag-active">{st.session_state.cfg_availability_threshold:.0f}%</span>'
                    f'{" &nbsp; <i>(matches default)</i>" if is_default_avail else " &nbsp; <i>(custom — differs from default)</i>"}'
                    f'</div>', unsafe_allow_html=True)

        st.markdown("#### Adjust Threshold (optional)")
        new_threshold = st.number_input(
            "Minimum Availability (%) for an agent to be eligible",
            min_value=0, max_value=100,
            value=int(round(st.session_state.cfg_availability_threshold)),
        )

        save_col2, reset_col2 = st.columns(2)
        with save_col2:
            if st.button("💾 Save Threshold", use_container_width=True):
                st.session_state.cfg_availability_threshold = float(new_threshold)
                st.success("✅ Availability threshold saved and applied.")
                st.rerun()
        with reset_col2:
            if st.button("↺ Reset to Existing Default Threshold", use_container_width=True):
                st.session_state.cfg_availability_threshold = DEFAULT_AVAILABILITY_THRESHOLD
                st.success("✅ Reset to the existing default threshold (80%).")
                st.rerun()


# ==============================================================================
# MAIN — routing
# ==============================================================================
def main():
    if not st.session_state.authenticated:
        render_login()
        return

    render_sidebar_nav()

    page = st.session_state.nav_page
    if page == "Dashboard":
        render_dashboard()
    elif page == "Recommendation":
        render_recommendation_page()
    elif page == "Admin Console" and st.session_state.role == "Admin":
        render_admin_console()
    else:
        st.session_state.nav_page = "Dashboard"
        render_dashboard()


main()
