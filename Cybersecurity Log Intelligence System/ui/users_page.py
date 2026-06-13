import streamlit as st
import pandas as pd

from auth.access_control import require_admin
from services.user_service import get_all_users, set_user_active, delete_user
from config.settings import ROLE_ADMIN


def render_users_page(user, db):
    require_admin()

    st.markdown(
        '<div class="page-header">'
        '<div class="page-title">User Management</div>'
        '<div class="page-subtitle">Manage IT Owner accounts — the Administrator account cannot be modified here</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    users = get_all_users(db)

    if not users:
        st.markdown('<div class="info-box">No users found.</div>', unsafe_allow_html=True)
        return

    # ── Users table ────────────────────────────────────────────────────────────
    rows = []
    for u in users:
        created_str = u.created_at.strftime("%Y-%m-%d") if u.created_at else "N/A"
        login_str   = u.last_login.strftime("%Y-%m-%d %H:%M") if u.last_login else "Never"
        rows.append({
            "ID":         u.id,
            "Username":   u.username,
            "Email":      u.email,
            "Role":       u.role.replace("_", " ").title(),
            "Status":     "Active" if u.is_active else "Disabled",
            "Password":   u.password_type.title(),
            "Created":    created_str,
            "Last Login": login_str,
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, width='stretch', hide_index=True, height=280)

    st.divider()

    # ── Account actions ────────────────────────────────────────────────────────
    st.subheader("Manage Account")

    it_owners = [u for u in users if u.role != ROLE_ADMIN]
    if not it_owners:
        st.markdown(
            '<div class="info-box">No IT Owner accounts to manage.</div>',
            unsafe_allow_html=True,
        )
        return

    selected_name = st.selectbox(
        "Select IT Owner",
        options=[u.username for u in it_owners],
        key="user_mgmt_select",
    )
    sel = next((u for u in it_owners if u.username == selected_name), None)
    if sel is None:
        return

    status_color = "#16a34a" if sel.is_active else "#dc2626"
    st.markdown(
        f'<div class="section-card" style="padding:16px 20px;">'
        f"<strong>{sel.username}</strong> &nbsp;·&nbsp; {sel.email} &nbsp;·&nbsp; "
        f'<span style="color:{status_color};font-weight:600;">'
        f'{"Active" if sel.is_active else "Disabled"}</span>'
        f'<br><span style="font-size:0.82rem;color:#718096;">'
        f'Password: {sel.password_type.title()}'
        f'</span></div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if sel.is_active:
            if st.button("Deactivate", width='stretch', key="deact_btn"):
                ok = set_user_active(sel.id, False, db, actor_id=user.id)
                if ok:
                    st.success(f"'{sel.username}' deactivated.")
                    st.rerun()
        else:
            if st.button("Activate", width='stretch', type="primary", key="act_btn"):
                ok = set_user_active(sel.id, True, db, actor_id=user.id)
                if ok:
                    st.success(f"'{sel.username}' activated.")
                    st.rerun()

    with col2:
        if st.button("Delete Account", width='stretch', key="del_btn"):
            st.session_state["confirm_delete_user"] = sel.id

    if st.session_state.get("confirm_delete_user") == sel.id:
        st.markdown(
            f'<div class="warn-box">'
            f"<strong>Warning:</strong> Permanently delete <strong>{sel.username}</strong>? "
            f"This cannot be undone."
            f"</div>",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm Delete", type="primary", width='stretch', key="conf_del"):
                ok, msg = delete_user(sel.id, db, actor_id=user.id)
                st.session_state.pop("confirm_delete_user", None)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
                st.rerun()
        with c2:
            if st.button("Cancel", width='stretch', key="cancel_del"):
                st.session_state.pop("confirm_delete_user", None)
                st.rerun()
