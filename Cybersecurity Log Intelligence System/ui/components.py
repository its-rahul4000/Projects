import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from config.settings import APP_NAME, ROLE_ADMIN, ROLE_IT_OWNER, SEVERITY_COLORS


# ── CSS ───────────────────────────────────────────────────────────────────────

_CSS = """
<style>
/* ===== Hide sidebar completely ===== */
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
section[data-testid="stSidebarNav"] {
    display: none !important;
}

/* ===== Global base ===== */
.stApp {
    background: #f0f4f8;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                 'Helvetica Neue', Arial, sans-serif;
}
.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ===== Brand header ===== */
.brand-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #0d2137 100%);
    color: white;
    padding: 14px 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 2px 10px rgba(0,0,0,0.25);
    margin-bottom: 0;
}
.brand-left  { display: flex; align-items: center; gap: 10px; }
.brand-icon  { font-size: 1.6rem; }
.brand-name  { font-size: 1.05rem; font-weight: 700; letter-spacing: 0.01em; }
.brand-right { font-size: 0.82rem; color: #a0bcd8; text-align: right; line-height: 1.4; }
.brand-role  { font-weight: 600; color: #7eb3e3; }

/* ===== Nav bar marker trick ===== */
.nav-marker { display: none; }

/* Style the stHorizontalBlock that directly follows .nav-marker's container */
.element-container:has(.nav-marker) + div [data-testid="stHorizontalBlock"] {
    background: #163050;
    padding: 5px 16px !important;
    border-bottom: 2px solid #2563eb;
    gap: 2px !important;
    flex-wrap: nowrap !important;
}
.element-container:has(.nav-marker) + div [data-testid="stHorizontalBlock"] button {
    font-size: 0.75rem !important;
    padding: 5px 4px !important;
    border-radius: 5px !important;
    font-weight: 500 !important;
    border: none !important;
    transition: background 0.15s ease !important;
}
.element-container:has(.nav-marker) + div [data-testid="stHorizontalBlock"] button[kind="secondary"] {
    background: transparent !important;
    color: #9ab8d4 !important;
}
.element-container:has(.nav-marker) + div [data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.12) !important;
    color: #e8f4ff !important;
}
.element-container:has(.nav-marker) + div [data-testid="stHorizontalBlock"] button[kind="primary"] {
    background: #2563eb !important;
    color: white !important;
    font-weight: 600 !important;
}

/* ===== Page padding wrapper ===== */
.page-wrapper {
    padding: 24px 28px;
    max-width: 1400px;
    margin: 0 auto;
}

/* ===== Page header ===== */
.page-header {
    margin-bottom: 20px;
}
.page-title {
    font-size: 1.7rem;
    font-weight: 700;
    color: #1e3a5f;
    margin: 0 0 4px 0;
}
.page-subtitle {
    font-size: 0.88rem;
    color: #718096;
    margin: 0;
}

/* ===== Metric cards ===== */
.metric-row { display: flex; gap: 14px; margin-bottom: 24px; }
.metric-card {
    flex: 1;
    background: white;
    border-radius: 12px;
    padding: 20px 16px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.07);
    text-align: center;
    border-top: 4px solid #e2e8f0;
    min-width: 0;
}
.metric-card.total    { border-top-color: #2563eb; }
.metric-card.critical { border-top-color: #dc2626; }
.metric-card.high     { border-top-color: #ea580c; }
.metric-card.medium   { border-top-color: #d97706; }
.metric-card.low      { border-top-color: #16a34a; }
.metric-value {
    font-size: 2.2rem;
    font-weight: 800;
    color: #1a202c;
    line-height: 1.1;
    margin: 0;
}
.metric-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: #718096;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 6px;
}
.metric-card.total    .metric-value { color: #2563eb; }
.metric-card.critical .metric-value { color: #dc2626; }
.metric-card.high     .metric-value { color: #ea580c; }
.metric-card.medium   .metric-value { color: #d97706; }
.metric-card.low      .metric-value { color: #16a34a; }

/* ===== Severity badges ===== */
.sev-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.sev-critical { background: #fee2e2; color: #b91c1c; }
.sev-high     { background: #ffedd5; color: #c2410c; }
.sev-medium   { background: #fef9c3; color: #854d0e; }
.sev-low      { background: #dcfce7; color: #166534; }
.sev-info     { background: #dbeafe; color: #1d4ed8; }

/* ===== Info / alert boxes ===== */
.info-box {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 16px;
    color: #1e40af;
    font-size: 0.9rem;
}
.warn-box {
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 16px;
    color: #92400e;
}
.success-box {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 16px;
    color: #14532d;
}
.error-box {
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 16px;
    color: #7f1d1d;
}

/* ===== Temp-password display box ===== */
.temp-pass-box {
    background: #1e3a5f;
    color: #7dd3fc;
    font-family: 'Courier New', Courier, monospace;
    font-size: 1.1rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    padding: 14px 20px;
    border-radius: 8px;
    text-align: center;
    margin: 12px 0;
    word-break: break-all;
}

/* ===== Login page ===== */
.login-outer {
    min-height: 80vh;
    display: flex;
    align-items: center;
    justify-content: center;
}
.login-card {
    background: white;
    border-radius: 16px;
    padding: 40px 36px;
    box-shadow: 0 8px 40px rgba(0,0,0,0.13);
    width: 100%;
    max-width: 420px;
    margin: 40px auto;
}
.login-logo   { text-align: center; font-size: 3rem; margin-bottom: 4px; }
.login-title  { text-align: center; font-size: 1.4rem; font-weight: 700; color: #1e3a5f; margin: 0; }
.login-sub    { text-align: center; font-size: 0.84rem; color: #718096; margin: 6px 0 28px; }

/* ===== Section cards ===== */
.section-card {
    background: white;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 1px 8px rgba(0,0,0,0.07);
    margin-bottom: 20px;
}
.section-title {
    font-size: 1rem;
    font-weight: 700;
    color: #1e3a5f;
    margin: 0 0 16px 0;
    padding-bottom: 10px;
    border-bottom: 1px solid #e2e8f0;
}

/* ===== Stats row (admin overview) ===== */
.stat-chip {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 16px 24px;
    min-width: 120px;
}
.stat-chip-value { font-size: 1.8rem; font-weight: 800; color: #1e3a5f; }
.stat-chip-label { font-size: 0.72rem; font-weight: 600; color: #718096;
                   text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px; }

/* ===== Upload dropzone enhancement ===== */
[data-testid="stFileUploader"] {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 1px 8px rgba(0,0,0,0.07);
}

/* ===== Streamlit default overrides ===== */
h1, h2, h3 { color: #1e3a5f !important; }
.stAlert    { border-radius: 10px !important; }
.stButton > button {
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: box-shadow 0.15s !important;
}
.stButton > button:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important; }
div[data-testid="stForm"] { background: transparent !important; border: none !important; }

/* ===== Divider ===== */
hr { border-color: #e2e8f0 !important; margin: 16px 0 !important; }
</style>
"""


