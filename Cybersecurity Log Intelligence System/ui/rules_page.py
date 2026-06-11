import streamlit as st
import datetime
import pandas as pd

from database.models import DetectionRule
from auth.access_control import is_admin
from utils.validators import sanitize_text, validate_rule_condition
from services.audit_service import log_action, ACTION_RULE_CREATE, ACTION_RULE_UPDATE, ACTION_RULE_DELETE, ACTION_RULE_TOGGLE


def render_rules_page(user, db):
    admin = is_admin()

    if admin:
        st.markdown(
            '<div class="page-header">'
            '<div class="page-title">Threat Detection Rules</div>'
            '<div class="page-subtitle">Create, edit, enable/disable, and delete detection rules — changes apply immediately</div>'
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="page-header">'
            '<div class="page-title">Detection Rules (Read-Only)</div>'
            '<div class="page-subtitle">Active threat detection rules configured by the Administrator</div>'
            "</div>",
            unsafe_allow_html=True,
        )

    tab_static, tab_dynamic = st.tabs(["Static Rules (Regex)", "Dynamic Rules (Threshold)"])

    with tab_static:
        _show_rules_section(db, user, admin, is_static=True)

    with tab_dynamic:
        _show_rules_section(db, user, admin, is_static=False)

    if admin:
        st.divider()
        st.subheader("Add New Rule")
        _show_add_rule_form(db, user)


_SEV_ICON = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢", "INFO": "🔵"}


def _show_rules_section(db, user, admin: bool, is_static: bool):
    label = "Static" if is_static else "Dynamic"
    rules = (
        db.query(DetectionRule)
        .filter_by(is_static=is_static)
        .order_by(DetectionRule.severity.desc(), DetectionRule.rule_name)
        .all()
    )

    if not rules:
        st.markdown(
            f'<div class="info-box">No {label.lower()} rules configured.</div>',
            unsafe_allow_html=True,
        )
        return

    enabled_count  = sum(1 for r in rules if r.is_enabled)
    disabled_count = len(rules) - enabled_count
    st.caption(
        f"{len(rules)} {label.lower()} rules &nbsp;·&nbsp; "
        f"**{enabled_count}** enabled &nbsp;·&nbsp; {disabled_count} disabled"
    )

    for rule in rules:
        icon    = _SEV_ICON.get(rule.severity, "⚪")
        enabled = "✅ Enabled" if rule.is_enabled else "❌ Disabled"
        header  = f"{icon} **{rule.rule_name}** — {rule.severity} — {enabled}"

        with st.expander(header, expanded=False):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Description:** {rule.description or 'N/A'}")
                if admin:
                    st.code(rule.condition, language="text")
                if not rule.is_static and rule.default_threshold is not None:
                    st.markdown(
                        f"**Threshold:** `{rule.default_threshold}` &nbsp;·&nbsp; "
                        f"**Time Window:** `{rule.time_window_seconds or 0}s`"
                    )
                updated = rule.updated_at
                updated_str = updated.strftime("%Y-%m-%d %H:%M") if updated else "N/A"
                st.caption(f"Rule ID: {rule.id} &nbsp;·&nbsp; Last updated: {updated_str}")

            if admin:
                with col2:
                    _admin_rule_controls(rule, db, user)


def _admin_rule_controls(rule: DetectionRule, db, user):
    kp = f"rule_{rule.id}"

    if st.button(
        "Disable" if rule.is_enabled else "Enable",
        key=f"{kp}_toggle",
        use_container_width=True,
        type="secondary" if rule.is_enabled else "primary",
    ):
        rule.is_enabled = not rule.is_enabled
        rule.updated_at = datetime.datetime.utcnow()
        db.commit()
        log_action(
            user.id, ACTION_RULE_TOGGLE, db,
            details=f"Rule '{rule.rule_name}' {'enabled' if rule.is_enabled else 'disabled'}.",
        )
        st.rerun()

    if st.button("Edit", key=f"{kp}_edit", use_container_width=True):
        st.session_state["editing_rule_id"] = rule.id
        st.rerun()

    if st.button("Delete", key=f"{kp}_delete", use_container_width=True):
        st.session_state[f"confirm_delete_{rule.id}"] = True

    if st.session_state.pop(f"confirm_delete_{rule.id}", False):
        db.delete(rule)
        db.commit()
        log_action(user.id, ACTION_RULE_DELETE, db, details=f"Rule '{rule.rule_name}' deleted.")
        st.success(f"Rule '{rule.rule_name}' deleted.")
        st.rerun()

    if st.session_state.get("editing_rule_id") == rule.id:
        _show_edit_form(rule, db, user)


