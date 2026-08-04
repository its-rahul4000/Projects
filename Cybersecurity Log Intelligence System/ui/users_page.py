import streamlit as st
import pandas as pd

from auth.access_control import require_admin
from services.user_service import get_all_users, set_user_active, delete_user
from services.audit_service import get_app_mappings_by_user
from config.settings import ROLE_ADMIN


def render_users_page(user, db):
    require_admin()

    st.markdown(
        '<div class="page-header">'
        '<div class="page-title">User Management</div>'
        '<div class="page-subtitle">Manage IT Owner accounts</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    users = get_all_users(db)
    it_owners = [u for u in users if u.role != ROLE_ADMIN]
    # One IT Owner can own several applications, so each user maps to a list of
    # (Application/Product, LeanIX/PIF ID) pairs, derived from their analysis history.
    mappings_by_user = get_app_mappings_by_user(db)

    # ── Overview ────────────────────────────────────────────────────────────────
    total_apps = sum(len(mappings_by_user.get(u.id, [])) for u in it_owners)
    active_count = sum(1 for u in it_owners if u.is_active)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("IT Owners", len(it_owners))
    m2.metric("Active", active_count)
    m3.metric("Disabled", len(it_owners) - active_count)
    m4.metric("Applications", total_apps)

    st.divider()

    if not it_owners:
        st.markdown('<div class="info-box">No IT Owner accounts yet.</div>', unsafe_allow_html=True)
        return

    # ── Filter (by username, email, or application/LeanIX) ──────────────────────
    q = st.text_input(
        "Filter users",
        placeholder="🔍  Find by username, email, application, or LeanIX / PIF ID…",
        label_visibility="collapsed", key="user_filter",
    ).strip().lower()
    st.button("✕", key="user_filter_clear",
              on_click=lambda: st.session_state.update({"user_filter": ""}),
              help="Clear search")

    def _matches(u):
        if not q:
            return True
        hay = [u.username, u.email]
        hay += [f"{app} {leanix}" for app, leanix in mappings_by_user.get(u.id, [])]
        return any(q in str(h).lower() for h in hay)

    shown = [u for u in it_owners if _matches(u)]
    st.caption(f"Showing {len(shown)} of {len(it_owners)} IT Owner(s).")
    if not shown:
        return

    # ── One expandable card per IT Owner (apps + management together) ────────────
    for u in shown:
        maps = mappings_by_user.get(u.id, [])
        status = "Active" if u.is_active else "Disabled"
        dot = "🟢" if u.is_active else "🔴"
        label = f"{dot}  {u.username}   ·   {status}   ·   {len(maps)} application(s)"
        with st.expander(label, expanded=False):
            _render_user_card(u, maps, db, actor=user)


def _render_user_card(u, maps, db, actor):
    status = "Active" if u.is_active else "Disabled"
    status_color = "#16a34a" if u.is_active else "#dc2626"
    created_str = u.created_at.strftime("%d-%m-%Y") if u.created_at else "N/A"
    login_str = u.last_login.strftime("%d-%m-%Y %H:%M") if u.last_login else "Never"

    # ── Account details ─────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="font-size:0.9rem;color:#374151;line-height:1.9;">'
        f'<strong>Email:</strong> {u.email}<br>'
        f'<strong>Status:</strong> <span style="color:{status_color};font-weight:600;">{status}</span>'
        f'&nbsp;&nbsp;·&nbsp;&nbsp;<strong>Password:</strong> {u.password_type.title()}<br>'
        f'<strong>Created:</strong> {created_str}'
        f'&nbsp;&nbsp;·&nbsp;&nbsp;<strong>Last login:</strong> {login_str}'
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Applications owned by this user (Application/Product ↔ LeanIX / PIF ID) ──
    st.markdown(
        '<div style="font-weight:600;color:#1e3a5f;margin:14px 0 4px;">'
        "Applications &amp; LeanIX / PIF IDs owned</div>",
        unsafe_allow_html=True,
    )
    if maps:
        map_df = pd.DataFrame(
            [{"Application / Product": app, "LeanIX ID / PIF ID": leanix or "—"}
             for app, leanix in maps]
        )
        st.dataframe(map_df, width='stretch', hide_index=True)
    else:
        st.caption("No applications recorded yet — captured automatically when this user runs a log analysis.")

    # ── Management actions ───────────────────────────────────────────────────────
    a1, a2, _ = st.columns([1, 1, 2])
    with a1:
        if u.is_active:
            if st.button("Deactivate", width='stretch', key=f"deact_{u.id}"):
                if set_user_active(u.id, False, db, actor_id=actor.id):
                    st.rerun()
        else:
            if st.button("Activate", width='stretch', type="primary", key=f"act_{u.id}"):
                if set_user_active(u.id, True, db, actor_id=actor.id):
                    st.rerun()
    with a2:
        if st.button("Delete Account", width='stretch', key=f"del_{u.id}"):
            st.session_state["confirm_delete_user"] = u.id

    if st.session_state.get("confirm_delete_user") == u.id:
        st.markdown(
            f'<div class="warn-box"><strong>Warning:</strong> Permanently delete '
            f"<strong>{u.username}</strong>? This cannot be undone.</div>",
            unsafe_allow_html=True,
        )
        d1, d2 = st.columns(2)
        with d1:
            if st.button("Confirm Delete", type="primary", width='stretch', key=f"confdel_{u.id}"):
                ok, msg = delete_user(u.id, db, actor_id=actor.id)
                st.session_state.pop("confirm_delete_user", None)
                (st.success if ok else st.error)(msg)
                st.rerun()
        with d2:
            if st.button("Cancel", width='stretch', key=f"canceldel_{u.id}"):
                st.session_state.pop("confirm_delete_user", None)
                st.rerun()
