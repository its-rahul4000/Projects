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
            else:
                from ui.login_page import render_login_page
                render_login_page(db)
            return

        # ── Authenticated ────────────────────────────────────────────────────
        st.session_state["current_user"] = current_user
        st.session_state["current_user_id"] = current_user.id

        page = st.session_state.get("page", "dashboard")

        # Change-password page: minimal chrome, no nav
        if page == "change_password":
            set_page_style()
            from ui.login_page import render_change_password_page
            st.markdown(
                f'<div style="max-width:480px;margin:60px auto;">'
                f'<div style="text-align:center;font-size:2rem;margin-bottom:8px;">🛡️</div>'
                f'<div style="text-align:center;font-size:1.2rem;font-weight:700;color:#1e3a5f;margin-bottom:24px;">'
                f'{APP_NAME}</div>',
                unsafe_allow_html=True,
            )
            render_change_password_page(current_user, db)
            st.markdown("</div>", unsafe_allow_html=True)
            return

        # All authenticated pages get the top nav
        render_top_nav(current_user)
        st.markdown('<div style="padding: 24px 28px;">', unsafe_allow_html=True)

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

        else:
            st.session_state["page"] = "dashboard"
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

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
