import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from config.settings import APP_NAME, ROLE_ADMIN, ROLE_IT_OWNER, SEVERITY_COLORS

# ── Chart palette (light-mode friendly) ──────────────────────────────────────
_CHART_BG   = "rgba(255,255,255,0)"
_CHART_GRID = "rgba(0,0,0,0.06)"
_ACCENT     = "#1a73e8"

# ── CSS ───────────────────────────────────────────────────────────────────────
_CSS = """
<style>
/* ===== Remove ALL Streamlit chrome ===== */
#MainMenu,
footer,
[data-testid="stDeployButton"],
[data-testid="stToolbar"],
.stDeployButton,
.viewerBadge_container__1QSob,
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
section[data-testid="stSidebarNav"] {
    display: none !important;
}
header[data-testid="stHeader"],
[data-testid="stDecoration"] {
    display: none !important;
    height: 0 !important;
}

/* ===== Prevent horizontal overflow (page must fit the window) ===== */
html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
    overflow-x: hidden !important;
    max-width: 100vw !important;
}
[data-testid="stMain"],
[data-testid="stAppViewContainer"] > section {
    padding-top: 0 !important;
}
* { box-sizing: border-box; }

/* ===== Brand header ===== */
.brand-header {
    background: rgba(255, 255, 255, 0.88);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid rgba(0,0,0,0.08);
    box-shadow: 0 1px 8px rgba(0,0,0,0.07);
    padding: 10px 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 9999;
}
.brand-left {
    display: flex;
    align-items: flex-start;
    gap: 10px;
}
.brand-icon { font-size: 1.55rem; margin-top: 2px; }
.brand-info { display: flex; flex-direction: column; }
.brand-name {
    font-size: 1.05rem;
    font-weight: 700;
    color: #111827;
    letter-spacing: 0.01em;
    line-height: 1.3;
}
.brand-dear {
    font-size: 0.8rem;
    color: #6b7280;
    font-style: italic;
    line-height: 1.3;
}
.brand-nav {
    display: flex;
    align-items: center;
    gap: 4px;
}
.brand-nav a {
    color: #374151 !important;
    text-decoration: none !important;
    font-size: 0.88rem;
    font-weight: 500;
    padding: 5px 12px;
    border-radius: 6px;
    transition: background 0.18s, color 0.18s;
    cursor: pointer;
}
.brand-nav a:hover {
    background: rgba(229,57,53,0.08);
    color: #e53935 !important;
}
.brand-nav a.active {
    color: #e53935 !important;
    font-weight: 700;
}

/* ===== All buttons — default (content area) ===== */
.stButton > button {
    background: #ffffff !important;
    color: #374151 !important;
    border: 1px solid #d1d5db !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    transition: all 0.18s ease !important;
    box-shadow: none !important;
}
.stButton > button:hover {
    background: #f9fafb !important;
    border-color: #9ca3af !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1) !important;
    transform: none !important;
}
.stButton > button[kind="primary"] {
    background: #e53935 !important;
    color: #ffffff !important;
    border: none !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(229,57,53,0.25) !important;
}
.stButton > button[kind="primary"]:hover {
    background: #c62828 !important;
    box-shadow: 0 4px 14px rgba(229,57,53,0.38) !important;
    transform: translateY(-1px) !important;
}
/* Tertiary = link-style (e.g. Forgot Password) */
.stButton > button[kind="tertiary"] {
    background: transparent !important;
    border: none !important;
    color: #e53935 !important;
    box-shadow: none !important;
    font-weight: 600 !important;
    padding: 4px 6px !important;
}
.stButton > button[kind="tertiary"]:hover {
    background: transparent !important;
    color: #c62828 !important;
    text-decoration: underline !important;
    transform: none !important;
}

/* ===== Top nav bar — full-bleed header, flush to the very top ===== */
/* Collapse injected <style> containers and the marker so nothing sits above the bar */
.element-container:has(style),
.element-container:has(.nav-marker) {
    display: none !important;
}
/* The columns row right after the marker becomes a full-width white header bar */
.element-container:has(.nav-marker) + div {
    background: #ffffff;
    border: none;
    border-bottom: 1px solid rgba(0,0,0,0.08);
    border-radius: 0;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    padding: 8px 10px !important;
    width: 100vw !important;
    max-width: 100vw !important;
    margin-left: calc(50% - 50vw) !important;
    margin-right: calc(50% - 50vw) !important;
    margin-top: 0 !important;
    margin-bottom: -14px !important;
    align-items: center;
}
/* Targets only buttons rendered directly after the .nav-marker span */
.element-container:has(.nav-marker) + div .stButton > button {
    background: transparent !important;
    color: #374151 !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    padding: 6px 14px !important;
    box-shadow: none !important;
}
.element-container:has(.nav-marker) + div .stButton > button:hover {
    color: #e53935 !important;
    background: rgba(229,57,53,0.05) !important;
    box-shadow: none !important;
    transform: none !important;
}
.element-container:has(.nav-marker) + div .stButton > button[kind="primary"] {
    color: #e53935 !important;
    border-bottom: 2px solid #e53935 !important;
    font-weight: 700 !important;
    background: transparent !important;
    box-shadow: none !important;
}

/* ===== Download button ===== */
[data-testid="stDownloadButton"] > button {
    background: #e53935 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
[data-testid="stDownloadButton"] > button:hover {
    background: #c62828 !important;
}

/* ===== Block container (Streamlit 1.54 uses stMainBlockContainer) ===== */
[data-testid="stMainBlockContainer"],
[data-testid="stAppViewBlockContainer"],
.main .block-container,
.block-container {
    padding: 0 1rem 2rem 1rem !important;
    max-width: 100% !important;
    width: 100% !important;
    margin: 0 !important;
}

/* ===== Page header ===== */
.page-header   { margin-bottom: 20px; }
.page-title    { font-size: 1.9rem; font-weight: 800; color: #1e3a5f; margin: 0 0 4px; }
.page-subtitle { font-size: 0.88rem; color: #6b7280; margin: 0; }

/* ===== Metric cards ===== */
.metric-row {
    display: flex;
    gap: 12px;
    margin-bottom: 24px;
    flex-wrap: wrap;
}
.metric-card {
    flex: 1;
    min-width: 110px;
    background: #ffffff;
    border-radius: 12px;
    padding: 18px 14px;
    text-align: center;
    border: 1px solid #e5e7eb;
    border-top: 4px solid #e5e7eb;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.metric-card:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.10);
    transform: translateY(-2px);
}
.metric-card.total    { border-top-color: #3b82f6; }
.metric-card.critical { border-top-color: #ef4444; }
.metric-card.high     { border-top-color: #f97316; }
.metric-card.medium   { border-top-color: #f59e0b; }
.metric-card.low      { border-top-color: #22c55e; }
.metric-value {
    font-size: 2.2rem;
    font-weight: 800;
    line-height: 1.1;
    margin: 0;
    color: #111827;
}
.metric-card.total    .metric-value { color: #3b82f6; }
.metric-card.critical .metric-value { color: #ef4444; }
.metric-card.high     .metric-value { color: #f97316; }
.metric-card.medium   .metric-value { color: #f59e0b; }
.metric-card.low      .metric-value { color: #22c55e; }
.metric-label {
    font-size: 0.7rem;
    font-weight: 600;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 6px;
}

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
.sev-critical { background: #fee2e2; color: #dc2626; }
.sev-high     { background: #ffedd5; color: #ea580c; }
.sev-medium   { background: #fef3c7; color: #d97706; }
.sev-low      { background: #dcfce7; color: #16a34a; }
.sev-info     { background: #dbeafe; color: #2563eb; }

/* ===== Info / alert boxes ===== */
.info-box {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 10px;
    padding: 13px 18px;
    margin-bottom: 14px;
    color: #1e40af;
    font-size: 0.9rem;
}
.warn-box {
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-radius: 10px;
    padding: 13px 18px;
    margin-bottom: 14px;
    color: #92400e;
}
.success-box {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 10px;
    padding: 13px 18px;
    margin-bottom: 14px;
    color: #166534;
}
.error-box {
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 10px;
    padding: 13px 18px;
    margin-bottom: 14px;
    color: #991b1b;
}

/* ===== Temp-password box ===== */
.temp-pass-box {
    background: #f0fdf4;
    color: #166534;
    font-family: 'Courier New', Courier, monospace;
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    padding: 14px 20px;
    border-radius: 8px;
    text-align: center;
    margin: 12px 0;
    word-break: break-all;
    border: 1px solid #bbf7d0;
    box-shadow: 0 2px 8px rgba(22,163,74,0.1);
}

/* ===== Login card ===== */
.login-outer {
    min-height: 80vh;
    display: flex;
    align-items: center;
    justify-content: center;
}
.login-card {
    background: transparent;
    border: none;
    border-radius: 20px;
    padding: 20px 6px 6px;
    box-shadow: none;
    width: 100%;
    max-width: 520px;
    margin: 18px auto 6px;
}
.login-logo  { text-align: center; font-size: 3.6rem; margin-bottom: 0; }
.login-title {
    text-align: center;
    font-size: 2.3rem;
    font-weight: 800;
    color: #111827;
    margin: 0;
    letter-spacing: -0.01em;
    line-height: 1.15;
}
.login-sub {
    text-align: center;
    font-size: 0.92rem;
    color: #6b7280;
    margin: 8px 0 24px;
}
.login-divider-text {
    text-align: center;
    color: #6b7280;
    font-size: 0.85rem;
    margin: 18px 0 10px;
}

/* ===== Section cards ===== */
.section-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 22px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    margin-bottom: 18px;
}
.section-title {
    font-size: 1rem;
    font-weight: 700;
    color: #111827;
    margin: 0 0 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid #e5e7eb;
}

/* ===== Stat chips ===== */
.stat-chip {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 14px 22px;
    min-width: 110px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.stat-chip-value { font-size: 1.75rem; font-weight: 800; color: #1a73e8; }
.stat-chip-label {
    font-size: 0.7rem;
    font-weight: 600;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 4px;
}

/* ===== File uploader ===== */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.8) !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 12px !important;
    padding: 14px !important;
}

/* ===== Text inputs ===== */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input {
    background: #eef1f4 !important;
    color: #111827 !important;
    border: 1px solid transparent !important;
    border-radius: 10px !important;
    padding: 11px 14px !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: #e53935 !important;
    box-shadow: 0 0 0 3px rgba(229,57,53,0.12) !important;
}

/* ===== Select / multiselect ===== */
[data-testid="stSelectbox"] > div > div {
    background: #eef1f4 !important;
    border: 1px solid transparent !important;
    border-radius: 10px !important;
}

/* ===== Expander ===== */
[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
}

/* ===== Tabs ===== */
[data-testid="stTabs"] [data-baseweb="tab"] {
    color: #6b7280 !important;
    font-weight: 500 !important;
}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
    color: #e53935 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    background: #e53935 !important;
}

/* ===== Metrics ===== */
[data-testid="stMetric"] {
    background: #ffffff !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 10px !important;
    padding: 14px 18px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important;
}

/* ===== Dataframe ===== */
.stDataFrame {
    border: 1px solid #e5e7eb !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
}

/* ===== Form container ===== */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #e5e7eb !important;
    border-radius: 12px !important;
    background: rgba(255,255,255,0.7) !important;
}

/* ===== Divider ===== */
hr, [data-testid="stDivider"] {
    border-color: #e5e7eb !important;
    margin: 14px 0 !important;
}

/* ===== Recommendation cards ===== */
.rec-panel {
    background: rgba(255,255,255,0.9);
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}
.rec-panel-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #111827;
    margin-bottom: 14px;
}
.rec-card {
    background: #f9fafb;
    border-left: 4px solid #d1d5db;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 10px;
}
.rec-card.sev-critical-card { border-left-color: #ef4444; }
.rec-card.sev-high-card     { border-left-color: #f97316; }
.rec-card.sev-medium-card   { border-left-color: #f59e0b; }
.rec-card.sev-low-card      { border-left-color: #22c55e; }
.rec-rule    { font-size: 0.88rem; font-weight: 700; color: #111827; margin-bottom: 2px; }
.rec-urgency { font-size: 0.7rem; color: #9ca3af; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.05em; }
.rec-action  { font-size: 0.82rem; color: #374151; padding: 2px 0; }
.rec-action::before { content: '→ '; color: #e53935; font-weight: 700; }

/* ===== Rule detail cards ===== */
.rule-why    { background: #fffbeb; border: 1px solid #fde68a; border-radius: 7px; padding: 10px 14px; margin: 6px 0; color: #92400e; font-size: 0.84rem; }
.rule-impact { background: #fef2f2; border: 1px solid #fecaca; border-radius: 7px; padding: 10px 14px; margin: 6px 0; color: #991b1b; font-size: 0.84rem; }
.rule-action { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 7px; padding: 10px 14px; margin: 6px 0; color: #166534; font-size: 0.84rem; }
.rule-example{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 7px; padding: 8px 12px;  margin: 6px 0; font-family: 'Courier New', monospace; font-size: 0.77rem; color: #475569; overflow-x: auto; }
</style>
"""


