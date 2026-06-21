import streamlit as st
import time
import random
from datetime import datetime
import re
from agents import (
    build_search_agent,
    build_reader_agent,
    writer_chain,
    critic_chain,
    claim_extractor_chain,
    query_refiner_chain,
)
from agents import build_verifier_agent
from tools import parse_critic_score

# ── Config ────────────────────────────────────────────────────────────────────
MIN_SCORE      = 7.0
MAX_ITERATIONS = 3
MAX_CLAIMS     = 5

EXAMPLE_TOPICS = ["LLM agents in 2025", "CRISPR gene editing", "Fusion energy progress"]

VERDICT_KEY = {
    "VERIFIED":     {"label": "VERIFIED",     "var": "--verified"},
    "UNVERIFIED":   {"label": "UNVERIFIED",   "var": "--unverified"},
    "CONTRADICTED": {"label": "CONTRADICTED", "var": "--contradicted"},
}

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OrvixAI · Verified Research",
    page_icon="◎",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Theme state ───────────────────────────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state["theme"] = "light"

theme = st.session_state["theme"]

# ── Custom CSS ────────────────────────────────────────────────────────────────
_root_vars = """
    --paper:        #F5F5F1;
    --surface:      #FCFCFA;
    --surface-raised:#FFFFFF;
    --ink:          #1B1C20;
    --ink-soft:     #5A5C66;
    --ink-faint:    #97999F;
    --line:         #D9D9D0;
    --line-strong:  #C3C3B7;

    --accent:       #1F4FD8;
    --accent-soft:  #E7ECFB;
    --accent-hover: #1A3FAE;

    --stamp-red:    #B5392F;
    --lamp:         #C77F1A;

    --verified:     #1C7F4E;
    --verified-soft:#E7F5EC;
    --unverified:   #9A6B0C;
    --unverified-soft:#FBF1DC;
    --contradicted: #B5392F;
    --contradicted-soft:#FBEAE7;

    --grid-dot:     #C3C3B7;
    --grid-opacity: 1;
    --shadow-card:  2px 2px 0 rgba(27,28,32,0.04);
    --noise-opacity: 0.025;
""" if theme == "light" else """
    --paper:        #131316;
    --surface:      #1A1A1F;
    --surface-raised:#1F2024;
    --ink:          #ECEAE3;
    --ink-soft:     #ABA9A4;
    --ink-faint:    #6C6B68;
    --line:         #2C2C30;
    --line-strong:  #3A3A3F;

    --accent:       #E0A646;
    --accent-soft:  #2C2418;
    --accent-hover: #F0B85A;

    --stamp-red:    #D6594C;
    --lamp:         #E0A646;

    --verified:     #4FBE85;
    --verified-soft:#16291F;
    --unverified:   #E0A646;
    --unverified-soft:#2C2418;
    --contradicted: #D6594C;
    --contradicted-soft:#2E1D1A;

    --grid-dot:     #353539;
    --grid-opacity: 0.7;
    --shadow-card:  2px 2px 0 rgba(0,0,0,0.35);
    --noise-opacity: 0.05;
"""

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,500;0,6..72,600;0,6..72,700;1,6..72,500&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {{
{_root_vars}
}}

[data-theme="light"] {{
    --paper:        #F5F5F1;
    --surface:      #FCFCFA;
    --surface-raised:#FFFFFF;
    --ink:          #1B1C20;
    --ink-soft:     #5A5C66;
    --ink-faint:    #97999F;
    --line:         #D9D9D0;
    --line-strong:  #C3C3B7;
    --accent:       #1F4FD8;
    --accent-soft:  #E7ECFB;
    --accent-hover: #1A3FAE;
    --stamp-red:    #B5392F;
    --lamp:         #C77F1A;
    --verified:     #1C7F4E;
    --verified-soft:#E7F5EC;
    --unverified:   #9A6B0C;
    --unverified-soft:#FBF1DC;
    --contradicted: #B5392F;
    --contradicted-soft:#FBEAE7;
    --grid-dot:     #C3C3B7;
    --grid-opacity: 1;
    --shadow-card:  2px 2px 0 rgba(27,28,32,0.04);
    --noise-opacity: 0.025;
}}

[data-theme="dark"] {{
    --paper:        #131316;
    --surface:      #1A1A1F;
    --surface-raised:#1F2024;
    --ink:          #ECEAE3;
    --ink-soft:     #ABA9A4;
    --ink-faint:    #6C6B68;
    --line:         #2C2C30;
    --line-strong:  #3A3A3F;
    --accent:       #E0A646;
    --accent-soft:  #2C2418;
    --accent-hover: #F0B85A;
    --stamp-red:    #D6594C;
    --lamp:         #E0A646;
    --verified:     #4FBE85;
    --verified-soft:#16291F;
    --unverified:   #E0A646;
    --unverified-soft:#2C2418;
    --contradicted: #D6594C;
    --contradicted-soft:#2E1D1A;
    --grid-dot:     #353539;
    --grid-opacity: 0.7;
    --shadow-card:  2px 2px 0 rgba(0,0,0,0.35);
    --noise-opacity: 0.05;
}}

