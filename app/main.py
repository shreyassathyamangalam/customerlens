"""
app/main.py
============
CustomerLens Streamlit application entry point.

Run:
    uv run streamlit run app/main.py
"""

import sys
from pathlib import Path

# Ensure project root is on path when running via streamlit
sys.path.insert(0, str(Path(__file__).parents[1]))

import streamlit as st

st.set_page_config(
    page_title="CustomerLens",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global design tokens ──────────────────────────────────────────────────────
st.markdown(
    """
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');

  /* ── Reset & base ── */
  html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {
    background: #0d1117;
    border-right: 1px solid #21262d;
  }
  [data-testid="stSidebar"] * { color: #e6edf3 !important; }
  [data-testid="stSidebar"] .stRadio label {
    font-size: 0.9rem;
    letter-spacing: 0.02em;
    padding: 6px 0;
  }

  /* ── Main background ── */
  .stApp { background: #f6f8fa; }

  /* ── Page header ── */
  .cl-header {
    background: linear-gradient(135deg, #0d1117 0%, #161b22 60%, #1c2333 100%);
    border-radius: 12px;
    padding: 32px 40px;
    margin-bottom: 28px;
    border: 1px solid #30363d;
    position: relative;
    overflow: hidden;
  }
  .cl-header::before {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 220px; height: 220px;
    background: radial-gradient(circle, rgba(88,166,255,0.12) 0%, transparent 70%);
    border-radius: 50%;
  }
  .cl-header-title {
    font-family: 'DM Serif Display', serif;
    font-size: 2.2rem;
    color: #e6edf3;
    margin: 0 0 6px 0;
    line-height: 1.2;
  }
  .cl-header-sub {
    font-size: 0.95rem;
    color: #8b949e;
    font-weight: 300;
    letter-spacing: 0.03em;
  }
  .cl-badge {
    display: inline-block;
    background: rgba(88,166,255,0.15);
    border: 1px solid rgba(88,166,255,0.3);
    color: #58a6ff;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 20px;
    margin-bottom: 14px;
  }

  /* ── Cards ── */
  .cl-card {
    background: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 10px;
    padding: 24px 28px;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }
  .cl-card-dark {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 16px;
  }

  /* ── Metric chips ── */
  .cl-metric {
    background: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 14px 18px;
    text-align: center;
  }
  .cl-metric-value {
    font-family: 'DM Mono', monospace;
    font-size: 1.6rem;
    font-weight: 500;
    color: #0d1117;
  }
  .cl-metric-label {
    font-size: 0.75rem;
    color: #57606a;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 4px;
  }

  /* ── Cypher block ── */
  .cl-cypher {
    background: #0d1117;
    border: 1px solid #30363d;
    border-left: 3px solid #58a6ff;
    border-radius: 8px;
    padding: 16px 20px;
    font-family: 'DM Mono', monospace;
    font-size: 0.82rem;
    color: #79c0ff;
    white-space: pre-wrap;
    word-break: break-word;
    margin: 12px 0;
  }

  /* ── Answer bubble ── */
  .cl-answer {
    background: #ffffff;
    border: 1px solid #d0d7de;
    border-left: 4px solid #3fb950;
    border-radius: 0 8px 8px 0;
    padding: 18px 22px;
    font-size: 0.95rem;
    line-height: 1.7;
    color: #1f2328;
  }

  /* ── Report narrative ── */
  .cl-narrative {
    background: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 10px;
    padding: 28px 32px;
    line-height: 1.8;
    color: #1f2328;
    font-size: 0.93rem;
  }
  .cl-narrative h2 {
    font-family: 'DM Serif Display', serif;
    color: #0d1117;
    font-size: 1.2rem;
    margin-top: 24px;
    border-bottom: 1px solid #d0d7de;
    padding-bottom: 6px;
  }

  /* ── History item ── */
  .cl-history-item {
    background: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 0.85rem;
    color: #57606a;
    margin-bottom: 6px;
    cursor: pointer;
  }

  /* ── Expander — make visible against light bg ── */
  [data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1.5px solid #30363d !important;
    border-radius: 8px !important;
  }
  [data-testid="stExpander"] summary {
    background: #1c2333 !important;
    color: #79c0ff !important;
    border-radius: 6px !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    padding: 10px 14px !important;
  }
  [data-testid="stExpander"] summary:hover {
    background: #21262d !important;
  }
  [data-testid="stExpander"] summary svg {
    fill: #79c0ff !important;
  }

  /* ── Tabs ── */
  [data-testid="stTabs"] [data-testid="stTab"] {
    color: #57606a !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
  }
  [data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"] {
    color: #0d1117 !important;
    font-weight: 600 !important;
    border-bottom-color: #0d1117 !important;
  }
  [data-testid="stTabs"] [data-testid="stTab"]:hover {
    color: #0d1117 !important;
  }

  /* ── Streamlit overrides ── */
  .stTextInput > div > div > input {
    border-radius: 8px !important;
    border: 1.5px solid #d0d7de !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 10px 14px !important;
  }
  .stTextInput > div > div > input:focus {
    border-color: #58a6ff !important;
    box-shadow: 0 0 0 3px rgba(88,166,255,0.15) !important;
  }
  .stButton > button {
    background: #0d1117 !important;
    color: #e6edf3 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    letter-spacing: 0.02em !important;
    padding: 8px 20px !important;
    transition: all 0.15s ease !important;
  }
  .stButton > button:hover {
    background: #161b22 !important;
    border-color: #58a6ff !important;
  }
  div[data-testid="stDataFrame"] {
    border-radius: 8px !important;
    overflow: hidden !important;
    border: 1px solid #d0d7de !important;
  }
  .stSelectbox > div > div {
    border-radius: 8px !important;
  }
  .stSpinner > div { color: #58a6ff !important; }
  .stAlert { border-radius: 8px !important; }

  /* ── Sidebar logo area ── */
  .cl-sidebar-logo {
    font-family: 'DM Serif Display', serif;
    font-size: 1.4rem;
    color: #e6edf3;
    padding: 8px 0 24px 0;
    border-bottom: 1px solid #21262d;
    margin-bottom: 24px;
  }
  .cl-sidebar-logo span { color: #58a6ff; }
  .cl-nav-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #484f58 !important;
    margin-bottom: 8px;
  }
</style>
""",
    unsafe_allow_html=True,
)

# ── Sidebar navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
    <div class="cl-sidebar-logo">Customer<span>Lens</span></div>
    <div class="cl-nav-label">Navigation</div>
    """,
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Navigation",
        ["💬  Q&A Chat", "📄  Report Builder", "🕸️  Graph Explorer"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown('<div class="cl-nav-label">About</div>', unsafe_allow_html=True)
    st.markdown(
        """
    <div style="font-size:0.8rem; color:#8b949e; line-height:1.6;">
    Retail customer intelligence powered by a Neo4j knowledge graph
    and Claude Sonnet. Ask questions in plain English — the app
    generates Cypher, queries the graph, and explains the results.
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown('<div class="cl-nav-label">Graph Stats</div>', unsafe_allow_html=True)

    @st.cache_data(ttl=300)
    def _graph_stats():
        try:
            from graph.loaders.neo4j_client import Neo4jClient

            with Neo4jClient() as c:
                c._database = None
                rows = c.run(
                    "MATCH (n) RETURN labels(n)[0] AS l, count(n) AS n ORDER BY n DESC"
                )
            return {r["l"]: r["n"] for r in rows if r["l"]}
        except Exception:
            return {}

    stats = _graph_stats()
    if stats:
        for label, count in stats.items():
            st.markdown(
                f'<div style="font-size:0.8rem;color:#8b949e;'
                f'display:flex;justify-content:space-between;padding:2px 0;">'
                f'<span>{label}</span><span style="color:#58a6ff;'
                f"font-family:'DM Mono',monospace;\">{count:,}</span></div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div style="font-size:0.8rem;color:#484f58;">Connect to Neo4j to see stats</div>',
            unsafe_allow_html=True,
        )

# ── Route to page ─────────────────────────────────────────────────────────────
if "Q&A" in page:
    from app._pages import qa_page

    qa_page.render()
elif "Report" in page:
    from app._pages import report_page

    report_page.render()
else:
    from app._pages import graph_page

    graph_page.render()
