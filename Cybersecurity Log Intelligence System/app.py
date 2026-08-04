import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from config.settings import APP_NAME

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _init_session_defaults():
    defaults = {
        "page": "login",
        "session_token": None,
        "current_user": None,
        "current_user_id": None,
        "analysis_results": None,
        "log_df": None,
        "analyzed_files": [],
        # Files staged for analysis — a plain key so they persist across page navigation
        # (the file_uploader widget itself cannot be re-populated after it unmounts).
        "staged_files": [],
        "db_initialized": False,
        # Application/Product + LeanIX ID/PIF ID captured on Home; gate upload until set.
        "application": "",
        "leanix_id": "",
        # Bumped by "Clear & New Analysis" to mount a fresh, empty file uploader.
        "uploader_nonce": 0,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # Keep the Application/Product + LeanIX/PIF context alive across page navigation.
    # These are bound to text_input widgets on Home; Streamlit drops a widget's value from
    # session_state on runs where the widget isn't rendered (i.e. while the user is on
    # another page). Re-assigning the keys to themselves here (before any widget is
    # instantiated) marks them as user-set state, so they persist until "Clear & New
    # Analysis" clears them.
    for key in ("application", "leanix_id"):
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]


def _bootstrap_db():
    if not st.session_state.get("db_initialized"):
        from database.init_db import init_db
        init_db()
        st.session_state["db_initialized"] = True


def _render_page_body(page, current_user, db):
    """Dispatch to the active page's renderer. Kept as a helper so the page body can be
    wrapped in the keyed cross-fade containers in main() without deep re-indentation."""
    # Upload + analyze + results are now all part of the Home dashboard.
    if page in ("dashboard", "upload", "results"):
        from ui.dashboard_page import render_dashboard
        render_dashboard(current_user, db)
    elif page == "rules":
        from ui.rules_page import render_rules_page
        render_rules_page(current_user, db)
    elif page == "users":
        from ui.users_page import render_users_page
        render_users_page(current_user, db)
    elif page == "audit":
        from ui.audit_page import render_audit_page
        render_audit_page(current_user, db)
    elif page == "settings":
        from ui.settings_page import render_settings_page
        render_settings_page(current_user, db)
    elif page == "change_password":
        from ui.login_page import render_change_password_page
        render_change_password_page(current_user, db)
    else:
        st.session_state["page"] = "dashboard"
        st.rerun()


def main():
    _init_session_defaults()
    _bootstrap_db()

    from database.db import get_db
    from auth.session_manager import validate_and_refresh
    from ui.components import set_page_style, render_top_nav, pin_browser_tab
    from config.settings import ROLE_ADMIN

    set_page_style()
    # Inject the one-time parent-document helpers (favicon/title pin + page-transition
    # hooks) once per run. Both share one keyed container that must be created only once.
    pin_browser_tab()
    db = get_db()

    try:
        current_user = validate_and_refresh(db)

        # ── Unauthenticated routes ──────────────────────────────────────────
        if current_user is None:
            page = st.session_state.get("page", "login")
            if page == "register":
                from ui.register_page import render_register_page
                render_register_page(db)
            elif page == "complete_registration":
                from ui.login_page import render_complete_registration_page
                render_complete_registration_page(db)
            elif page == "forgot_password":
                from ui.login_page import render_forgot_password_page
                render_forgot_password_page(db)
            else:
                from ui.login_page import render_login_page
                render_login_page(db)
            return

        # ── Authenticated ────────────────────────────────────────────────────
        st.session_state["current_user"] = current_user
        st.session_state["current_user_id"] = current_user.id

        page = st.session_state.get("page", "dashboard")

        # Admin first-login: must configure recovery email before anything else
        if (
            page not in ("admin_setup", "change_password")
            and current_user.role == ROLE_ADMIN
            and getattr(current_user, "is_first_login", False)
            and getattr(current_user, "password_type", "") == "permanent"
        ):
            st.session_state["page"] = "admin_setup"
            st.rerun()
            return

        # Admin recovery email setup page (minimal chrome, no nav)
        if page == "admin_setup":
            set_page_style()
            from ui.login_page import render_admin_setup_page
            st.markdown(
                f'<div style="max-width:520px;margin:48px auto;">'
                f'<div style="text-align:center;font-size:2.6rem;margin-bottom:6px;">🛡️</div>'
                f'<div style="text-align:center;font-size:1.4rem;font-weight:800;'
                f'color:#1e3a5f;margin-bottom:24px;">{APP_NAME}</div>',
                unsafe_allow_html=True,
            )
            render_admin_setup_page(current_user, db)
            st.markdown("</div>", unsafe_allow_html=True)
            return

        # Forced password change (first login / expired): minimal chrome, no nav.
        # A voluntary change (IT Owner "Password" link) falls through to the nav layout.
        if page == "change_password" and st.session_state.get("force_change_reason"):
            set_page_style()
            from ui.login_page import render_change_password_page
            st.markdown(
                f'<div style="max-width:480px;margin:48px auto;">'
                f'<div style="text-align:center;font-size:2.6rem;margin-bottom:6px;">🛡️</div>'
                f'<div style="text-align:center;font-size:1.4rem;font-weight:800;'
                f'color:#1e3a5f;margin-bottom:24px;">{APP_NAME}</div>',
                unsafe_allow_html=True,
            )
            render_change_password_page(current_user, db)
            st.markdown("</div>", unsafe_allow_html=True)
            return

        # All authenticated pages get the top nav
        render_top_nav(current_user)

        # Each page body lives in a keyed container (st-key-pagebox_<page>). A page switch
        # changes the key, so Streamlit mounts a fresh node and the incoming page fades in
        # (see the keyed-container CSS in components.py). Streamlit handles tearing down the
        # outgoing page natively — we no longer pin it on screen — so it doesn't bleed onto
        # the new page. The whole Home group shares one key so analysis state changes
        # (dashboard/upload/results) don't re-trigger the fade.
        page_key = "home" if page in ("dashboard", "upload", "results") else page
        with st.container(key=f"pagebox_{page_key}"):
            _render_page_body(page, current_user, db)

    except Exception as exc:
        st.error(f"An unexpected error occurred: {exc}")
        import logging
        logging.getLogger(__name__).exception("Unhandled error in main()")
    finally:
        db.close()


if __name__ == "__main__":
    main()
else:
    main()