html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: var(--ink); }}

.stApp {{
    background-color: var(--paper);
    background-image: radial-gradient(circle, var(--grid-dot) 1px, transparent 1px);
    background-size: 24px 24px;
    background-position: var(--grid-pos, 0px 0px);
    transition: background-color 0.35s ease;
    animation: gridDrift 60s linear infinite;
}}
@keyframes gridDrift {{
    0%   {{ background-position: 0px 0px; }}
    100% {{ background-position: 240px 240px; }}
}}
@media (prefers-reduced-motion: reduce) {{
    .stApp {{ animation: none; }}
    .ov-topbar-cell, div[data-testid="stToggle"], .ov-hero-hatch, .ov-eyebrow, .ov-h1, .ov-sub {{ animation: none !important; opacity:1 !important; transform:none !important; }}
    .ov-eyebrow-dot, .ov-doc-id .live::before {{ animation: none !important; }}
}}

#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding: 0 0 6rem; max-width: 740px; margin: 0 auto; }}

/* ── report card prose — scoped so it only fires inside .ov-report-body ── */
.ov-report-body h1 {{ font-family: 'Newsreader', serif; font-weight: 600; font-style: italic; font-size: 1.55rem; line-height: 1.3; margin: 0 0 1rem; color: var(--ink); }}
.ov-report-body h2 {{ font-family: 'Newsreader', serif; font-weight: 600; font-size: 1.2rem; margin: 1.7rem 0 0.7rem; color: var(--ink); border-bottom: 1px solid var(--line); padding-bottom: 0.4rem; }}
.ov-report-body h3 {{ font-family: 'Newsreader', serif; font-weight: 600; font-size: 1.05rem; margin: 1.3rem 0 0.5rem; }}
.ov-report-body p, .ov-report-body li {{ font-size: 0.93rem; line-height: 1.75; color: var(--ink-soft); }}
.ov-report-body strong {{ color: var(--ink); font-weight: 600; }}
.ov-report-body li::marker {{ color: var(--accent); }}

.ov-topbar-cell {{
    padding: 1.05rem 0; border-bottom: 1.5px solid var(--ink);
    display:flex; align-items:center; min-height: 2.6rem;
    animation: topbarIn 0.5s ease both;
}}
@keyframes topbarIn {{
    0%   {{ opacity:0; transform: translateY(-6px); }}
    100% {{ opacity:1; transform: translateY(0); }}
}}
.ov-logo {{ display:flex; align-items:center; gap:0.55rem; }}
.ov-logo-mark {{
    width:24px; height:24px; border:1.5px solid var(--ink); border-radius:3px;
    display:flex; align-items:center; justify-content:center;
    font-family:'JetBrains Mono',monospace; font-weight:700; font-size:12px; color:var(--ink);
}}
.ov-logo-text {{ font-family:'JetBrains Mono',monospace; font-weight:700; font-size:0.85rem; letter-spacing:0.04em; color:var(--ink); text-transform:uppercase; }}
.ov-logo-text span {{ color:var(--accent); }}
.ov-doc-id {{ font-family:'JetBrains Mono',monospace; font-size:0.66rem; letter-spacing:0.08em; color:var(--ink-faint); text-align:right; line-height:1.5; }}
.ov-doc-id .live {{ color: var(--accent); position:relative; }}
.ov-doc-id .live::before {{
    content:""; display:inline-block; width:5px; height:5px; border-radius:50%;
    background: var(--accent); margin-right:5px; vertical-align:middle;
    animation: pulseDot 2.4s ease-in-out infinite;
}}

div[data-testid="stHorizontalBlock"]:has(.ov-topbar-cell) {{ padding: 0 1.5rem; }}
@media (max-width: 600px) {{
    div[data-testid="stHorizontalBlock"]:has(.ov-topbar-cell) {{ padding: 0 1rem; }}
}}

div[data-testid="stToggle"] {{
    display:flex; align-items:center; justify-content:flex-end;
    margin-top:0 !important; padding-top: 1.05rem; padding-bottom: 1.05rem;
    border-bottom: 1.5px solid var(--ink); min-height: 2.6rem;
    animation: topbarIn 0.5s ease both;
}}
div[data-testid="stToggle"] label {{ gap: 0 !important; margin: 0 !important; cursor:pointer; }}
div[data-testid="stToggle"] p {{ display:none !important; }}

