import streamlit as st
from config.settings import ROLE_ADMIN, ROLE_IT_OWNER
from database.models import User


def get_current_user() -> "User | None":
    return st.session_state.get("current_user")


def is_admin() -> bool:
    user = get_current_user()
    return user is not None and user.role == ROLE_ADMIN


def is_it_owner() -> bool:
    user = get_current_user()
    return user is not None and user.role == ROLE_IT_OWNER


def require_authenticated() -> "User":
    """Return the current user or redirect to login if not authenticated."""
    user = get_current_user()
    if user is None:
        st.session_state["page"] = "login"
        st.rerun()
    return user


def require_admin() -> "User":
    """Return the current user or redirect with error if not admin."""
    user = require_authenticated()
    if user.role != ROLE_ADMIN:
        st.error("Administrator access required.")
        st.stop()
    return user
