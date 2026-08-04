import streamlit as st
import pandas as pd

from auth.access_control import require_admin
from services.audit_service import get_audit_logs
from database.models import User
from config.settings import now_ist


def render_audit_page(user, db):
    require_admin()

    st.markdown(
        '<div class="page-header">'
        '<div class="page-title">Audit Logs</div>'
        '<div class="page-subtitle">Security-sensitive action trail — retained for 180 days</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Time window + free-text search ──────────────────────────────────────────
    with st.container(border=True):
        c1, c2 = st.columns([1, 4])
        with c1:
            days_back = st.number_input("Days back", min_value=1, max_value=180, value=30)
        with c2:
            search = st.text_input(
                "Search",
                placeholder="🔍  Find anything — user, action, application, LeanIX / PIF ID, IP, file, details…",
                key="audit_search",
            ).strip().lower()
            st.button("✕", key="audit_search_clear",
                      on_click=lambda: st.session_state.update({"audit_search": ""}),
                      help="Clear search")

    import datetime
    start_date = now_ist() - datetime.timedelta(days=int(days_back))

    users = db.query(User).order_by(User.username).all()
    user_map = {u.id: u.username for u in users}

    logs = get_audit_logs(db=db, start_date=start_date, limit=1000)

    rows = []
    for log in logs:
        ts_str = log.timestamp.strftime("%d-%m-%Y %H:%M:%S IST") if log.timestamp else "N/A"
        rows.append({
            "Timestamp (IST)":     ts_str,
            "User":                user_map.get(log.user_id, f"ID:{log.user_id}"),
            "Application/Product": log.application or "-",
            "LeanIX ID / PIF ID":  log.leanix_id or "-",
            "Action":              log.action,
            "File":                log.file_name or "",
            "IP Address":          log.ip_address or "",
            "Details":             (log.details or "")[:120],
        })

    # Free-text search across every column shown in the table below.
    if search:
        rows = [r for r in rows if any(search in str(v).lower() for v in r.values())]

    if not rows:
        st.markdown(
            '<div class="info-box">No audit log entries match.</div>',
            unsafe_allow_html=True,
        )
        return

    st.caption(f"Showing **{len(rows)}** entries (most recent first).")

    df = pd.DataFrame(rows)
    st.dataframe(df, width='stretch', height=500, hide_index=True)

    st.download_button(
        "Export as CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"audit_logs_{now_ist().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        width='stretch',
    )
