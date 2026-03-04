"""
app/pages/qa_page.py
=====================
Q&A Chat page — users ask natural-language questions, the app
generates Cypher, queries Neo4j, and Claude explains the results.

Features:
  - Conversation history (this session)
  - Expandable Cypher inspector per answer
  - Raw result table toggle
  - Suggested starter questions
  - Per-answer copy button
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

SUGGESTED_QUESTIONS = [
    "Which customer segment has the highest average order value?",
    "How many customers are in each RFM segment?",
    "Who are the top 5 customers by lifetime spend?",
    "Which cities have the most Champions customers?",
    "What are the top 10 products by total revenue?",
    "Which product categories are most popular among Champions?",
    "How many customers responded to more than one campaign?",
    "Compare email vs SMS campaign response counts.",
    "Show customers in the At-Risk segment from New York.",
    "What is the average number of products per order by channel?",
]


@st.cache_resource(show_spinner=False)
def _get_chain():
    from llm.chains.qa_chain import build_qa_chain

    return build_qa_chain(verbose=False, return_intermediate_steps=True)


def _init_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []  # list of {question, cypher, rows, answer, ts}
    if "pending_question" not in st.session_state:
        st.session_state.pending_question = ""


def _ask(chain, question: str) -> dict:
    result = chain.invoke({"query": question})
    steps = result.get("intermediate_steps", [])
    cypher = steps[0].get("query", "").strip() if steps else ""
    raw_rows = steps[1].get("context", []) if len(steps) > 1 else []
    return {
        "question": question,
        "cypher": cypher,
        "rows": raw_rows,
        "answer": result.get("result", "").strip(),
        "ts": datetime.now().strftime("%H:%M"),
    }


def _render_message(msg: dict, idx: int):
    """Render one Q&A exchange."""
    # Question bubble
    st.markdown(
        f'<div style="display:flex;justify-content:flex-end;margin-bottom:8px;">'
        f'<div style="background:#0d1117;color:#e6edf3;border-radius:12px 12px 0 12px;'
        f'padding:12px 18px;max-width:80%;font-size:0.9rem;line-height:1.5;">'
        f"{msg['question']}"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    # Answer card
    with st.container():
        if msg["answer"]:
            st.markdown(
                f'<div class="cl-answer">{msg["answer"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.warning("No answer was returned for this question.")

        # Expandable details — rendered as styled pill buttons + conditional blocks
        col1, col2 = st.columns([1, 1])
        with col1:
            if msg["cypher"]:
                cypher_key = f"cypher_open_{idx}"
                if cypher_key not in st.session_state:
                    st.session_state[cypher_key] = False
                label = (
                    "▼ Hide Cypher"
                    if st.session_state[cypher_key]
                    else "▶ View generated Cypher"
                )
                st.markdown(
                    "<style>"
                    'div[data-testid="stButton"] button[kind="secondary"] {'
                    "  background:#1c2333 !important; color:#79c0ff !important;"
                    "  border:1px solid #30363d !important; font-size:0.8rem !important;"
                    "}"
                    "</style>",
                    unsafe_allow_html=True,
                )
                if st.button(label, key=f"toggle_cypher_{idx}"):
                    st.session_state[cypher_key] = not st.session_state[cypher_key]
                    st.rerun()
                if st.session_state[cypher_key]:
                    st.markdown(
                        f'<div class="cl-cypher">{msg["cypher"]}</div>',
                        unsafe_allow_html=True,
                    )
        with col2:
            if msg["rows"]:
                rows_key = f"rows_open_{idx}"
                if rows_key not in st.session_state:
                    st.session_state[rows_key] = False
                label2 = (
                    "▼ Hide data"
                    if st.session_state[rows_key]
                    else f"▶ Raw data ({len(msg['rows'])} rows)"
                )
                if st.button(label2, key=f"toggle_rows_{idx}"):
                    st.session_state[rows_key] = not st.session_state[rows_key]
                    st.rerun()
                if st.session_state[rows_key]:
                    df = pd.DataFrame(msg["rows"])
                    st.dataframe(df, width="stretch", hide_index=True)

        st.markdown(
            f'<div style="font-size:0.72rem;color:#8b949e;'
            f'text-align:right;margin-top:4px;">{msg["ts"]}</div>',
            unsafe_allow_html=True,
        )
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)


def render():
    _init_state()

    # ── Page header ───────────────────────────────────────────────────────────
    st.markdown(
        """
    <div class="cl-header">
      <div class="cl-badge">Q&A Chat</div>
      <div class="cl-header-title">Ask Your Customer Graph</div>
      <div class="cl-header-sub">
        Plain-English questions → Cypher queries → graph results → Claude explanations
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ── Suggested questions ───────────────────────────────────────────────────
    if not st.session_state.messages:
        st.markdown(
            '<div style="font-size:0.8rem;font-weight:600;color:#57606a;'
            'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px;">'
            "Suggested questions</div>",
            unsafe_allow_html=True,
        )
        cols = st.columns(2)
        for i, q in enumerate(SUGGESTED_QUESTIONS):
            with cols[i % 2]:
                if st.button(
                    q,
                    key=f"sug_{i}",
                    width="content",
                ):
                    st.session_state.pending_question = q
                    st.rerun()

        st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)

    # ── Conversation history ──────────────────────────────────────────────────
    for idx, msg in enumerate(st.session_state.messages):
        _render_message(msg, idx)

    # ── Input bar ─────────────────────────────────────────────────────────────
    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    col_input, col_btn, col_clear = st.columns([8, 1.2, 1])

    with col_input:
        question = st.text_input(
            "question_input",
            value=st.session_state.pending_question,
            placeholder="e.g. Which segment has the highest average order value?",
            label_visibility="collapsed",
            key="question_input",
        )

    with col_btn:
        ask_clicked = st.button("Ask →", width="content")

    with col_clear:
        if st.button("Clear", width="content"):
            st.session_state.messages = []
            st.session_state.pending_question = ""
            st.rerun()

    # ── Trigger on button click or Enter (pending question) ──────────────────
    trigger = (
        question
        if ask_clicked and question.strip()
        else st.session_state.pending_question
    )

    if trigger and trigger.strip():
        st.session_state.pending_question = ""

        with st.spinner("Querying graph…"):
            try:
                chain = _get_chain()
                msg = _ask(chain, trigger.strip())
                st.session_state.messages.append(msg)
            except Exception as exc:
                st.error(f"Something went wrong: {exc}")

        st.rerun()