def _show_edit_form(rule: DetectionRule, db, user):
    st.markdown("---")
    st.markdown("**Edit Rule**")
    with st.form(f"edit_rule_{rule.id}"):
        new_desc  = st.text_area("Description", value=rule.description or "", max_chars=500)
        new_cond  = st.text_area("Condition (regex or metric key)", value=rule.condition, height=80)
        sev_opts  = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
        new_sev   = st.selectbox("Severity", sev_opts, index=sev_opts.index(rule.severity))
        new_thresh = None
        new_window = None
        if not rule.is_static:
            new_thresh = st.number_input("Threshold", min_value=1, max_value=100000,
                                          value=rule.default_threshold or 5)
            new_window = st.number_input("Time Window (seconds)", min_value=0, max_value=86400,
                                          value=rule.time_window_seconds or 300)
        col_save, col_cancel = st.columns(2)
        save   = col_save.form_submit_button("Save Changes", type="primary")
        cancel = col_cancel.form_submit_button("Cancel")

    if save:
        valid_cond, err = validate_rule_condition(new_cond)
        if not valid_cond:
            st.error(err)
        else:
            rule.description = sanitize_text(new_desc, 500)
            rule.condition   = new_cond
            rule.severity    = new_sev
            if new_thresh is not None:
                rule.default_threshold  = int(new_thresh)
                rule.time_window_seconds = int(new_window)
            rule.updated_at = datetime.datetime.utcnow()
            db.commit()
            log_action(user.id, ACTION_RULE_UPDATE, db, details=f"Rule '{rule.rule_name}' updated.")
            st.session_state.pop("editing_rule_id", None)
            st.success("Rule updated successfully.")
            st.rerun()

    if cancel:
        st.session_state.pop("editing_rule_id", None)
        st.rerun()


def _show_add_rule_form(db, user):
    with st.container(border=True):
        with st.form("add_rule_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                rule_name = st.text_input("Rule Name *", max_chars=150)
                rule_type = st.selectbox("Rule Type", ["static", "dynamic"])
            with col_b:
                severity    = st.selectbox("Severity *", ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"])
                description = st.text_input("Description", max_chars=500)

            is_static = rule_type == "static"
            condition = st.text_area(
                "Condition *",
                placeholder="Regex pattern (static) or metric key (dynamic, e.g. brute_force)",
                height=70,
            )

            threshold = None
            window    = None
            if not is_static:
                col_t, col_w = st.columns(2)
                with col_t:
                    threshold = st.number_input("Threshold *", min_value=1, max_value=100000, value=5)
                with col_w:
                    window = st.number_input("Time Window (sec) *", min_value=0, max_value=86400, value=300)

            submitted = st.form_submit_button("Add Rule", type="primary", use_container_width=True)

    if submitted:
        if not rule_name.strip() or not condition.strip():
            st.error("Rule name and condition are required.")
            return
        valid_cond, err = validate_rule_condition(condition)
        if not valid_cond:
            st.error(err)
            return
        if db.query(DetectionRule).filter_by(rule_name=rule_name.strip()).first():
            st.error("A rule with this name already exists.")
            return

        new_rule = DetectionRule(
            rule_name=sanitize_text(rule_name.strip(), 150),
            rule_type=rule_type,
            condition=condition.strip(),
            severity=severity,
            description=sanitize_text(description, 500),
            is_static=is_static,
            default_threshold=int(threshold) if threshold else None,
            time_window_seconds=int(window) if window else None,
            is_enabled=True,
            created_by=user.id,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
        db.add(new_rule)
        db.commit()
        log_action(user.id, ACTION_RULE_CREATE, db, details=f"Created rule: {rule_name}")
        st.success(f"Rule **{rule_name}** created and is now active.")
        st.rerun()