def set_page_style():
    st.markdown(_CSS, unsafe_allow_html=True)


def severity_badge(severity: str) -> str:
    cls = f"sev-{severity.lower()}"
    return f'<span class="sev-badge {cls}">{severity}</span>'


def safe_ts_str(ts, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Safely format a timestamp that might be pd.NaT, None, or a real datetime."""
    if ts is None:
        return "N/A"
    try:
        if pd.isnull(ts):
            return "N/A"
    except (TypeError, ValueError):
        pass
    try:
        return ts.strftime(fmt)
    except (AttributeError, ValueError, OverflowError):
        return str(ts)[:19]


# ── Navigation ────────────────────────────────────────────────────────────────

def render_top_nav(user):
    current = st.session_state.get("page", "dashboard")
    role = getattr(user, "role", ROLE_IT_OWNER)

    # Brand header
    role_label = "Administrator" if role == ROLE_ADMIN else "IT Owner"
    st.markdown(
        f"""<div class="brand-header">
          <div class="brand-left">
            <span class="brand-icon">🛡️</span>
            <span class="brand-name">{APP_NAME}</span>
          </div>
          <div class="brand-right">
            <span class="brand-role">{user.username}</span><br>
            <span>{role_label}</span>
          </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # Nav items
    if role == ROLE_ADMIN:
        nav = [
            ("dashboard",        "🏠 Dashboard"),
            ("upload",           "📁 Upload"),
            ("results",          "🔍 Results"),
            ("rules",            "⚡ Rules"),
            ("users",            "👥 Users"),
            ("audit",            "📋 Audit"),
            ("settings",         "⚙️ Settings"),
            ("change_password",  "🔑 Password"),
        ]
    else:
        nav = [
            ("dashboard",        "🏠 Dashboard"),
            ("upload",           "📁 Upload"),
            ("results",          "🔍 Results"),
            ("rules",            "📋 Rules"),
            ("change_password",  "🔑 Password"),
        ]

    st.markdown('<div class="nav-marker"></div>', unsafe_allow_html=True)
    cols = st.columns(len(nav) + 1)
    for col, (page, label) in zip(cols, nav):
        with col:
            btn_type = "primary" if current == page else "secondary"
            if st.button(label, key=f"nav_{page}", use_container_width=True, type=btn_type):
                st.session_state["page"] = page
                st.rerun()
    with cols[-1]:
        if st.button("🚪 Logout", key="nav_logout", use_container_width=True, type="secondary"):
            _do_logout()


def _do_logout():
    from auth.session_manager import invalidate_session
    from utils.temp_file_manager import cleanup_session_files
    from services.audit_service import log_action, ACTION_LOGOUT
    from database.db import get_db

    token = st.session_state.get("session_token")
    user_id = st.session_state.get("current_user_id")
    if token:
        db = get_db()
        try:
            if user_id:
                log_action(user_id, ACTION_LOGOUT, db)
            invalidate_session(token, db)
            cleanup_session_files(token)
        finally:
            db.close()

    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# ── Severity summary cards ────────────────────────────────────────────────────

def show_severity_cards(summary: dict):
    metrics = [
        ("total",    "Total",    summary.get("total", 0)),
        ("critical", "Critical", summary.get("CRITICAL", 0)),
        ("high",     "High",     summary.get("HIGH", 0)),
        ("medium",   "Medium",   summary.get("MEDIUM", 0)),
        ("low",      "Low",      summary.get("LOW", 0)),
    ]
    html = '<div class="metric-row">'
    for cls, label, val in metrics:
        html += (
            f'<div class="metric-card {cls}">'
            f'<div class="metric-value">{val}</div>'
            f'<div class="metric-label">{label}</div>'
            f'</div>'
        )
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


# ── Charts ────────────────────────────────────────────────────────────────────

def plot_severity_pie(findings: list[dict]):
    if not findings:
        return None
    df = pd.DataFrame(findings)
    counts = df["severity"].value_counts().reset_index()
    counts.columns = ["Severity", "Count"]
    color_map = {k: v for k, v in SEVERITY_COLORS.items()}
    fig = px.pie(
        counts, names="Severity", values="Count",
        title="Threat Severity Distribution",
        color="Severity", color_discrete_map=color_map,
        hole=0.35,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(
        height=340, margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="'Segoe UI', sans-serif"),
        title_font_size=14,
    )
    return fig


def plot_threat_types(findings: list[dict]):
    if not findings:
        return None
    df = pd.DataFrame(findings)
    counts = df["rule_name"].value_counts().head(10).reset_index()
    counts.columns = ["Rule", "Count"]
    fig = px.bar(
        counts, x="Count", y="Rule", orientation="h",
        title="Top 10 Threat Types",
        color_discrete_sequence=["#2563eb"],
    )
    fig.update_layout(
        height=340, yaxis=dict(autorange="reversed"),
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="white", plot_bgcolor="#f8fafc",
        font=dict(family="'Segoe UI', sans-serif"),
        title_font_size=14,
    )
    return fig


def plot_timeline(findings: list[dict]):
    ts_findings = [f for f in findings if f.get("timestamp") is not None]
    if not ts_findings:
        return None
    df = pd.DataFrame(ts_findings)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
    if df.empty:
        return None
    df["hour"] = df["timestamp"].dt.floor("h")
    counts = df.groupby(["hour", "severity"]).size().reset_index(name="count")
    fig = px.line(
        counts, x="hour", y="count", color="severity",
        title="Threat Timeline",
        color_discrete_map=SEVERITY_COLORS,
        markers=True,
    )
    fig.update_layout(
        height=300, margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="white", plot_bgcolor="#f8fafc",
        font=dict(family="'Segoe UI', sans-serif"),
        title_font_size=14,
    )
    return fig


def plot_top_sources(findings: list[dict]):
    ips = [f["source_ip"] for f in findings if f.get("source_ip")]
    if not ips:
        return None
    s = pd.Series(ips).value_counts().head(10).reset_index()
    s.columns = ["IP Address", "Count"]
    fig = px.bar(
        s, x="Count", y="IP Address", orientation="h",
        title="Top Attack Sources",
        color_discrete_sequence=["#dc2626"],
    )
    fig.update_layout(
        height=320, yaxis=dict(autorange="reversed"),
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="white", plot_bgcolor="#f8fafc",
        font=dict(family="'Segoe UI', sans-serif"),
        title_font_size=14,
    )
    return fig


# ── Findings table ────────────────────────────────────────────────────────────

def show_findings_table(findings: list[dict], max_rows: int = 200):
    if not findings:
        st.info("No threats detected.")
        return

    rows = []
    for f in findings[:max_rows]:
        ts = f.get("timestamp")
        rows.append({
            "Severity":    f.get("severity", ""),
            "Rule":        f.get("rule_name", ""),
            "Source IP":   f.get("source_ip") or "N/A",
            "Username":    f.get("username") or "N/A",
            "Timestamp":   safe_ts_str(ts),
            "Line #":      f.get("line_num") or "",
            "Description": f.get("description", "")[:120],
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, height=420, hide_index=True)