div[data-testid="stToggle"] [data-baseweb="checkbox"] > div:first-child {{
    width: 48px !important; height: 26px !important;
    border-radius: 999px !important;
    background: var(--surface-raised) !important;
    border: 1.5px solid var(--ink) !important;
    transition: background 0.35s ease, border-color 0.35s ease, box-shadow 0.2s ease !important;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.15) !important;
    position: relative !important;
}}
div[data-testid="stToggle"] label:hover [data-baseweb="checkbox"] > div:first-child {{
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.15), 0 0 0 4px color-mix(in srgb, var(--accent) 16%, transparent) !important;
}}
div[data-testid="stToggle"] [data-baseweb="checkbox"] > div:first-child > div {{
    width: 20px !important; height: 20px !important;
    background: var(--accent) !important;
    border: 1px solid var(--ink) !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
    transition: transform 0.4s cubic-bezier(.34,1.56,.4,1), background 0.35s ease !important;
    display:flex !important; align-items:center !important; justify-content:center !important;
}}
div[data-testid="stToggle"] [data-baseweb="checkbox"] > div:first-child > div::before {{
    content: "☉"; font-size: 11px; color: var(--paper); line-height:1;
    transition: content 0.2s, transform 0.4s ease;
}}
div[data-testid="stToggle"] [aria-checked="true"] > div:first-child {{
    background: var(--ink) !important;
    border-color: var(--ink) !important;
}}
div[data-testid="stToggle"] [aria-checked="true"] > div:first-child > div {{
    background: var(--accent) !important;
    transform: rotate(180deg) !important;
}}
div[data-testid="stToggle"] [aria-checked="true"] > div:first-child > div::before {{
    content: "☾"; transform: rotate(-180deg);
}}

.ov-hero {{ position:relative; padding: 2.6rem 1.5rem 2.2rem; text-align:left; overflow:hidden; }}
.ov-hero-hatch {{
    position:absolute; top:0; right:0; width:84px; height:84px;
    background-image: repeating-linear-gradient(45deg, var(--ink) 0, var(--ink) 1px, transparent 1px, transparent 7px);
    opacity:0.45; -webkit-mask-image: linear-gradient(to bottom left, black 40%, transparent 75%);
            mask-image: linear-gradient(to bottom left, black 40%, transparent 75%);
    animation: fadeIn 0.8s ease 0.1s both;
}}
@keyframes fadeUp {{
    0%   {{ opacity:0; transform: translateY(10px); }}
    100% {{ opacity:1; transform: translateY(0); }}
}}
@keyframes fadeIn {{
    0%   {{ opacity:0; }}
    100% {{ opacity:1; }}
}}
.ov-eyebrow {{
    display:inline-flex; align-items:center; gap:0.5rem;
    border:1px solid var(--ink); border-radius:3px; padding:0.3rem 0.7rem;
    font-family:'JetBrains Mono',monospace; font-size:0.62rem; letter-spacing:0.12em; text-transform:uppercase; font-weight:700;
    color: var(--ink); margin-bottom:1.3rem;
    animation: fadeUp 0.5s ease 0.05s both;
}}
.ov-eyebrow-dot {{ width:6px; height:6px; border-radius:50%; background:var(--stamp-red); display:inline-block; animation: pulseDot 2.4s ease-in-out 0.6s infinite; }}
@keyframes pulseDot {{
    0%, 100% {{ opacity:1; box-shadow: 0 0 0 0 rgba(181,57,47,0.35); }}
    50% {{ opacity:0.55; box-shadow: 0 0 0 4px rgba(181,57,47,0); }}
}}
.ov-h1 {{
    font-family:'Newsreader', serif; font-weight:600; color:var(--ink);
    font-size: clamp(2rem, 5.4vw, 2.85rem); line-height:1.2;
    margin: 0 0 1.1rem; max-width: 580px;
    animation: fadeUp 0.55s ease 0.16s both;
}}
.ov-h1 .mark {{
    background: linear-gradient(120deg, var(--accent-soft) 0%, var(--accent-soft) 100%);
    background-repeat: no-repeat; background-size: 100% 38%; background-position: 0 88%;
    font-style: italic; padding: 0 0.05em;
}}
.ov-sub {{
    font-family:'Inter',sans-serif; font-size:1rem; line-height:1.7;
    color: var(--ink-soft); max-width:480px; margin:0;
    animation: fadeUp 0.55s ease 0.26s both;
}}

.stTextInput > div > div > input {{
    background: var(--surface) !important;
    border: 1.5px solid var(--ink) !important;
    border-radius: 6px !important;
    color: var(--ink) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 0.75rem 1.1rem !important;
}}
.stTextInput > div > div > input:focus {{
    border-color: var(--accent) !important;
    box-shadow: 2px 2px 0 var(--accent-soft) !important;
}}
.stTextInput > div > div > input::placeholder {{ color: var(--ink-faint) !important; }}
.stTextInput > label {{ display:none; }}

.block-container .stForm,
.block-container .stButton,
.block-container .stDownloadButton,
.block-container .stExpander,
.block-container .stAlert {{ padding-left: 1.5rem; padding-right: 1.5rem; }}

button[kind="primary"] {{
    background: var(--accent) !important;
    color: var(--paper) !important;
    border: 1.5px solid var(--accent) !important;
    border-radius: 6px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
    padding: 0.7rem 1.3rem !important;
    width: 100% !important;
    transition: background 0.15s, transform 0.1s, box-shadow 0.15s !important;
}}
button[kind="primary"]:hover {{ background: var(--accent-hover) !important; box-shadow: 0 2px 10px -2px color-mix(in srgb, var(--accent) 45%, transparent) !important; }}
button[kind="primary"]:active {{ transform: scale(0.98); }}

