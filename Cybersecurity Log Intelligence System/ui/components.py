import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from html import escape as _esc
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

/* ===== Page navigation, step 1 of 2: cover only the LOAD with a white sheet ===== */
/* Streamlit keeps the PREVIOUS page on screen (dimmed + marked stale) while it renders
   the next one, so on data-heavy pages the old page used to bleed through. The instant a
   nav button for a DIFFERENT page is clicked, the parent-doc hook (see _NAV_TRANSITION_JS)
   adds `app-navigating` to <body>, which (a) paints the content area clean WHITE so the
   load is hidden under a sheet (not the teal app bg), and (b) hides the OUTGOING page so
   nothing stale shows. This lasts ONLY the real load time — the instant the new page is
   ready the sheet is lifted and step 2 cascades the actual CONTENT in. opacity (not
   display) on the hide keeps layout stable.
   CRUCIAL — the hide is scoped to STALE content ([data-stale] = the previous frame), so
   it RELEASES ITSELF once Streamlit finishes the render (nothing is stale). The incoming
   page is fresh, never stale, so it is never hidden — the page can NEVER get stuck blank.
   `app-navigating` is ONLY added on a real page change — the active page, Logout, the
   Home→Home sub-view case, and every same-page rerun (search / filter / sort / expander /
   publish / polling) are all skipped, so those stay instant and never flicker. */
body.app-navigating [data-testid="stMain"] {
    background: #ffffff !important;
}
/* Scoped to the pagebox ELEMENT being stale (the previous frame) — NOT :has(a stale
   descendant). On a heavy, multi-batch render (e.g. the Rules page, whose cards live in
   st.tabs) the INCOMING page momentarily contains a stale descendant mid-render; a
   :has() rule would then hide the whole NEW page → the white sheet covers the cascade,
   intermittently (it only triggers when the render splits across batches). The new
   pagebox element itself is always fresh, so matching the element only ever hides the
   OUTGOING page, and the incoming cascade is never covered. */
body.app-navigating [class*="st-key-pagebox_"][data-stale="true"] {
    opacity: 0 !important;
}

/* ===== Smooth the analysis progress bar ===== */
/* st.progress repaints each new value instantly, so progress jumps. A width
   transition on the fill makes it glide between values, turning every step
   (and the static-rule leap) into a continuous slide. */
[data-testid="stProgress"] div[role="progressbar"] > div,
[data-testid="stProgressBar"] div[role="progressbar"] > div {
    transition: width 0.45s ease-in-out !important;
}

/* ===== Page navigation, step 2 of 2: cascade the CONTENT in, top → bottom ===== */
/* When a page switch mounts the fresh keyed container, the page's top-level blocks fall
   into place one after another from the top — a soft "waterfall" of the ACTUAL content
   (not a curtain). Two pieces:
     • appPageMount is a 0-effect marker animation on the pagebox; its animationstart is
       the signal the parent-doc hook uses to lift the white sheet the instant the page is
       ready, and a timer then disarms the cascade.
     • appCascadeFall is the real effect — each block fades in + slides down, staggered by
       position (nth-child), so the page assembles top→bottom like falling content.
   It is GATED by body.navfx-cascade (added on the nav click, removed ~1.5s after mount),
   so it plays exactly ONCE per real navigation. Same-page reruns never carry the class,
   so an edited rule / new search results / a poll never re-animate the content — no
   flicker. The pagebox key sits on the vertical block's border-wrapper, so the page's
   blocks are its grandchildren (… > stVerticalBlock > *); a second selector also covers
   the key-on-block layout. transform/opacity only — compositor-friendly, never reflow;
   `backwards` holds the hidden first frame so nothing flashes before each block starts. */
@keyframes appPageMount { from { opacity: 1; } to { opacity: 1; } }   /* marker only — fires the mount event */
[class*="st-key-pagebox_"] { animation: appPageMount 0.01s linear; }

@keyframes appCascadeFall {
    from { opacity: 0; transform: translateY(-16px); }
    to   { opacity: 1; transform: translateY(0); }
}
body.navfx-cascade [class*="st-key-pagebox_"] > [data-testid="stVerticalBlock"] > *,
body.navfx-cascade [class*="st-key-pagebox_"][data-testid="stVerticalBlock"] > * {
    animation: appCascadeFall 0.5s cubic-bezier(0.22, 0.61, 0.36, 1) backwards;
    will-change: transform, opacity;
}
/* Stagger each block so they fall in one after another (top → bottom). */
body.navfx-cascade [class*="st-key-pagebox_"] > [data-testid="stVerticalBlock"] > *:nth-child(2)    { animation-delay: .07s; }
body.navfx-cascade [class*="st-key-pagebox_"] > [data-testid="stVerticalBlock"] > *:nth-child(3)    { animation-delay: .14s; }
body.navfx-cascade [class*="st-key-pagebox_"] > [data-testid="stVerticalBlock"] > *:nth-child(4)    { animation-delay: .21s; }
body.navfx-cascade [class*="st-key-pagebox_"] > [data-testid="stVerticalBlock"] > *:nth-child(5)    { animation-delay: .28s; }
body.navfx-cascade [class*="st-key-pagebox_"] > [data-testid="stVerticalBlock"] > *:nth-child(6)    { animation-delay: .35s; }
body.navfx-cascade [class*="st-key-pagebox_"] > [data-testid="stVerticalBlock"] > *:nth-child(7)    { animation-delay: .42s; }
body.navfx-cascade [class*="st-key-pagebox_"] > [data-testid="stVerticalBlock"] > *:nth-child(8)    { animation-delay: .49s; }
body.navfx-cascade [class*="st-key-pagebox_"] > [data-testid="stVerticalBlock"] > *:nth-child(9)    { animation-delay: .56s; }
body.navfx-cascade [class*="st-key-pagebox_"] > [data-testid="stVerticalBlock"] > *:nth-child(n+10) { animation-delay: .63s; }
/* Reduced-motion: no slide/stagger — content just appears (the marker still fires, so the
   white sheet is still lifted on mount). */