def set_page_style():
    st.markdown(_CSS, unsafe_allow_html=True)


def severity_badge(severity: str) -> str:
    cls = f"sev-{severity.lower()}"
    return f'<span class="sev-badge {cls}">{severity}</span>'


def safe_ts_str(ts, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
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

    # Build salutation
    display_name = getattr(user, "username", "User")
    salutation = f"Dear {display_name.split('@')[0].replace('_', ' ').title()},"

    if role == ROLE_ADMIN:
        nav = [
            ("dashboard", "Home"),
            ("rules",     "Rules"),
            ("users",     "Users"),
            ("audit",     "Audit"),
            ("settings",  "Settings"),
        ]
    else:
        nav = [
            ("dashboard", "Home"),
            ("rules",     "Rules"),
            ("settings",  "Settings"),
        ]

    # Single-row top bar: brand on the left, nav links on the right.
    # The marker span scopes the white-bar + link-style button CSS to this row.
    st.markdown('<span class="nav-marker"></span>', unsafe_allow_html=True)
    cols = st.columns([3.4] + [1] * (len(nav) + 1), vertical_alignment="center")

    with cols[0]:
        st.markdown(
            f"""<div class="brand-left">
              <span class="brand-icon">🛡️</span>
              <div class="brand-info">
                <span class="brand-name">Cybersecurity Log Intelligence</span>
                <span class="brand-dear">{salutation}</span>
              </div>
            </div>""",
            unsafe_allow_html=True,
        )

    for col, (page, label) in zip(cols[1:], nav):
        with col:
            btn_type = "primary" if current == page else "secondary"
            if st.button(label, key=f"nav_{page}", width='stretch', type=btn_type):
                st.session_state["page"] = page
                st.rerun()
    with cols[-1]:
        if st.button("Logout", key="nav_logout", width='stretch', type="secondary"):
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


# ── Recommendation panel ──────────────────────────────────────────────────────

def show_recommendations_panel(findings: list[dict]):
    from services.recommendations import get_recommendations, get_general_actions
    from services.threat_engine import compute_summary

    summary = compute_summary(findings)
    general = get_general_actions(summary)
    recs = get_recommendations(findings)

    if not recs and not general:
        return

    html = '<div class="rec-panel"><div class="rec-panel-title">Recommended Actions</div>'

    if general:
        highest = next((s for s in ("CRITICAL", "HIGH", "MEDIUM", "LOW") if summary.get(s, 0) > 0), "")
        html += f'<div style="margin-bottom:12px;"><strong style="color:#374151;font-size:.88rem;">Immediate Response — {highest}:</strong></div>'
        html += '<div style="margin-bottom:16px;">'
        for action in general:
            html += f'<div class="rec-action">{action}</div>'
        html += '</div>'

    for rec in recs[:8]:
        sev = rec["severity"].lower()
        html += f'<div class="rec-card sev-{sev}-card">'
        html += f'<div class="rec-rule">{rec["rule_name"]}</div>'
        html += f'<div class="rec-urgency">Urgency: {rec.get("urgency","")}</div>'
        for action in rec["actions"][:3]:
            html += f'<div class="rec-action">{action}</div>'
        html += '</div>'

    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


# ── Charts (light mode) ───────────────────────────────────────────────────────

def _light_layout(**kwargs) -> dict:
    base = dict(
        paper_bgcolor=_CHART_BG,
        plot_bgcolor=_CHART_BG,
        font=dict(color="#374151", family="'Segoe UI', sans-serif"),
        title_font=dict(color="#111827", size=14, family="'Segoe UI', sans-serif"),
        legend=dict(font=dict(color="#374151"), bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    base.update(kwargs)
    return base


def plot_severity_pie(findings: list[dict]):
    if not findings:
        return None
    df = pd.DataFrame(findings)
    counts = df["severity"].value_counts().reset_index()
    counts.columns = ["Severity", "Count"]
    color_map = {
        "CRITICAL": "#ef4444",
        "HIGH":     "#f97316",
        "MEDIUM":   "#f59e0b",
        "LOW":      "#22c55e",
        "INFO":     "#3b82f6",
    }
    fig = px.pie(
        counts, names="Severity", values="Count",
        title="Threat Severity Distribution",
        color="Severity", color_discrete_map=color_map,
        hole=0.38,
    )
    fig.update_traces(
        textposition="inside", textinfo="percent+label",
        textfont=dict(color="white", size=11),
    )
    fig.update_layout(height=340, **_light_layout())
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
        color_discrete_sequence=["#1a73e8"],
    )
    fig.update_layout(
        height=340,
        yaxis=dict(autorange="reversed", gridcolor=_CHART_GRID),
        xaxis=dict(gridcolor=_CHART_GRID),
        **_light_layout(),
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
    color_map = {
        "CRITICAL": "#ef4444",
        "HIGH":     "#f97316",
        "MEDIUM":   "#f59e0b",
        "LOW":      "#22c55e",
        "INFO":     "#3b82f6",
    }
    fig = px.line(
        counts, x="hour", y="count", color="severity",
        title="Threat Timeline",
        color_discrete_map=color_map,
        markers=True,
    )
    fig.update_layout(
        height=300,
        xaxis=dict(gridcolor=_CHART_GRID),
        yaxis=dict(gridcolor=_CHART_GRID),
        **_light_layout(),
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
        color_discrete_sequence=["#e53935"],
    )
    fig.update_layout(
        height=320,
        yaxis=dict(autorange="reversed", gridcolor=_CHART_GRID),
        xaxis=dict(gridcolor=_CHART_GRID),
        **_light_layout(),
    )
    return fig


# ── Findings table ────────────────────────────────────────────────────────────

def show_findings_table(findings: list[dict], max_rows: int = 200):
    if not findings:
        st.info("No threats detected.")
        return

    rows = []
    for f in findings[:max_rows]:
        rows.append({
            "Severity":    f.get("severity", ""),
            "Rule":        f.get("rule_name", ""),
            "Source IP":   f.get("source_ip") or "N/A",
            "Username":    f.get("username") or "N/A",
            "Timestamp":   safe_ts_str(f.get("timestamp")),
            "Line #":      f.get("line_num") or "",
            "Description": f.get("description", "")[:120],
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, width='stretch', height=420, hide_index=True)