button[kind="secondary"] {{
    background: var(--surface) !important;
    color: var(--ink-soft) !important;
    border: 1px solid var(--line-strong) !important;
    border-radius: 6px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.8rem !important;
    padding: 0.45rem 0.9rem !important;
    transition: border-color 0.15s, color 0.15s, transform 0.1s !important;
}}
button[kind="secondary"]:hover {{ border-color: var(--accent) !important; color: var(--accent) !important; }}
button[kind="secondary"]:active {{ transform: scale(0.97); }}

.ov-features {{ display:flex; gap:0; margin: 2.4rem 1.5rem 0; border-top: 1.5px solid var(--ink); }}
.ov-feature {{ flex:1; padding: 1rem 1.1rem 1.1rem 0; border-right: 1px solid var(--line); transition: opacity 0.2s; }}
.ov-feature:last-child {{ border-right:none; }}
.ov-feature:hover {{ opacity: 0.78; }}
.ov-feature-num {{ font-family:'JetBrains Mono',monospace; font-size:0.7rem; font-weight:700; color:var(--accent); margin-bottom:0.5rem; }}
.ov-feature-label {{ font-family:'JetBrains Mono',monospace; font-size:0.62rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--ink); font-weight:700; margin-bottom:0.4rem; }}
.ov-feature-text {{ font-size:0.82rem; color:var(--ink-soft); line-height:1.55; }}

.ov-loading {{
    display:flex; flex-direction:column; align-items:flex-start; gap:0.5rem;
    margin: 2.2rem 1.5rem; padding: 1rem 1.2rem;
    border:1px dashed var(--line-strong); border-radius:6px; background: var(--surface);
}}
.ov-loading-text {{ font-family:'JetBrains Mono',monospace; font-size:0.82rem; color:var(--ink-soft); display:flex; align-items:center; }}
.ov-loading-text::before {{ content:"› "; color: var(--accent); }}
.ov-loading-caret {{
    display:inline-block; width:7px; height:1em; margin-left:5px;
    background: var(--accent); animation: caretBlink 0.9s steps(1) infinite;
}}
@keyframes caretBlink {{ 50% {{ opacity: 0; }} }}
.ov-loading-bar {{ width:100%; height:2px; background: var(--line); border-radius:2px; overflow:hidden; margin-top:0.2rem; }}
.ov-loading-bar-fill {{ height:100%; width:40%; background: var(--accent); animation: barSlide 1.3s ease-in-out infinite; }}
@keyframes barSlide {{
    0%   {{ transform: translateX(-100%); }}
    100% {{ transform: translateX(350%); }}
}}

.ov-meta-title {{ font-family:'Newsreader',serif; font-weight:600; font-size:1.05rem; color:var(--ink); }}
.ov-meta-sub {{ font-family:'JetBrains Mono',monospace; font-size:0.72rem; color:var(--ink-faint); margin-top:0.15rem; }}

.ov-card {{
    position:relative;
    background: var(--surface); border: 1.5px solid var(--ink);
    border-radius: 4px; padding: 2.1rem 2rem 1.9rem; margin: 1.9rem 1.5rem 0;
    box-shadow: var(--shadow-card);
    transition: box-shadow 0.2s ease;
}}
.ov-card::after {{
    content: ""; position:absolute; top:0; right:0; width:0; height:0;
    border-style: solid; border-width: 0 22px 22px 0;
    border-color: transparent var(--paper) transparent transparent;
    filter: drop-shadow(-1px 1px 1px rgba(0,0,0,0.18));
}}
.ov-card-tab {{
    position:absolute; top:-1.5px; left:1.4rem; transform:translateY(-100%);
    background: var(--ink); color: var(--paper);
    font-family:'JetBrains Mono',monospace; font-size:0.62rem; font-weight:700; letter-spacing:0.1em;
    padding: 0.3rem 0.7rem; border-radius: 4px 4px 0 0;
}}
.ov-ledger-head {{ display:flex; align-items:baseline; justify-content:space-between; margin-bottom:1.1rem; }}
.ov-ledger-title {{ font-family:'Newsreader',serif; font-weight:600; font-size:1.05rem; }}
.ov-ledger-count {{ font-family:'JetBrains Mono',monospace; font-size:0.7rem; color:var(--ink-faint); }}
.ov-ledger-row {{ transition: background 0.15s ease; border-radius: 4px; }}
.ov-ledger-row:hover {{ background: var(--paper); }}
.ov-tag {{
    display:inline-flex; align-items:center; flex-shrink:0; height:fit-content;
    font-family:'JetBrains Mono',monospace; font-size:0.62rem; font-weight:700; letter-spacing:0.05em;
    border-radius:4px; padding:0.3rem 0.55rem; border:1.5px solid currentColor; background:var(--surface);
    transform: rotate(-1.2deg);
}}
.ov-sources-text {{ font-size:0.82rem; line-height:1.65; color:var(--ink-soft); white-space:pre-wrap; }}
.ov-sources-label {{ font-family:'JetBrains Mono',monospace; font-size:0.62rem; letter-spacing:0.1em; text-transform:uppercase; color:var(--ink-faint); margin-bottom:0.4rem; }}