@media (prefers-reduced-motion: reduce) {
    [class*="st-key-pagebox_"] { animation-duration: 0.01ms !important; }
    body.navfx-cascade [class*="st-key-pagebox_"] > [data-testid="stVerticalBlock"] > *,
    body.navfx-cascade [class*="st-key-pagebox_"][data-testid="stVerticalBlock"] > * {
        animation: none !important;
    }
}

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
/* Targets only buttons rendered directly after the .nav-marker span — smooth rounded
   "pills" with an attractive hover (tint + subtle lift + soft shadow). */
.element-container:has(.nav-marker) + div .stButton > button {
    background: transparent !important;
    color: #374151 !important;
    border: 1px solid transparent !important;  /* reserve space so the hover border doesn't shift layout */
    border-radius: 4px !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    padding: 7px 16px !important;
    box-shadow: none !important;
    transition: background 0.18s ease, color 0.18s ease, border-color 0.18s ease,
                transform 0.18s ease, box-shadow 0.18s ease !important;
}
/* Hover = outlined look (white fill + red border + red text), matching the rule tabs */
.element-container:has(.nav-marker) + div .stButton > button:hover {
    color: #e53935 !important;
    background: #ffffff !important;
    border-color: #e53935 !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    transform: translateY(-1px) !important;
}
.element-container:has(.nav-marker) + div .stButton > button:active {
    transform: translateY(0) !important;
    box-shadow: 0 1px 4px rgba(229,57,53,0.18) !important;
}
/* Active page = red pill (original brand colour), smooth rounded corners. */
.element-container:has(.nav-marker) + div .stButton > button[kind="primary"] {
    color: #ffffff !important;
    background: #e53935 !important;
    border: none !important;
    border-radius: 4px !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 8px rgba(229,57,53,0.25) !important;
}
.element-container:has(.nav-marker) + div .stButton > button[kind="primary"]:hover {
    color: #ffffff !important;
    background: #c62828 !important;
    box-shadow: 0 4px 14px rgba(229,57,53,0.38) !important;
    transform: translateY(-1px) !important;
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
    margin: -16px 0 0 0 !important;
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
/* Streamlit auto-generates a "Limit <size> per file • <types>" hint in the dropzone.
   In Streamlit 1.54 this hint is a <span> (the LAST span in the instructions' text
   column), NOT a <small>. No upload-size cap is surfaced to the user, so a small script
   (in _GLOBAL_DROP_JS) strips the "Limit <size> per file •" prefix, leaving only the
   accepted file types, and marks the element data-hint-fixed="1". It stays hidden until
   then so the size limit never flashes on screen. */
[data-testid="stFileUploaderDropzoneInstructions"] > div:last-child > span:last-child:not([data-hint-fixed="1"]) {
    visibility: hidden !important;
}

/* ===== Text inputs — ONE bordered box (the outer BaseWeb wrapper) ===== */
/* Only div[data-baseweb="input"] / "textarea" carries the border. The nested
   base-input container and the <input> are transparent & borderless, so password
   fields — which nest an extra container for the reveal-eye icon — don't show a
   second inner box. */
[data-testid="stTextInput"] div[data-baseweb="input"],
[data-testid="stNumberInput"] div[data-baseweb="input"],
[data-testid="stTextArea"] div[data-baseweb="textarea"] {
    background: #eef1f4 !important;
    border: 1px solid #e2e5ea !important;
    border-radius: 4px !important;
    box-shadow: none !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
}
[data-testid="stTextInput"] div[data-baseweb="base-input"],
[data-testid="stNumberInput"] div[data-baseweb="base-input"],
[data-testid="stTextArea"] div[data-baseweb="base-input"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea {
    background: transparent !important;
    color: #111827 !important;
    border: none !important;
    box-shadow: none !important;
    padding: 9px 12px !important;
}
/* One red border + soft glow on focus — applied to the outer wrapper only */
[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within,
[data-testid="stNumberInput"] div[data-baseweb="input"]:focus-within,
[data-testid="stTextArea"] div[data-baseweb="textarea"]:focus-within {
    border-color: #e53935 !important;
    box-shadow: 0 0 0 3px rgba(229,57,53,0.15) !important;
}
/* Drop the "Press Enter to submit form" hint clutter inside inputs */
[data-testid="InputInstructions"] { display: none !important; }

/* Home-page context fields (Application/Product + LeanIX ID/PIF ID): a clearly visible
   grey-border box that stands out above the uploader. A white fill (vs the default light-
   grey input fill) makes the grey border read clearly as a box. Focus still shows the
   shared red glow via the :focus-within rule above. */
.st-key-application div[data-baseweb="input"],
.st-key-leanix_id div[data-baseweb="input"] {
    border: 1.5px solid #9ca3af !important;
    background: #ffffff !important;
    border-radius: 8px !important;
}

/* Users-page filter + Audit-page search boxes: a visible grey border. */
.st-key-user_filter div[data-baseweb="input"],
.st-key-audit_search div[data-baseweb="input"] {
    border: 1.5px solid #9ca3af !important;
    border-radius: 8px !important;
}

/* ===== Search clear (✕): a dark icon overlaid on the full-width search box ===== */
/* The button is lifted up onto the input above it and pinned to the right, so it
   never reserves layout width (the search box stays full width with no gap). */
.st-key-clear_search_btn {
    margin-top: -3rem !important;
    margin-bottom: 0 !important;
    margin-left: auto !important;
    margin-right: 12px !important;
    width: fit-content !important;
    align-self: flex-end !important;
    position: relative;
    z-index: 5;
}
.st-key-clear_search_btn button,
.st-key-clear_search_btn button:focus {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #4b5563 !important;
    font-size: 1rem !important;
    min-height: 0 !important;
    padding: 2px 6px !important;
}
.st-key-clear_search_btn button:hover {
    color: #e53935 !important;
    background: transparent !important;
    transform: none !important;
}
/* The ✕ appears only once the user has typed (placeholder no longer shown). */
.st-key-findings_search:has(input:placeholder-shown) ~ .st-key-clear_search_btn {
    display: none !important;
}

/* ===== Rules-page search clear (✕) — single GLOBAL search box overlay ===== */
.st-key-rules_clear {
    margin-top: -3rem !important;
    margin-bottom: 0 !important;
    margin-left: auto !important;
    margin-right: 12px !important;
    width: fit-content !important;
    align-self: flex-end !important;
    position: relative;
    z-index: 5;
}
.st-key-rules_clear button,
.st-key-rules_clear button:focus {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #4b5563 !important;
    font-size: 1rem !important;
    min-height: 0 !important;
    padding: 2px 6px !important;
}
.st-key-rules_clear button:hover {
    color: #e53935 !important;
    background: transparent !important;
    transform: none !important;
}
.st-key-rules_search:has(input:placeholder-shown) ~ .st-key-rules_clear {
    display: none !important;
}

/* ===== Users-page & Audit-page search clear (✕) — overlay on the search box ===== */
.st-key-user_filter_clear,
.st-key-audit_search_clear {
    margin-top: -3rem !important;
    margin-bottom: 0 !important;
    margin-left: auto !important;
    margin-right: 12px !important;
    width: fit-content !important;
    align-self: flex-end !important;
    position: relative;
    z-index: 5;
}
.st-key-user_filter_clear button,
.st-key-user_filter_clear button:focus,
.st-key-audit_search_clear button,
.st-key-audit_search_clear button:focus {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #4b5563 !important;
    font-size: 1rem !important;
    min-height: 0 !important;
    padding: 2px 6px !important;
}
.st-key-user_filter_clear button:hover,
.st-key-audit_search_clear button:hover {
    color: #e53935 !important;
    background: transparent !important;
    transform: none !important;
}
.st-key-user_filter:has(input:placeholder-shown) ~ .st-key-user_filter_clear,
.st-key-audit_search:has(input:placeholder-shown) ~ .st-key-audit_search_clear {
    display: none !important;
}

/* ===== Rules-page search box + sort dropdown: visible grey border ===== */
.st-key-rules_search div[data-baseweb="input"],
.st-key-rules_sort   div[data-baseweb="select"] > div {
    border: 1px solid #9ca3af !important;
}

/* ===== Rules-page sort dropdown: visible grey border ===== */
.st-key-rules_sort div[data-baseweb="select"] > div {
    border: 1px solid #9ca3af !important;
}

/* ===== Publish-all button: pinned to the RIGHT of the tab strip, yellow = pending (request #13) ===== */
/* Rendered just before st.tabs; right-aligned and lifted onto the tab row's free right
   side using the same margin-left:auto + fit-content overlay pattern as the ✕ button
   (element containers are column flex, so margin-left:auto — NOT justify-content — is
   what pushes it to the right). */
.st-key-publish_all_btn {
    margin-left: auto !important;
    margin-right: 4px !important;
    margin-top: 0 !important;
    margin-bottom: -46px !important;
    width: fit-content !important;
    align-self: flex-end !important;
    position: relative;
    z-index: 10;
}
.st-key-publish_all_btn button,
.st-key-publish_all_btn button[kind="secondary"] {
    width: auto !important;
    background: #f59e0b !important;
    color: #ffffff !important;
    border: none !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 8px rgba(245,158,11,0.30) !important;
}
.st-key-publish_all_btn button:hover {
    background: #d97706 !important;
    color: #ffffff !important;
    box-shadow: 0 4px 14px rgba(245,158,11,0.42) !important;
    transform: translateY(-1px) !important;
}

/* ===== Script-only iframes (favicon-pin) add no vertical space (request #3) ===== */
/* Pull the tab-pin holder out of flow so its 0-height injector iframe never creates a
   margin above the page header — it still renders (display, not none) so its JS runs. */
.st-key-tab_pin_holder {
    position: absolute !important;
    top: 0; left: 0;
    width: 0 !important;
    height: 0 !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
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

/* ===== Rule cards (Rules page) ===== */
/* Each rule is ONE compact bordered card. The expander label is the rule name, so the
   single header row ("▸ Rule name") is itself the clickable toggle — no separate
   "Details" row, which keeps the box short. Status chips are overlaid on the right of
   that header row. Targeted via the container key st-key-rulecard_<severity>_<id> so the
   styling is reliable (no fragile :has). */
[class*="st-key-rulecard_"] {
    border: 1px solid #e5e7eb !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
    background: #ffffff !important;
    margin-bottom: -6px !important;   /* ← GAP BETWEEN BOXES: raise for more space, lower (even negative) for less */
    padding: 0 10px !important;
    gap: 0 !important;               /* ★ no empty band between the chips row and the header */
}
[class*="st-key-rulecard_critical_"] { border-left: 6px solid #ef4444 !important; }
[class*="st-key-rulecard_high_"]     { border-left: 6px solid #f97316 !important; }
[class*="st-key-rulecard_medium_"]   { border-left: 6px solid #f59e0b !important; }
[class*="st-key-rulecard_low_"]      { border-left: 6px solid #22c55e !important; }
[class*="st-key-rulecard_info_"]     { border-left: 6px solid #38bdf8 !important; }
/* The expander inside a rule card is fully flat — no nested box, no shadow, no
   background — so the whole card reads as a single box. */
[class*="st-key-rulecard_"] [data-testid="stExpander"],
[class*="st-key-rulecard_"] [data-testid="stExpander"] > details,
[class*="st-key-rulecard_"] [data-testid="stExpander"] summary {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
}
/* ★ THE FIX — collapse the chips' wrapper element-container (Streamlit's inter-element
   gap above the header). Without this line the box stays TALL no matter what you set
   for padding/line-height, because the empty band lives in this wrapper, not the header. */
[class*="st-key-rulecard_"] [data-testid="stElementContainer"]:has(.rule-chips-overlay) {
    height: 0 !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}
/* Make the expander label (the rule name) read like a card title, vertically centred. */
[class*="st-key-rulecard_"] [data-testid="stExpander"] summary p {
    font-size: 1rem !important;
    color: #111827 !important;
    margin: 0 !important;          /* ← removing the default paragraph spacing is what
                                        actually shrinks the box (padding alone did not) */
    line-height: 3.6 !important;  /* ← LOWER this to make the box even SHORTER */
}
/* Vertically centre the "▸ rule name" row in the box and drop the min-height/padding
   that the expander adds by default. */
[class*="st-key-rulecard_"] [data-testid="stExpander"] summary {
    align-items: center !important;
    min-height: 0 !important;
    padding-top: 0px !important;     /* ← BOX HEIGHT KNOB: lower toward 0 for a shorter box */
    padding-bottom: 1px !important;  /* ← BOX HEIGHT KNOB */
}
/* Status chips overlaid onto the RIGHT of the header row. height:0 so they add no
   vertical space; top nudges them onto the name row; pointer-events:none lets clicks
   fall through to the expander toggle underneath. ↑ tune `top` to move chips up/down. */
[class*="st-key-rulecard_"] .rule-chips-overlay {
    position: relative;
    z-index: 5;
    height: 0 !important;
    margin: 0 !important;
    top: 10px;
    padding-right: 6px;
    pointer-events: none;
}
[class*="st-key-rulecard_"] .rule-chips-overlay .rule-badge-row {
    justify-content: flex-end !important;
    margin: 0 !important;
}

/* ===== Tabs — styled as attractive pill/box buttons (left-aligned by default) ===== */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 10px !important;
    border-bottom: none !important;
    flex-wrap: wrap !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: #f3f5f8 !important;
    border: 1px solid #9ca3af !important;   /* visible grey border on each tab box */
    border-radius: 10px !important;
    color: #374151 !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 8px 22px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
    transition: all 0.18s ease !important;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {
    background: #ffffff !important;
    border-color: #e53935 !important;
    color: #e53935 !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
}
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
    background: #e53935 !important;
    border-color: #9ca3af !important;   /* keep the grey border on the selected box too */
    color: #ffffff !important;
    box-shadow: 0 2px 8px rgba(229,57,53,0.25) !important;
}
/* Filled pills replace the underline highlight */
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] {
    display: none !important;
    background: transparent !important;
}
/* Center ONLY the dashboard result tabs (marked with .viz-tabs-marker). Other
   tab groups — e.g. the Rules page Static/Behavioral tabs — stay left-aligned. */
.element-container:has(.viz-tabs-marker) {
    display: none !important;
}
.element-container:has(.viz-tabs-marker) + div [data-baseweb="tab-list"] {
    justify-content: center !important;
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
.rec-rule     { font-size: 0.88rem; font-weight: 700; color: #111827; margin-bottom: 2px; }
.rec-severity { font-size: 0.7rem; color: #9ca3af; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.05em; }
.rec-issue   { font-size: 0.82rem; color: #6b7280; padding: 2px 0; }
.rec-issue strong { color: #374151; }
.rec-action  { font-size: 0.82rem; color: #374151; padding: 2px 0; }
.rec-action::before { content: '→ '; color: #e53935; font-weight: 700; }

/* ===== Rule detail cards ===== */
.rule-why    { background: #fffbeb; border: 1px solid #fde68a; border-radius: 7px; padding: 10px 14px; margin: 6px 0; color: #92400e; font-size: 0.84rem; }
.rule-impact { background: #fef2f2; border: 1px solid #fecaca; border-radius: 7px; padding: 10px 14px; margin: 6px 0; color: #991b1b; font-size: 0.84rem; }
.rule-action { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 7px; padding: 10px 14px; margin: 6px 0; color: #166534; font-size: 0.84rem; }
.rule-example{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 7px; padding: 8px 12px;  margin: 6px 0; font-family: 'Courier New', monospace; font-size: 0.77rem; color: #475569; overflow-x: auto; }
.rule-logic  { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 7px; padding: 10px 14px; margin: 6px 0; color: #1e3a8a; font-size: 0.84rem; }

/* Parameter chips — make threshold / window / group-by prominent at a glance */
.rule-chips  { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0 4px; }
.rule-chip   { display: inline-flex; align-items: baseline; gap: 5px; background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 999px; padding: 3px 11px; font-size: 0.74rem; color: #475569; }
.rule-chip b { color: #0f172a; font-weight: 700; }

/* Severity + status badges */
.rule-badge          { display: inline-block; border-radius: 6px; padding: 2px 9px; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; }
.rule-badge-critical { background: #fee2e2; color: #b91c1c; border: 1px solid #fecaca; }
.rule-badge-high     { background: #ffedd5; color: #c2410c; border: 1px solid #fed7aa; }
.rule-badge-medium   { background: #fef9c3; color: #a16207; border: 1px solid #fde68a; }
.rule-badge-low      { background: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; }
.rule-badge-info     { background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }
.rule-badge-on       { background: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; }
.rule-badge-off      { background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0; }
.rule-badge-custom   { background: #ede9fe; color: #6d28d9; border: 1px solid #ddd6fe; }
.rule-badge-prop     { background: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; }
.rule-badge-pending  { background: #fef3c7; color: #b45309; border: 1px solid #fde68a; }
/* Badge cluster pinned to the top-right of a rule card (severity · status · propagation). */
.rule-badge-row { display: flex; flex-wrap: wrap; gap: 6px; justify-content: flex-end; margin: 2px 0 8px; }

/* Framework reference tags (MITRE / NIST / ISO / CERT-In) */
.fw-tags { display: flex; flex-wrap: wrap; gap: 5px; margin: 6px 0; }
.fw-tag  { display: inline-block; background: #f5f3ff; border: 1px solid #ddd6fe; color: #5b21b6; border-radius: 5px; padding: 2px 8px; font-size: 0.7rem; font-weight: 600; }
.fw-label{ font-size: 0.72rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin: 8px 0 2px; }

</style>
"""


# Streamlit swaps the browser-tab favicon to an animated "running" indicator on every
# rerun (and re-emits the title), which shows up as the tab icon flickering/"shivering"
# on each page switch or background poll. This installs a one-time MutationObserver in
# the parent document that pins the favicon to a fixed shield and keeps the title
# stable, so the tab no longer flickers. It is purely cosmetic and fails safe.
_TAB_PIN_JS = """
<script>
(function () {
  try {
    var d = window.parent.document;
    if (d.__tabPinned) return;
    d.__tabPinned = true;
    var TITLE = "Cybersecurity Log Intelligence System";
    var SVG = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>" +
              "<path fill='#1a73e8' d='M12 2 4 5v6c0 5 3.4 9.3 8 11 4.6-1.7 8-6 8-11V5z'/></svg>";
    var ICON = "data:image/svg+xml," + encodeURIComponent(SVG);
    function pin() {
      var links = d.querySelectorAll("link[rel~='icon'], link[rel='shortcut icon']");
      if (!links.length) {
        var l = d.createElement('link'); l.rel = 'icon'; l.href = ICON; d.head.appendChild(l);
      } else {
        links.forEach(function (l) { if (l.href !== ICON) l.href = ICON; });
      }
      if (d.title !== TITLE) d.title = TITLE;
    }
    pin();
    new MutationObserver(pin).observe(d.head,
      { childList: true, subtree: true, attributes: true, attributeFilter: ['href'] });
  } catch (e) { /* cosmetic only — ignore if parent doc is unreachable */ }
})();
</script>
"""


def pin_browser_tab():
    """Inject the one-time, parent-document helpers that run at the top of every page.

    Both script-only iframes share ONE keyed container so they create a single layout
    slot — a SECOND container was reserving an extra ~1rem flex gap above the header (the
    gap the block container's -16px top margin no longer absorbed). CSS pulls this one
    container out of flow (position:absolute, 0×0) so it adds NO vertical space, while
    still rendering so the scripts run:
      • _TAB_PIN_JS       — pins the tab favicon/title so it doesn't flicker on reruns;
      • _NAV_TRANSITION_JS — installs the page-transition hooks (blank the outgoing page
                              on navigation, reveal the incoming one).
    """
    with st.container(key="tab_pin_holder"):
        components.html(_TAB_PIN_JS, height=0)
        components.html(_NAV_TRANSITION_JS, height=0)


# Page-transition hooks. Streamlit keeps the OUTGOING page on screen (dimmed, marked
# stale) while it renders the INCOMING one, so on data-heavy pages the old page used to
# bleed through a switch. This injects a tiny script ONCE into the PARENT document — and
# crucially it runs in the parent's OWN realm (a <script> appended to the parent head),
# NOT in this component iframe. Streamlit tears down + recreates the component iframe on
# every rerun, which kills any listener defined inside it; that teardown is exactly why an
# earlier in-iframe version went dead after one rerun and left the page stuck blank.
# Living in the parent realm, these listeners survive every rerun:
#   • on a click of a nav button that leads to a DIFFERENT page, add `app-navigating` to
#     <body> — CSS step 1 then hides ONLY the stale outgoing page (no bleed);
#   • clear `app-navigating` when the incoming page's waterfall reveal starts (with a 4 s
#     failsafe). And because CSS step 1 is scoped to stale content, the page un-hides
#     itself once the render settles even if this clear never runs — it can't get stuck.
# It fires ONLY on real page changes: the active page (red primary pill), Logout, the
# Home→Home sub-view case, and every same-page rerun (search / filter / sort / expander /
# publish / polling) are all skipped, so those stay instant. Purely additive, fails safe.
_NAV_TRANSITION_JS = """
<script>
(function () {
  try {
    var d = window.parent.document;
    if (d.getElementById('__navfx')) return;          // install the hook only once
    var s = d.createElement('script');
    s.id = '__navfx';
    s.textContent = `
      (function () {
        var doc = document;                            // the PARENT document
        var navTimer = null;
        function reset() {
          doc.body.classList.remove('app-navigating', 'navfx-cascade');
          if (navTimer) { clearTimeout(navTimer); navTimer = null; }
        }
        function box(el) {
          var m = el ? /st-key-pagebox_([a-z]+)/.exec(el.getAttribute('class') || '') : null;
          return m ? m[1] : null;
        }
        function navTo(cls) {
          var m = /st-key-nav_([a-z]+)/.exec(cls || '');
          if (!m) return null;
          return m[1] === 'dashboard' ? 'home' : m[1]; // rules/users/audit/settings/logout
        }
        // Click a nav button for a DIFFERENT page -> white-sheet the load + arm the cascade.
        doc.addEventListener('click', function (e) {
          var h = (e.target && e.target.closest)
            ? e.target.closest('[class*="st-key-nav_"]') : null;
          if (!h) return;
          var t = navTo(h.getAttribute('class'));
          if (!t || t === 'logout') return;                          // leaving to login
          var b = h.querySelector('button');
          if (b && b.getAttribute('kind') === 'primary') return;     // already on this page
          if (t === box(doc.querySelector('[class*="st-key-pagebox_"]'))) return; // same box
          doc.body.classList.add('app-navigating');                  // white sheet over the load
          doc.body.classList.add('navfx-cascade');                   // arm the content cascade
          if (navTimer) clearTimeout(navTimer);
          navTimer = setTimeout(reset, 5000);                        // failsafe
        }, true);
        // Content is mounting -> lift the white sheet so the cascade plays on the normal
        // bg. Trigger on the pagebox marker AND on the first block actually cascading
        // (appCascadeFall) — the latter fires even when the pagebox node is reused, so the
        // sheet lifts reliably on every navigation. Each block start pushes the disarm out
        // 1.5s, so navfx-cascade is dropped only once the whole cascade has finished (then
        // same-page reruns never re-animate the content).
        doc.addEventListener('animationstart', function (e) {
          if (e.animationName !== 'appPageMount' && e.animationName !== 'appCascadeFall') return;
          doc.body.classList.remove('app-navigating');
          if (navTimer) clearTimeout(navTimer);
          navTimer = setTimeout(function () { doc.body.classList.remove('navfx-cascade'); }, 1500);
        }, true);
      })();
    `;
    d.head.appendChild(s);
  } catch (e) { /* parent-doc blocked -- navigation still works, just without polish */ }
})();
</script>
"""


def set_page_style():
    st.markdown(_CSS, unsafe_allow_html=True)


# JS forwards a file dropped ANYWHERE on the page to the file_uploader's hidden
# <input>, so users don't have to hit the small dropzone. It runs in a same-origin
# srcdoc iframe (can reach window.parent.document) and is purely additive — if the
# browser blocks parent access, the normal uploader/dropzone still works.
_GLOBAL_DROP_JS = """
<script>
(function () {
  try {
    var doc = window.parent.document;

    // Strip Streamlit's auto-generated "Limit <size> per file •" prefix from the
    // dropzone hint, keeping ONLY the accepted file types (e.g. "TXT, CEF, LOG,
    // SYSLOG"). No upload-size cap is shown anywhere.
    //
    // IMPORTANT: the fixer is injected as a <script> into the PARENT document so its
    // MutationObserver lives in the page itself. Streamlit replaces this component's
    // iframe on every rerun, which would destroy an observer created in the iframe —
    // that is why the hint vanished after navigating away and back. Running in the
    // parent realm, the observer survives reruns/navigation and re-applies the fix
    // every time the uploader is re-rendered. The hint stays CSS-hidden until it is
    // marked data-hint-fixed="1", so the size limit never flashes.
    if (!doc.__uploaderHintFixerInstalled) {
      doc.__uploaderHintFixerInstalled = true;
      var fixerSrc = function () {
        var fix = function () {
          var boxes = document.querySelectorAll('[data-testid="stFileUploaderDropzoneInstructions"]');
          for (var j = 0; j < boxes.length; j++) {
            var nodes = boxes[j].querySelectorAll('span, small, p, div');
            for (var i = 0; i < nodes.length; i++) {
              var el = nodes[i];
              if (el.querySelector('span, small, p, div')) continue;   // only leaf text elements
              var txt = el.textContent || '';
              var bullet = txt.indexOf('\u2022');                      // "•" splits size from types
              var isHint = bullet >= 0 || /limit\b/i.test(txt);
              if (!isHint || /drag and drop/i.test(txt)) continue;     // never touch the drag text
              if (bullet >= 0) {
                var types = txt.slice(bullet + 1).trim();              // keep "TXT, CEF, LOG, SYSLOG"
                if (el.textContent !== types) el.textContent = types;
              } else if (el.textContent !== '') {
                el.textContent = '';                                   // size-only hint, no types listed
              }
              if (el.getAttribute('data-hint-fixed') !== '1') el.setAttribute('data-hint-fixed', '1');
            }
          }
        };
        var scheduled = false;
        var schedule = function () {
          if (scheduled) return; scheduled = true;
          requestAnimationFrame(function () { scheduled = false; fix(); });
        };
        fix();
        [0, 50, 150, 350, 800].forEach(function (d) { setTimeout(fix, d); });
        try {
          new MutationObserver(schedule).observe(
            document.body, { childList: true, subtree: true, characterData: true });
        } catch (_) { setInterval(fix, 800); }                        // observer blocked -> poll
      };
      var s = doc.createElement('script');
      s.type = 'text/javascript';
      s.textContent = '(' + fixerSrc.toString() + ')();';
      (doc.head || doc.documentElement).appendChild(s);
    }

    if (doc.__globalDropInstalled) return;
    doc.__globalDropInstalled = true;

    var ov = doc.createElement('div');
    ov.id = '__global_drop_overlay';
    ov.style.cssText = 'position:fixed;inset:0;z-index:99998;display:none;' +
      'align-items:center;justify-content:center;background:rgba(229,57,53,0.10);' +
      'border:3px dashed #e53935;color:#c62828;pointer-events:none;' +
      "font:700 1.6rem 'Segoe UI',sans-serif;";
    ov.textContent = 'Drop log file(s) to upload';
    doc.body.appendChild(ov);

    function hasFiles(e) {
      try { return Array.prototype.indexOf.call((e.dataTransfer && e.dataTransfer.types) || [], 'Files') >= 0; }
      catch (_) { return false; }
    }
    var depth = 0;
    doc.addEventListener('dragenter', function (e) { if (hasFiles(e)) { depth++; ov.style.display = 'flex'; } });
    doc.addEventListener('dragover',  function (e) { if (hasFiles(e)) { e.preventDefault(); } });
    doc.addEventListener('dragleave', function (e) { if (hasFiles(e)) { depth--; if (depth <= 0) { depth = 0; ov.style.display = 'none'; } } });
    doc.addEventListener('drop', function (e) {
      if (!hasFiles(e)) return;
      e.preventDefault(); depth = 0; ov.style.display = 'none';
      var files = e.dataTransfer && e.dataTransfer.files;
      if (!files || !files.length) return;
      var input = doc.querySelector('[data-testid="stFileUploaderDropzoneInput"]')
               || doc.querySelector('[data-testid="stFileUploaderDropzone"] input[type=file]')
               || doc.querySelector('[data-testid="stFileUploader"] input[type=file]');
      if (!input) return;
      var dt = new DataTransfer();
      var multi = input.hasAttribute('multiple');
      for (var i = 0; i < files.length; i++) { dt.items.add(files[i]); if (!multi) break; }
      input.files = dt.files;
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
  } catch (err) { /* parent-doc blocked — normal uploader still works */ }
})();
</script>
"""


def enable_global_drag_drop():
    """Make the whole page a drop target for the file uploader (single + append)."""
    components.html(_GLOBAL_DROP_JS, height=0)


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

    # Navigation stays enabled during analysis — the job runs in a background
    # thread/process, so leaving Home and coming back does NOT stop it. The progress
    # and results are picked back up when the user returns to Home.
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

    n = 0  # numbering for the per-rule cards only (Immediate Response stays unnumbered)
    if general:
        highest = next((s for s in ("CRITICAL", "HIGH", "MEDIUM", "LOW") if summary.get(s, 0) > 0), "")
        html += f'<div style="margin-bottom:12px;"><strong style="color:#374151;font-size:.88rem;">Immediate Response — {highest}:</strong></div>'
        html += '<div style="margin-bottom:16px;">'
        for action in general:
            html += f'<div class="rec-action">{action}</div>'
        html += '</div>'

    # Show every per-rule recommendation (one per detected rule), matching the PDF report.
    for rec in recs:
        n += 1
        sev = rec["severity"].lower()
        html += f'<div class="rec-card sev-{sev}-card">'
        html += f'<div class="rec-rule">{n}. {_esc(rec["rule_name"])}</div>'
        html += f'<div class="rec-severity">Severity: {_esc(rec.get("severity",""))}</div>'
        # Two concise lines: the issue detected, then the exact action to take.
        if rec.get("issue"):
            html += f'<div class="rec-issue"><strong>Issue:</strong> {_esc(rec["issue"])}</div>'
        if rec.get("action"):
            html += f'<div class="rec-action"><strong>Action:</strong> {_esc(rec["action"])}</div>'
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
        category_orders={"Severity": ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]},
        hole=0.38,
    )
    fig.update_traces(
        textposition="inside", textinfo="percent+label",
        textfont=dict(color="white", size=11),
        sort=False,
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
        category_orders={"severity": ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]},
        markers=True,
    )
    fig.update_layout(
        height=300,
        xaxis=dict(gridcolor=_CHART_GRID),
        yaxis=dict(gridcolor=_CHART_GRID),
        **_light_layout(),
    )
    fig.update_layout(legend_title_text="Severity")
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


# ── Extra analysis plots ──────────────────────────────────────────────────────

def plot_top_users(findings: list[dict]):
    users = [f["username"] for f in findings if f.get("username")]
    if not users:
        return None
    s = pd.Series(users).value_counts().head(10).reset_index()
    s.columns = ["Username", "Count"]
    fig = px.bar(
        s, x="Count", y="Username", orientation="h",
        title="Top Involved Users",
        color_discrete_sequence=["#7c3aed"],
    )
    fig.update_layout(
        height=320,
        yaxis=dict(autorange="reversed", gridcolor=_CHART_GRID),
        xaxis=dict(gridcolor=_CHART_GRID),
        **_light_layout(),
    )
    return fig


def plot_rule_type_breakdown(findings: list[dict]):
    if not findings:
        return None
    df = pd.DataFrame(findings)
    if "rule_type" not in df.columns:
        return None
    counts = df["rule_type"].fillna("static").str.title().value_counts().reset_index()
    counts.columns = ["Rule Type", "Count"]
    fig = px.bar(
        counts, x="Rule Type", y="Count",
        title="Findings by Rule Type (Static vs Behavioral)",
        color="Rule Type",
        color_discrete_sequence=["#1a73e8", "#e53935"],
    )
    fig.update_layout(height=320, **_light_layout())
    return fig


def threats_by_rule_table(findings: list[dict]) -> pd.DataFrame:
    """Aggregated count of findings per rule (most frequent first)."""
    if not findings:
        return pd.DataFrame(columns=["Rule", "Severity", "Count"])
    df = pd.DataFrame(findings)
    grp = (
        df.groupby(["rule_name", "severity"]).size()
        .reset_index(name="Count")
        .sort_values("Count", ascending=False)
    )
    grp.columns = ["Rule", "Severity", "Count"]
    return grp.reset_index(drop=True)


# ── Findings table ────────────────────────────────────────────────────────────

def findings_to_dataframe(findings: list[dict]) -> pd.DataFrame:
    """Full, untruncated findings table — used for both display and CSV export."""
    rows = []
    for f in findings:
        rows.append({
            "Severity":    f.get("severity", ""),
            "Rule":        f.get("rule_name", ""),
            "Source IP":   f.get("source_ip") or "N/A",
            "Username":    f.get("username") or "N/A",
            "Timestamp":   safe_ts_str(f.get("timestamp")),
            "Line #":      f.get("line_num") or "",
            "Description": f.get("description", ""),
        })
    return pd.DataFrame(rows)


def findings_to_csv_bytes(findings: list[dict]) -> bytes:
    """CSV for download, made Excel-friendly.

    Excel auto-converts a space-separated date like ``1900-06-08 22:30:34`` into a
    date value and then shows ``####`` whenever the column is narrower than the
    formatted date. Writing the timestamp in ISO-8601 form with a ``T`` separator
    keeps Excel from treating it as a date, so it stays plain text (no ####). A
    UTF-8 BOM also makes Excel detect the encoding correctly.
    """
    df = findings_to_dataframe(findings)
    if "Timestamp" in df.columns:
        df["Timestamp"] = df["Timestamp"].astype(str).str.replace(" ", "T", regex=False)
    return df.to_csv(index=False).encode("utf-8-sig")


def show_findings_table(findings: list[dict], max_rows: int = 500):
    if not findings:
        st.info("No threats detected.")
        return

    df = findings_to_dataframe(findings)
    if len(df) > max_rows:
        st.caption(f"Showing first {max_rows} of {len(df)} rows on screen — use the CSV download for the full set.")
        df = df.head(max_rows)
    st.dataframe(df, width='stretch', height=420, hide_index=True)