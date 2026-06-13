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

    # ── Filters ────────────────────────────────────────────────────────────────
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        users = db.query(User).order_by(User.username).all()

        with col1:
            user_opts = ["All"] + [u.username for u in users]
            sel_user  = st.selectbox("Filter by User", user_opts, key="audit_user")
        with col2:
            action_opts = [
                "All", "LOGIN", "LOGIN_FAILED", "LOGOUT", "REGISTER",
                "PASSWORD_CHANGE", "PASSWORD_EXPIRED_CHANGE",
                "FORGOT_PASSWORD", "ADMIN_SETUP",
                "LOG_ANALYZE", "EMAIL_REPORT", "DOWNLOAD_REPORT",
                "RULE_CREATE", "RULE_UPDATE", "RULE_DELETE", "RULE_TOGGLE",
                "USER_CREATE", "USER_DEACTIVATE", "USER_ACTIVATE", "USER_DELETE",
                "SESSION_EXPIRE",
            ]
            sel_action = st.selectbox("Filter by Action", action_opts, key="audit_action")
        with col3:
            days_back = st.number_input("Days back", min_value=1, max_value=180, value=30)

    filter_user_id = None
    if sel_user != "All":
        u = next((x for x in users if x.username == sel_user), None)
        filter_user_id = u.id if u else None

    import datetime
    filter_action = None if sel_action == "All" else sel_action
    start_date    = now_ist() - datetime.timedelta(days=int(days_back))

    logs = get_audit_logs(
        db=db,
        user_id=filter_user_id,
        action_filter=filter_action,
        start_date=start_date,
        limit=1000,
    )

    if not logs:
        st.markdown(
            '<div class="info-box">No audit log entries match the current filters.</div>',
            unsafe_allow_html=True,
        )
        return

    st.caption(f"Showing **{len(logs)}** entries (most recent first).")

    user_map = {u.id: u.username for u in users}
    rows = []
    for log in logs:
        ts_str = log.timestamp.strftime("%Y-%m-%d %H:%M:%S IST") if log.timestamp else "N/A"
        rows.append({
            "Timestamp (IST)": ts_str,
            "User":            user_map.get(log.user_id, f"ID:{log.user_id}"),
            "Action":          log.action,
            "File":            log.file_name or "",
            "Append":          "Yes" if log.append_used else ("" if log.append_used is None else "No"),
            "IP Address":      log.ip_address or "",
            "Details":         (log.details or "")[:120],
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, width='stretch', height=500, hide_index=True)

    st.download_button(
        "Export as CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"audit_logs_{now_ist().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        width='stretch',
    )