.streamlit-expanderHeader {{
    background: var(--surface) !important; border: 1px solid var(--line-strong) !important;
    border-radius: 6px !important; color: var(--ink-soft) !important;
    font-family: 'JetBrains Mono', monospace !important; font-size: 0.78rem !important;
}}
.streamlit-expanderContent {{ background: var(--surface) !important; border: 1px solid var(--line-strong) !important; border-top: none !important; }}

.stDownloadButton > button {{
    background: var(--surface) !important; color: var(--ink-soft) !important;
    border: 1px solid var(--line-strong) !important; border-radius: 6px !important;
    font-family: 'JetBrains Mono', monospace !important; font-size: 0.74rem !important; font-weight: 500 !important;
    padding: 0.5rem 1.1rem !important; transition: border-color 0.2s, color 0.2s !important;
    text-transform: uppercase; letter-spacing: 0.04em;
}}
.stDownloadButton > button:hover {{ border-color: var(--accent) !important; color: var(--accent) !important; }}
.stDownloadButton > button:active {{ transform: scale(0.97); }}

.stAlert {{
    background: var(--unverified-soft) !important; border: 1px solid rgba(154,107,12,0.3) !important;
    border-radius: 6px !important; color: var(--unverified) !important;
    font-family: 'Inter', sans-serif !important; font-size: 0.85rem !important;
}}

.ov-footer {{ text-align:center; margin-top:3.5rem; font-family:'JetBrains Mono',monospace; font-size:0.62rem; letter-spacing:0.12em; color:var(--ink-faint); }}

@media (max-width: 600px) {{
    .ov-topbar {{ padding: 1rem 1rem; }}
    .ov-logo-text {{ font-size: 0.74rem; }}
    .ov-doc-id {{ font-size: 0.58rem; }}
    .ov-hero {{ padding: 2rem 1rem 1.6rem; }}
    .ov-hero-hatch {{ width: 56px; height: 56px; }}
    .ov-h1 {{ font-size: clamp(1.6rem, 8vw, 2.1rem); }}
    .ov-sub {{ font-size: 0.9rem; }}
    .ov-features {{ flex-direction: column; margin: 1.8rem 1rem 0; }}
    .ov-feature {{ border-right: none; border-bottom: 1px solid var(--line); padding: 0.9rem 0; }}
    .ov-feature:last-child {{ border-bottom: none; }}
    .ov-card {{ margin: 1.4rem 1rem 0; padding: 1.6rem 1.3rem 1.5rem; }}
    .block-container .stForm,
    .block-container .stButton,
    .block-container .stDownloadButton,
    .block-container .stExpander,
    .block-container .stAlert {{ padding-left: 1rem; padding-right: 1rem; }}
}}

.ov-stamp {{
    width:88px; height:88px; border-radius:50%; border:2px solid var(--stamp-color);
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    background:var(--surface-raised);
    box-shadow: 0 0 0 5px color-mix(in srgb, var(--stamp-color) 10%, transparent), var(--shadow-card);
    animation: stampPress 0.55s cubic-bezier(.2,1.4,.4,1) both;
}}
@keyframes stampPress {{
    0%   {{ transform: scale(2.2) rotate(-22deg); opacity:0; }}
    55%  {{ transform: scale(0.92) rotate(-9deg); opacity:1; }}
    75%  {{ transform: scale(1.05) rotate(-7deg); }}
    100% {{ transform: scale(1) rotate(-6deg); opacity:1; }}
}}
@media (prefers-reduced-motion: reduce) {{
    .ov-stamp {{ animation: none; transform: rotate(-6deg); }}
}}
</style>

<script>
(function() {{
    function applyTheme() {{
        document.documentElement.setAttribute('data-theme', '{theme}');
    }}
    applyTheme();
    var tries = 0;
    var iv = setInterval(function() {{
        applyTheme();
        tries += 1;
        if (tries > 10) clearInterval(iv);
    }}, 100);
}})();
</script>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content)


def parse_claims_from_text(raw: str) -> list[str]:
    claims = []
    for line in raw.strip().splitlines():
        m = re.match(r"^\d+\.\s+(.+)$", line.strip())
        if m:
            claims.append(m.group(1).strip())
    return claims[:MAX_CLAIMS]


def run_search_and_scrape(query: str, topic_val: str) -> dict:
    sa = build_search_agent()
    sr = sa.invoke({"messages": [("user", f"Find recent, reliable and detailed information about: {query}")]})
    search_text = _extract_text(sr["messages"][-1].content)

    ra = build_reader_agent()
    rr = ra.invoke({"messages": [(
        "user",
        f"Based on the following search results about '{topic_val}', "
        f"pick the most relevant URL and scrape it.\n\nSearch Results:\n{search_text[:800]}"
    )]})
    return {"search": search_text, "reader": _extract_text(rr["messages"][-1].content)}


