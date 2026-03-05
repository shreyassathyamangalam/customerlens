"""
app/_pages/qa_page.py
======================
Q&A Chat page — two modes:

  Chain Mode  (default)  GraphCypherQAChain — free-form Cypher generation.
                         Best for ad-hoc exploration.
                         Inspector shows: generated Cypher · raw result rows

  Agent Mode             Tool-calling ReAct agent with 13 pre-built tools.
                         Best for multi-hop questions and reliable production use.
                         Inspector shows: reasoning chain (tool name -> data -> answer)
"""

from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import streamlit as st

# ── Suggested questions split by mode ────────────────────────────────────────

CHAIN_QUESTIONS = [
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

AGENT_QUESTIONS = [
    "Compare AOV and recency across all segments, then tell me which needs the most urgent attention.",
    "Which At-Risk customers have the highest lifetime spend and where are they located?",
    "Which campaigns were most effective and which segments actually responded to them?",
    "Give me a complete churn risk summary: revenue at stake, worst cities, top customers to re-engage.",
    "What products should I bundle together and which segments are most likely to buy them?",
    "Compare channel preferences across segments and identify any surprising patterns.",
    "Which customers responded to more than one campaign and how valuable are they?",
    "What are the top cross-sell opportunities for Champions vs At-Risk customers?",
]

# ── Cached backends ───────────────────────────────────────────────────────────


@st.cache_resource(show_spinner=False)
def _get_chain():
    from llm.chains.qa_chain import build_qa_chain

    return build_qa_chain(verbose=False, return_intermediate_steps=True)


@st.cache_resource(show_spinner=False)
def _get_agent():
    from llm.chains.agent_chain import get_agent

    return get_agent()


# ── State ─────────────────────────────────────────────────────────────────────


def _init_state():
    defaults = {
        "messages": [],
        "pending_question": "",
        "selected_suggestion": "",
        "agent_mode": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── Backend calls ─────────────────────────────────────────────────────────────


def _ask_chain(question: str) -> dict:
    chain = _get_chain()
    result = chain.invoke({"query": question})
    steps = result.get("intermediate_steps", [])
    cypher = steps[0].get("query", "").strip() if steps else ""
    raw_rows = steps[1].get("context", []) if len(steps) > 1 else []
    return {
        "mode": "chain",
        "question": question,
        "cypher": cypher,
        "rows": raw_rows,
        "answer": result.get("result", "").strip(),
        "steps": [],
        "ts": datetime.now().strftime("%H:%M"),
    }


def _ask_agent(question: str) -> dict:
    agent = _get_agent()
    result = agent.invoke(question)
    return {
        "mode": "agent",
        "question": question,
        "cypher": "",
        "rows": [],
        "answer": result.answer,
        "steps": result.steps,
        "error": result.error,
        "ts": datetime.now().strftime("%H:%M"),
    }


# ── Message rendering ─────────────────────────────────────────────────────────


def _render_message(msg: dict, idx: int):
    is_agent = msg["mode"] == "agent"
    badge_color = "#a371f7" if is_agent else "#58a6ff"
    badge_label = "Agent" if is_agent else "Chain"

    # Question bubble + mode badge
    st.markdown(
        f'<div style="display:flex;justify-content:flex-end;'
        f'align-items:flex-start;gap:8px;margin-bottom:8px;">'
        f'<div style="background:#0d1117;color:#e6edf3;border-radius:12px 12px 0 12px;'
        f'padding:12px 18px;max-width:80%;font-size:0.9rem;line-height:1.5;">'
        f"{msg['question']}</div>"
        f'<div style="background:{badge_color}22;border:1px solid {badge_color}55;'
        f"color:{badge_color};font-size:0.65rem;font-weight:700;letter-spacing:0.07em;"
        f"text-transform:uppercase;padding:3px 8px;border-radius:20px;"
        f'white-space:nowrap;margin-top:6px;">{badge_label}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )

    answer = msg.get("answer", "")
    if answer:
        st.markdown(f'<div class="cl-answer">{answer}</div>', unsafe_allow_html=True)
    else:
        st.warning("No answer was returned for this question.")

    if is_agent and msg.get("steps"):
        _render_agent_steps(msg["steps"], idx)
    elif not is_agent:
        _render_chain_inspector(msg, idx)

    st.markdown(
        f'<div style="font-size:0.72rem;color:#8b949e;text-align:right;margin-top:4px;">'
        f"{msg['ts']}</div>",
        unsafe_allow_html=True,
    )
    st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)


def _render_chain_inspector(msg: dict, idx: int):
    col1, col2 = st.columns(2)
    with col1:
        if msg.get("cypher"):
            key = f"cypher_open_{idx}"
            st.session_state.setdefault(key, False)
            lbl = (
                "▼ Hide Cypher" if st.session_state[key] else "▶ View generated Cypher"
            )
            if st.button(lbl, key=f"toggle_cypher_{idx}"):
                st.session_state[key] = not st.session_state[key]
                st.rerun()
            if st.session_state[key]:
                st.markdown(
                    f'<div class="cl-cypher">{msg["cypher"]}</div>',
                    unsafe_allow_html=True,
                )
    with col2:
        if msg.get("rows"):
            key = f"rows_open_{idx}"
            st.session_state.setdefault(key, False)
            lbl = (
                "▼ Hide data"
                if st.session_state[key]
                else f"▶ Raw data ({len(msg['rows'])} rows)"
            )
            if st.button(lbl, key=f"toggle_rows_{idx}"):
                st.session_state[key] = not st.session_state[key]
                st.rerun()
            if st.session_state[key]:
                st.dataframe(
                    pd.DataFrame(msg["rows"]), width="stretch", hide_index=True
                )


def _render_agent_steps(steps: list, idx: int):
    key = f"steps_open_{idx}"
    st.session_state.setdefault(key, False)
    n = len(steps)
    lbl = (
        "▼ Hide reasoning chain"
        if st.session_state[key]
        else f"▶ View reasoning chain ({n} tool call{'s' if n != 1 else ''})"
    )

    if st.button(lbl, key=f"toggle_steps_{idx}"):
        st.session_state[key] = not st.session_state[key]
        st.rerun()

    if not st.session_state[key]:
        return

    for i, step in enumerate(steps):
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;margin:12px 0 6px 0;">'
            f'<div style="background:#161b22;border:1px solid #30363d;border-radius:20px;'
            f"padding:3px 12px;font-family:'DM Mono',monospace;font-size:0.75rem;"
            f'color:#a371f7;white-space:nowrap;">Step {i + 1} · {step.tool_name}</div>'
            f'<div style="height:1px;background:#21262d;flex:1;"></div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        if step.tool_input:
            st.markdown(
                f'<div style="font-size:0.75rem;color:#8b949e;margin-bottom:4px;">'
                f'Input: <code style="color:#79c0ff;">{json.dumps(step.tool_input)}</code></div>',
                unsafe_allow_html=True,
            )
        try:
            rows = json.loads(step.tool_output)
            if isinstance(rows, list) and rows:
                st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
            else:
                st.markdown(
                    f'<div class="cl-cypher">{step.tool_output[:400]}</div>',
                    unsafe_allow_html=True,
                )
        except (json.JSONDecodeError, ValueError):
            st.markdown(
                f'<div class="cl-cypher">{step.tool_output[:400]}</div>',
                unsafe_allow_html=True,
            )


def _render_suggestions(questions: list[str]):
    selected_q = st.session_state.get("selected_suggestion", "")
    css = ""
    for q in questions:
        esc = q.replace('"', '\\"')
        if q == selected_q:
            css += f"""button[aria-label="{esc}"] {{
                background:#0d4a6e!important;border-color:#58a6ff!important;
                color:#ffffff!important;box-shadow:0 0 0 2px rgba(88,166,255,.35)!important;}}"""
        else:
            css += f"""button[aria-label="{esc}"] {{
                background:#0d1117!important;border-color:#30363d!important;color:#e6edf3!important;}}
            button[aria-label="{esc}"]:hover {{
                background:#161b22!important;border-color:#58a6ff!important;}}"""
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    cols = st.columns(2)
    for i, q in enumerate(questions):
        with cols[i % 2]:
            if st.button(q, key=f"sug_{i}", width="stretch"):
                st.session_state.selected_suggestion = q
                st.session_state.pending_question = q
                st.rerun()


# ── Main render ───────────────────────────────────────────────────────────────


def render():
    _init_state()
    agent_mode = st.session_state.agent_mode

    # ── Header + mode toggle ──────────────────────────────────────────────────
    col_header, col_toggle = st.columns([7, 3])

    with col_header:
        mode_label = "Agent Mode" if agent_mode else "Chain Mode"
        mode_color = "#a371f7" if agent_mode else "#58a6ff"
        sub = (
            "Multi-step reasoning · 13 pre-built tools · Reliable production queries"
            if agent_mode
            else "Plain-English questions → Cypher queries → graph results → Claude explanations"
        )
        st.markdown(
            f"""
        <div class="cl-header">
          <div class="cl-badge" style="background:{mode_color}22;
               border-color:{mode_color}55;color:{mode_color};">{mode_label}</div>
          <div class="cl-header-title">Ask Your Customer Graph</div>
          <div class="cl-header-sub">{sub}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col_toggle:
        st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
        st.markdown(
            """<div style="font-size:0.75rem;font-weight:600;color:#57606a;
            text-transform:uppercase;letter-spacing:0.07em;margin-bottom:8px;">
            Query mode</div>""",
            unsafe_allow_html=True,
        )

        # Styled toggle buttons
        toggle_css = ""
        for lbl, active, color in [
            ("⛓  Chain", not agent_mode, "#58a6ff"),
            ("🤖  Agent", agent_mode, "#a371f7"),
        ]:
            esc = lbl.replace('"', '\\"')
            if active:
                toggle_css += f"""button[aria-label="{esc}"] {{
                    background:{color}22!important;border-color:{color}!important;
                    color:{color}!important;font-weight:600!important;}}"""
            else:
                toggle_css += f"""button[aria-label="{esc}"] {{
                    background:#0d1117!important;border-color:#30363d!important;color:#8b949e!important;}}
                button[aria-label="{esc}"]:hover {{
                    border-color:{color}!important;color:{color}!important;}}"""
        st.markdown(f"<style>{toggle_css}</style>", unsafe_allow_html=True)

        tc1, tc2 = st.columns(2)
        with tc1:
            if st.button("⛓  Chain", width="stretch", key="btn_chain"):
                if agent_mode:
                    st.session_state.update(
                        {"agent_mode": False, "messages": [], "selected_suggestion": ""}
                    )
                    st.rerun()
        with tc2:
            if st.button("🤖  Agent", width="stretch", key="btn_agent"):
                if not agent_mode:
                    st.session_state.update(
                        {"agent_mode": True, "messages": [], "selected_suggestion": ""}
                    )
                    st.rerun()

        # Info card
        if agent_mode:
            st.markdown(
                """<div style="background:#1c1336;border:1px solid #a371f755;
                border-radius:8px;padding:10px 14px;margin-top:8px;
                font-size:0.78rem;color:#c9b3f5;line-height:1.6;">
                🤖 <strong>Agent Mode</strong><br>
                Claude reasons step-by-step, calling pre-built graph tools.
                Best for multi-part questions. Shows full reasoning chain.
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """<div style="background:#0d2137;border:1px solid #58a6ff55;
                border-radius:8px;padding:10px 14px;margin-top:8px;
                font-size:0.78rem;color:#79c0ff;line-height:1.6;">
                ⛓ <strong>Chain Mode</strong><br>
                Generates a single Cypher query per question.
                Best for ad-hoc exploration. Shows generated Cypher.
                </div>""",
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
        _render_suggestions(AGENT_QUESTIONS if agent_mode else CHAIN_QUESTIONS)
        st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)

    # ── Conversation history ──────────────────────────────────────────────────
    for idx, msg in enumerate(st.session_state.messages):
        _render_message(msg, idx)

    # ── Input bar ─────────────────────────────────────────────────────────────
    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    ci, cb, cc = st.columns([8, 1.2, 1])

    with ci:
        question = st.text_input(
            "question_input",
            value=st.session_state.pending_question,
            placeholder=(
                "e.g. Compare churn risk revenue across segments and identify top customers to re-engage."
                if agent_mode
                else "e.g. Which segment has the highest average order value?"
            ),
            label_visibility="collapsed",
            key="question_input",
        )
    with cb:
        ask_clicked = st.button("Ask →", width="content")
    with cc:
        if st.button("Clear", width="content"):
            st.session_state.update(
                {"messages": [], "pending_question": "", "selected_suggestion": ""}
            )
            st.rerun()

    # ── Fire ─────────────────────────────────────────────────────────────────
    trigger = (
        question
        if ask_clicked and question.strip()
        else st.session_state.pending_question
    )

    if trigger and trigger.strip():
        st.session_state.pending_question = ""
        with st.spinner("Agent reasoning…" if agent_mode else "Querying graph…"):
            try:
                msg = (
                    _ask_agent(trigger.strip())
                    if agent_mode
                    else _ask_chain(trigger.strip())
                )
                st.session_state.messages.append(msg)
            except Exception as exc:
                st.error(f"Something went wrong: {exc}")
        st.rerun()
