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
        "append_mode": False,
        "db_initialized": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _bootstrap_db():
    if not st.session_state.get("db_initialized"):
        from database.init_db import init_db
        init_db()
        st.session_state["db_initialized"] = True


def main():
    _init_session_defaults()
    _bootstrap_db()

    from database.db import get_db
    from auth.session_manager import validate_and_refresh
    from ui.components import set_page_style, render_top_nav
    from config.settings import ROLE_ADMIN

    set_page_style()
    db = get_db()

    try:
        current_user = validate_and_refresh(db)

        # ── Unauthenticated routes ──────────────────────────────────────────
        if current_user is None:
            page = st.session_state.get("page", "login")
            if page == "register":
                from ui.register_page import render_register_page
                render_register_page(db)
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

        if page == "dashboard":
            from ui.dashboard_page import render_dashboard
            render_dashboard(current_user, db)

        elif page == "upload":
            from ui.upload_page import render_upload_page
            render_upload_page(current_user, db)

        elif page == "results":
            from ui.results_page import render_results_page
            render_results_page(current_user, db)

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