def run_writer_critic(topic_val: str, search_text: str, reader_text: str) -> dict:
    combined = f"SEARCH RESULTS:\n{search_text}\n\nDETAILED SCRAPED CONTENT:\n{reader_text}"
    report   = writer_chain.invoke({"topic": topic_val, "research": combined})
    feedback = critic_chain.invoke({"report": report})
    score    = parse_critic_score(feedback)
    return {"writer": report, "critic": feedback, "score": score}


def loading_html(text: str) -> str:
    return f"""
    <div class="ov-loading">
        <div class="ov-loading-text">{text}<span class="ov-loading-caret"></span></div>
        <div class="ov-loading-bar"><div class="ov-loading-bar-fill"></div></div>
    </div>
    """


def stamp_html(score: float) -> str:
    verified = score >= MIN_SCORE
    color_var = "--verified" if verified else "--unverified"
    label = "VERIFIED" if verified else "DRAFT"
    return f"""
    <div class="ov-stamp" style="--stamp-color:var({color_var});">
        <span style="font-family:'JetBrains Mono',monospace;font-weight:700;font-size:1.2rem;color:var({color_var});line-height:1;">{score:.1f}</span>
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.52rem;color:var(--ink-faint);margin-top:1px;">/ 10</span>
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.44rem;letter-spacing:0.08em;color:var({color_var});margin-top:3px;">{label}</span>
    </div>
    """


def markdown_to_html(md: str) -> str:
    """Convert a minimal subset of markdown to HTML for embedding inside st.markdown HTML blocks."""
    import html as html_mod
    lines = md.split("\n")
    out = []
    in_ul = False
    for line in lines:
        # headings
        if line.startswith("### "):
            if in_ul: out.append("</ul>"); in_ul = False
            out.append(f"<h3>{html_mod.escape(line[4:])}</h3>")
        elif line.startswith("## "):
            if in_ul: out.append("</ul>"); in_ul = False
            out.append(f"<h2>{html_mod.escape(line[3:])}</h2>")
        elif line.startswith("# "):
            if in_ul: out.append("</ul>"); in_ul = False
            out.append(f"<h1>{html_mod.escape(line[2:])}</h1>")
        # bullet
        elif line.startswith("- ") or line.startswith("* "):
            if not in_ul: out.append("<ul>"); in_ul = True
            inner = line[2:]
            # bold
            inner = re.sub(r"\*\*(.+?)\*\*", lambda m: f"<strong>{html_mod.escape(m.group(1))}</strong>", inner)
            out.append(f"<li>{inner}</li>")
        # blank line
        elif line.strip() == "":
            if in_ul: out.append("</ul>"); in_ul = False
            out.append("")
        else:
            if in_ul: out.append("</ul>"); in_ul = False
            # bold inline
            text = re.sub(r"\*\*(.+?)\*\*", lambda m: f"<strong>{html_mod.escape(m.group(1))}</strong>", line)
            out.append(f"<p>{text}</p>")
    if in_ul:
        out.append("</ul>")
    return "\n".join(out)


