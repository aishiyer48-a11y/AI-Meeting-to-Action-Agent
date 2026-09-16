from __future__ import annotations

import os
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()

import streamlit as st
from langgraph.types import Command

from agent.graph import build_graph
from database.crud import get_all_tasks
from database.db import init_db
from llm.schemas import MeetingAnalysis
from utils.helpers import read_transcript

init_db()

st.set_page_config(page_title="AI Meeting-to-Action Agent", page_icon="🤖", layout="wide")

if "graph" not in st.session_state:
    st.session_state.graph = build_graph()
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid4())
if "result" not in st.session_state:
    st.session_state.result = None
if "interrupt" not in st.session_state:
    st.session_state.interrupt = None
if "transcript" not in st.session_state:
    st.session_state.transcript = ""

config = {"configurable": {"thread_id": st.session_state.thread_id}}


def handle_run(run_result):
    st.session_state.result = run_result
    interrupts = run_result.get("__interrupt__", []) if isinstance(run_result, dict) else []
    st.session_state.interrupt = interrupts[0].value if interrupts else None


def start_analysis():
    text = st.session_state.input_transcript.strip()
    if not text:
        st.error("Please paste or upload a transcript first.")
        return
    st.session_state.transcript = text
    st.session_state.last_result = None
    try:
        handle_run(st.session_state.graph.invoke({"transcript": text}, config))
    except Exception as exc:
        st.error(f"Agent failed: {exc}")


def resume_agent(value):
    try:
        handle_run(st.session_state.graph.invoke(Command(resume=value), config))
    except Exception as exc:
        st.error(f"Agent resume failed: {exc}")


st.title("🤖 AI Meeting-to-Action Agent")
st.caption("TRANSCRIPT → UNDERSTAND → IDENTIFY ACTION → DECIDE TOOL → ASK APPROVAL → EXECUTE → CONFIRM")

with st.sidebar:
    st.subheader("Configuration")
    st.write(f"OpenAI model: `{os.getenv('OPENAI_MODEL', 'gpt-5.6-luna')}`")
    st.write("Calendar timezone: `Asia/Kolkata`")
    st.info("Calendar events are never created until you explicitly approve them.")

col1, col2 = st.columns([2, 1])
with col1:
    st.subheader("1. Transcript Input")
    uploaded = st.file_uploader("Upload transcript", type=["txt", "md", "csv", "docx", "pdf"])
    if uploaded:
        try:
            st.session_state.input_transcript = read_transcript(uploaded)
        except Exception as exc:
            st.error(str(exc))
    else:
        st.text_area("Paste transcript", height=220, key="input_transcript")
    st.button("Analyze Meeting", type="primary", on_click=start_analysis)

with col2:
    st.subheader("Agent State")
    if st.session_state.result:
        st.write(st.session_state.result.get("status", "Processing"))
    else:
        st.write("Waiting for transcript")

result = st.session_state.result
if result and result.get("analysis"):
    analysis = MeetingAnalysis.model_validate(result["analysis"])
    st.subheader("2. Structured Meeting Understanding")
    st.write("**Summary:**", analysis.meeting_summary)
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Key Points**")
        for item in analysis.key_points:
            st.write(f"- {item}")
    with c2:
        st.write("**Decisions**")
        for item in analysis.decisions:
            st.write(f"- {item}")

    st.subheader("3. Action Items")
    for i, action in enumerate(analysis.action_items, start=1):
        with st.container(border=True):
            st.write(f"**Action {i}: {action.action_type.value}**")
            data = action.model_dump(mode="json")
            st.json({k: v for k, v in data.items() if v not in (None, "", [], {})})

interrupt = st.session_state.interrupt
if interrupt:
    if interrupt.get("type") == "approval":
        st.subheader("4. Human Approval Required")
        event = interrupt["event"]
        st.warning("No Calendar API call has happened yet. Review the proposed event.")
        st.json(event)
        a, r = st.columns(2)
        with a:
            if st.button("✅ APPROVE", type="primary", width="stretch"):
                resume_agent("APPROVE")
                st.rerun()
        with r:
            if st.button("❌ REJECT", width="stretch"):
                resume_agent("REJECT")
                st.rerun()
    elif interrupt.get("type") == "clarification":
        st.subheader("4. Clarification Required")
        st.warning(interrupt["prompt"])
        answer = st.text_input("Your clarification", key="clarification_input")
        if st.button("Continue", type="primary") and answer.strip():
            resume_agent(answer.strip())
            st.rerun()

if result and result.get("last_result"):
    st.subheader("5. Result")
    outcome = result["last_result"]
    if outcome.get("type") == "calendar":
        if outcome.get("mock"):
            st.warning("DEMO MODE: simulated Calendar result. No Google Calendar API call was made.")
        else:
            st.success(outcome["message"])
        if outcome.get("html_link"):
            st.link_button("Open Google Calendar Event", outcome["html_link"])
    elif outcome.get("type") == "rejected":
        st.info(outcome["message"])
    elif outcome.get("type") == "task":
        st.success(outcome["message"])
    else:
        st.error(outcome.get("message", "Unknown result"))

st.subheader("SQLite Task Store")
tasks = get_all_tasks()
if tasks:
    st.dataframe(tasks, width="stretch", hide_index=True)
else:
    st.caption("No tasks stored yet.")
