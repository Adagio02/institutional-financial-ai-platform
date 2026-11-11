"""Ask FinAI - chat with your FinAI research platform, powered by Claude.

Start with scripts\\start_ask_finai.ps1 (it loads the encrypted API key).
Read-only by default: jobs run only after you click Confirm. No trading.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import streamlit as st  # noqa: E402

from finai.assistant import claude_client, knowledge  # noqa: E402
from finai.assistant.jobs import JOBS, run_job  # noqa: E402

st.set_page_config(page_title="Ask FinAI", page_icon=":speech_balloon:", layout="wide")

API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("FINAI_CLAUDE_MODEL", claude_client.DEFAULT_MODEL)

SUGGESTIONS = [
    "Give me a status overview of the platform today.",
    "How close is V009 to its next milestone, and what happens at 13, 26 and 52 periods?",
    "Why did each V5.6 research version fail its gates?",
    "How are the H0, H3 and H5 shadow strategies doing, and when can they be judged?",
    "Is the daily data collection healthy? Show the last few runs.",
    "Explain why the legacy V4.1 intraday models lose money.",
]

if "messages" not in st.session_state:
    st.session_state.messages = []      # full API conversation (with tool blocks)
    st.session_state.display = []       # what the user sees: (role, text, tool_calls)
    st.session_state.pending_job = None
    st.session_state.tokens = {"input_tokens": 0, "output_tokens": 0}


def ask(question: str) -> None:
    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.display.append(("user", question, []))
    try:
        with st.spinner("Looking through your FinAI artifacts..."):
            result = claude_client.run_turn(st.session_state.messages, API_KEY, MODEL)
    except claude_client.ClaudeError as exc:
        st.session_state.messages.pop()
        st.session_state.display.append(("error", str(exc), []))
        return
    st.session_state.messages = result.messages
    st.session_state.display.append(("assistant", result.text or "(no answer)", result.tool_calls))
    st.session_state.pending_job = result.pending_job
    for key, value in result.usage.items():
        st.session_state.tokens[key] += value


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("Ask FinAI")
    st.caption("Claude answers from your project's artifacts, logs and research reports.")
    if API_KEY:
        st.success(f"Claude connected - {MODEL}")
    else:
        st.error("No Anthropic API key loaded.")
        st.markdown(
            "1. Run `scripts\\set_anthropic_key.ps1` once to store your key (encrypted).\n"
            "2. Start this page with `scripts\\start_ask_finai.ps1`."
        )
    st.divider()
    st.markdown("**Try asking**")
    for index, suggestion in enumerate(SUGGESTIONS):
        if st.button(suggestion, key=f"suggest_{index}", width="stretch", disabled=not API_KEY):
            ask(suggestion)
            st.rerun()
    st.divider()
    if st.button("New conversation", width="stretch"):
        for key in ("messages", "display", "pending_job"):
            st.session_state.pop(key, None)
        st.rerun()
    tokens = st.session_state.tokens
    st.caption(f"Tokens this session: {tokens['input_tokens']:,} in / {tokens['output_tokens']:,} out")
    st.caption("Read-only. Jobs run only after you confirm. Cannot trade. Not financial advice.")

# ---------------------------------------------------------------- chat
st.header("Ask FinAI")
st.caption(
    "Primary program: V5.6 research and the V009 performance-blind forward test. "
    "The V4.1 1-minute AAPL loop is legacy."
)

for role, text, tool_calls in st.session_state.display:
    if role == "error":
        st.error(text)
        continue
    with st.chat_message(role):
        st.markdown(text)
        if tool_calls:
            with st.expander(f"Looked up {len(tool_calls)} item(s)"):
                for call in tool_calls:
                    st.code(f"{call['tool']}({call['input'] or ''})", language="text")

pending = st.session_state.pending_job
if pending:
    job = JOBS[pending["job"]]
    with st.container(border=True):
        st.markdown(f"**Claude proposes a job: {job.title}**")
        st.write(job.description)
        if pending.get("reason"):
            st.caption(f"Why: {pending['reason']}")
        confirm, cancel = st.columns(2)
        if confirm.button("Confirm and run", type="primary", width="stretch"):
            st.session_state.pending_job = None
            with st.spinner(f"Running: {job.title} (this can take several minutes)..."):
                outcome = run_job(job.key)
            summary = "succeeded" if outcome.get("ok") else "failed"
            st.session_state.display.append(
                ("assistant", f"Job **{job.title}** {summary}.\n\n```\n{outcome.get('output_tail', outcome.get('error', ''))[-2500:]}\n```", [])
            )
            ask(f"The job '{job.title}' finished ({summary}). Explain the result briefly: {knowledge.redact(str(outcome))[:4000]}")
            st.rerun()
        if cancel.button("Cancel", width="stretch"):
            st.session_state.pending_job = None
            st.session_state.display.append(("assistant", "Okay, I did not run it.", []))
            st.rerun()

question = st.chat_input("Ask about your research, models, data or governance...", disabled=not API_KEY)
if question:
    ask(question)
    st.rerun()