# ── Session state ─────────────────────────────────────────────────────────────
defaults = {
    "phase":         "idle",
    "results":       {},
    "claims":        [],
    "score":         0.0,
    "topic_done":    "",
    "generated_at":  None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v
if "topic_input" not in st.session_state:
    st.session_state["topic_input"] = ""
if "doc_id" not in st.session_state:
    st.session_state["doc_id"] = f"OVX-{datetime.now().strftime('%y%m%d')}-{random.randint(1000, 9999)}"


# ── Top strip ─────────────────────────────────────────────────────────────────
status_word = "OPEN" if st.session_state.phase != "done" else "SEALED"

top_l, top_r = st.columns([2.2, 1.8], vertical_alignment="center")

with top_l:
    st.markdown("""
    <div class="ov-topbar-cell">
        <div class="ov-logo">
            <div class="ov-logo-mark">O</div>
            <div class="ov-logo-text">Orvix<span>AI</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with top_r:
    doc_col, toggle_col = st.columns([2.3, 1], vertical_alignment="center")
    with doc_col:
        st.markdown("", unsafe_allow_html=True)
    with toggle_col:
        is_dark = st.toggle(
            "Dark mode", value=(theme == "dark"), key="theme_toggle",
            label_visibility="collapsed",
        )
        new_theme = "dark" if is_dark else "light"
        if new_theme != theme:
            st.session_state["theme"] = new_theme
            st.rerun()


# ── Hero ──────────────────────────────────────────────────────────────────────
if st.session_state.phase != "done":
    st.markdown("""
    <div class="ov-hero">
        <div class="ov-hero-hatch"></div>
        <span class="ov-eyebrow"><span class="ov-eyebrow-dot"></span>Open Inquiry</span>
        <div class="ov-h1">One question in.<br>A <span class="mark">verified</span> dossier out.</div>
        <p class="ov-sub">OrvixAI searches the live web, drafts a complete report, and checks every claim against its sources before the file is sealed.</p>
    </div>
    """, unsafe_allow_html=True)


# ── Input form ────────────────────────────────────────────────────────────────
if st.session_state.phase != "running":
    with st.form("research_form", clear_on_submit=False):
        topic = st.text_input(
            "Research Topic",
            placeholder="What do you want researched?",
            key="topic_input",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button(" Start Research →", type="primary", use_container_width=True)

        st.markdown("", unsafe_allow_html=True)

    if submitted:
        if not topic.strip():
            st.warning("Please enter a research topic first.")
        else:
            st.session_state.phase      = "running"
            st.session_state.topic_done = topic.strip()
            st.session_state.results    = {}
            st.session_state.claims     = []
            st.rerun()


# ── Pipeline execution ────────────────────────────────────────────────────────
if st.session_state.phase == "running":
    topic_val = st.session_state.topic_done
    status = st.empty()
    status.markdown(loading_html("Reading the latest sources…"), unsafe_allow_html=True)

    data = run_search_and_scrape(topic_val, topic_val)
    search_text, reader_text = data["search"], data["reader"]

    status.markdown(loading_html("Drafting the dossier…"), unsafe_allow_html=True)
    result = run_writer_critic(topic_val, search_text, reader_text)

    iteration = 1
    while result["score"] < MIN_SCORE and iteration < MAX_ITERATIONS:
        iteration += 1
        status.markdown(loading_html(f"Refining the draft (pass {iteration})…"), unsafe_allow_html=True)
        refined_query = query_refiner_chain.invoke({
            "topic": topic_val, "feedback": result["critic"],
        }).strip()
        new_data = run_search_and_scrape(refined_query, topic_val)
        search_text = search_text + "\n\n--- REFINED SEARCH ---\n" + new_data["search"]
        reader_text = reader_text + "\n\n--- REFINED SCRAPE ---\n"  + new_data["reader"]
        result = run_writer_critic(topic_val, search_text, reader_text)

    status.markdown(loading_html("Checking each claim…"), unsafe_allow_html=True)
    raw_claims = claim_extractor_chain.invoke({"report": result["writer"]})
    claims     = parse_claims_from_text(raw_claims)
    verifier   = build_verifier_agent()
    verified_list = []
    for claim in claims:
        vr = verifier.invoke({"messages": [(
            "user",
            f"Use the verify_claim tool to check this claim, then give a final verdict.\n\n"
            f"Claim: {claim}\n\n"
            f"After seeing the evidence, respond in this exact format:\n"
            f"VERDICT: <VERIFIED|UNVERIFIED|CONTRADICTED>\n"
            f"REASON: <one sentence explaining why>"
        )]})
        out = _extract_text(vr["messages"][-1].content)
        vm  = re.search(r"VERDICT:\s*(VERIFIED|UNVERIFIED|CONTRADICTED)", out, re.IGNORECASE)
        rm  = re.search(r"REASON:\s*(.+)", out)
        verified_list.append({
            "claim":   claim,
            "verdict": vm.group(1).upper() if vm else "UNVERIFIED",
            "reason":  rm.group(1).strip()  if rm else "Could not determine.",
        })

    status.empty()
    st.session_state.results      = {"search": search_text, "reader": reader_text, "writer": result["writer"]}
    st.session_state.score        = result["score"]
    st.session_state.claims       = verified_list
    st.session_state.generated_at = datetime.now()
    st.session_state.phase        = "done"
    st.rerun()


# ── Results ───────────────────────────────────────────────────────────────────
if st.session_state.phase == "done":
    r      = st.session_state.results
    score  = st.session_state.score
    claims = st.session_state.claims
    verified_n = sum(1 for c in claims if c["verdict"] == "VERIFIED")

    col_stamp, col_meta, col_new = st.columns([1, 3.2, 1.4])
    with col_stamp:
        st.markdown(stamp_html(score), unsafe_allow_html=True)
    with col_meta:
        st.markdown(f"""
        <div class="ov-meta-title">{st.session_state.topic_done}</div>
        <div class="ov-meta-sub">{st.session_state.generated_at.strftime('%b %d, %Y')} · {verified_n}/{len(claims)} claims verified</div>
        """, unsafe_allow_html=True)
    with col_new:
        if st.button("↺ New file", key="new_research", type="secondary", use_container_width=True):
            st.session_state.phase = "idle"
            st.session_state.results = {}
            st.session_state.claims = []
            st.session_state.doc_id = f"OVX-{datetime.now().strftime('%y%m%d')}-{random.randint(1000, 9999)}"
            st.rerun()

    # ── FIX 1: Report card — render markdown content INSIDE the card div ──────
    report_html = markdown_to_html(r["writer"])
    st.markdown(f"""
    <div class="ov-card">
        <div class="ov-card-tab">Report</div>
        <div class="ov-report-body">{report_html}</div>
    </div>
    """, unsafe_allow_html=True)

    st.download_button(
        "⬇ Download dossier (.md)",
        data=r["writer"],
        file_name=f"{st.session_state.topic_done.lower().replace(' ', '-')}-dossier-{int(time.time())}.md",
        mime="text/markdown",
    )

    # ── Ledger — use st.components.v1.html so Streamlit can't interfere ─────
    if claims:
        import html as _html
        import streamlit.components.v1 as components

        # Resolve actual hex colors for the current theme so the iframe
        # (which has no access to the parent page's CSS variables) looks right.
        is_dark = (theme == "dark")
        COLORS = {
            "surface":      "#1A1A1F" if is_dark else "#FCFCFA",
            "surface_raised":"#1F2024" if is_dark else "#FFFFFF",
            "paper":        "#131316" if is_dark else "#F5F5F1",
            "ink":          "#ECEAE3" if is_dark else "#1B1C20",
            "ink_soft":     "#ABA9A4" if is_dark else "#5A5C66",
            "ink_faint":    "#6C6B68" if is_dark else "#97999F",
            "line":         "#2C2C30" if is_dark else "#D9D9D0",
            "accent":       "#E0A646" if is_dark else "#1F4FD8",
            "verified":     "#4FBE85" if is_dark else "#1C7F4E",
            "verified_soft":"#16291F" if is_dark else "#E7F5EC",
            "unverified":   "#E0A646" if is_dark else "#9A6B0C",
            "unverified_soft":"#2C2418" if is_dark else "#FBF1DC",
            "contradicted": "#D6594C" if is_dark else "#B5392F",
            "contradicted_soft":"#2E1D1A" if is_dark else "#FBEAE7",
        }
        VERDICT_COLORS = {
            "VERIFIED":     COLORS["verified"],
            "UNVERIFIED":   COLORS["unverified"],
            "CONTRADICTED": COLORS["contradicted"],
        }

        rows_html = ""
        for i, c in enumerate(claims):
            verdict  = c["verdict"].upper()
            color    = VERDICT_COLORS.get(verdict, COLORS["unverified"])
            label    = verdict
            border   = "none" if i == 0 else f"1px solid {COLORS['line']}"
            claim_safe  = _html.escape(c["claim"])
            reason_safe = _html.escape(c["reason"])
            rows_html += f"""
            <div style="display:flex;gap:1rem;padding:0.95rem 0.6rem;
                        border-top:{border};align-items:flex-start;
                        border-radius:4px;transition:background 0.15s;">
                <div style="flex:1;font-size:0.86rem;color:{COLORS['ink']};line-height:1.55;">
                    {claim_safe}
                    <div style="font-size:0.78rem;color:{COLORS['ink_faint']};margin-top:0.25rem;">{reason_safe}</div>
                </div>
                <span style="display:inline-flex;align-items:center;flex-shrink:0;
                             font-family:'JetBrains Mono',monospace;font-size:0.62rem;
                             font-weight:700;letter-spacing:0.05em;border-radius:4px;
                             padding:0.3rem 0.55rem;border:1.5px solid {color};
                             color:{color};background:{COLORS['surface']};
                             transform:rotate(-1.2deg);white-space:nowrap;">
                    {label}
                </span>
            </div>
            """

        ledger_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:wght@600&family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;500&display=swap">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: transparent;
    font-family: 'Inter', sans-serif;
    padding: 0;
    margin: 0;
  }}
  .card {{
    position: relative;
    background: {COLORS['surface']};
    border: 1.5px solid {COLORS['ink']};
    border-radius: 4px;
    padding: 2.1rem 2rem 1.9rem;
    box-shadow: 2px 2px 0 rgba(0,0,0,0.06);
  }}
  .card::after {{
    content: "";
    position: absolute;
    top: 0; right: 0;
    width: 0; height: 0;
    border-style: solid;
    border-width: 0 22px 22px 0;
    border-color: transparent {COLORS['paper']} transparent transparent;
    filter: drop-shadow(-1px 1px 1px rgba(0,0,0,0.18));
  }}
  .tab {{
    position: absolute;
    top: -1.5px; left: 1.4rem;
    transform: translateY(-100%);
    background: {COLORS['ink']};
    color: {COLORS['surface']};
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.62rem; font-weight: 700; letter-spacing: 0.1em;
    padding: 0.3rem 0.7rem;
    border-radius: 4px 4px 0 0;
  }}
  .head {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 1.1rem;
  }}
  .head-title {{
    font-family: 'Newsreader', serif;
    font-weight: 600; font-size: 1.05rem;
    color: {COLORS['ink']};
  }}
  .head-count {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: {COLORS['ink_faint']};
  }}
</style>
</head>
<body>
  <div class="card">
    <div class="tab">Ledger</div>
    <div class="head">
      <span class="head-title">Verification ledger</span>
      <span class="head-count">{verified_n}/{len(claims)} verified</span>
    </div>
    {rows_html}
  </div>
</body>
</html>"""

        # Height: header ~80px + each row ~72px + padding
        ledger_height = 100 + len(claims) * 90
        components.html(ledger_html, height=ledger_height, scrolling=False)

    # Research notes
    with st.expander("View research notes"):
        st.markdown(f'<div class="ov-sources-label">What was found</div><div class="ov-sources-text">{r["search"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ov-sources-label" style="margin-top:1rem;">Closest reading</div><div class="ov-sources-text">{r["reader"]}</div>', unsafe_allow_html=True)


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(f'<div class="ov-footer">© 2026 OrvixAI . All rights reserved. Legal and privacy policy.</div>', unsafe_allow_html=True)