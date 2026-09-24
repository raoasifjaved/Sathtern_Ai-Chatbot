from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from ai_service import AIService, AIServiceError
from config import settings
from database import Database
from memory import save_extracted_memory
from prompts import MODES, build_system_prompt
from utils import friendly_timestamp, markdown_export, pdf_export

st.set_page_config(
    page_title="Sathtern AI Chatbot",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB = Database()
AI = AIService()


# ---------- Styling ----------
st.markdown(
    """
<style>
:root { --accent: #7c5cff; --accent2: #00c2a8; }
.main { max-width: 1450px; }
.hero { padding: 28px 30px; border-radius: 24px; background: linear-gradient(135deg,#10182f 0%,#20234c 50%,#123d45 100%); color: white; border: 1px solid rgba(255,255,255,.08); box-shadow: 0 12px 35px rgba(0,0,0,.18); }
.hero h1 { margin: 0 0 7px 0; font-size: 34px; }
.hero p { margin: 0; opacity: .87; font-size: 15px; line-height: 1.6; }
.badge { display: inline-block; padding: 4px 10px; border-radius: 99px; background: rgba(255,255,255,.1); margin-bottom: 12px; font-size: 12px; }
.section-title { font-size: 15px; font-weight: 700; margin: 12px 0 8px 0; }
.metric-card { padding: 14px 16px; border: 1px solid rgba(128,128,128,.18); border-radius: 16px; background: rgba(128,128,128,.05); }
.small-muted { color: rgba(127,127,127,.95); font-size: 12px; }
.example { padding: 9px 11px; border-radius: 12px; background: rgba(124,92,255,.08); border: 1px solid rgba(124,92,255,.18); margin: 7px 0; }
</style>
""",
    unsafe_allow_html=True,
)


# ---------- Session bootstrap ----------
if "project_id" not in st.session_state:
    projects = DB.list_projects()
    if projects:
        st.session_state.project_id = projects[0]["id"]
    else:
        st.session_state.project_id = DB.create_project("My First Sathtern AI Project", "A new AI software engineering workspace.")

project_id = int(st.session_state.project_id)
project = DB.get_project(project_id)
if not project:
    st.session_state.project_id = DB.create_project("My First Sathtern AI Project")
    project_id = int(st.session_state.project_id)
    project = DB.get_project(project_id)

conversations = DB.list_conversations(project_id)
if not conversations:
    conversation_id = DB.create_conversation(project_id)
else:
    if "conversation_id" not in st.session_state or not DB.get_conversation(int(st.session_state.conversation_id)):
        st.session_state.conversation_id = conversations[0]["id"]
    conversation_id = int(st.session_state.conversation_id)

if "mode" not in st.session_state:
    st.session_state.mode = "Idea Analyzer"


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## 🧠 Sathtern AI Chatbot")
    st.caption("AI Software Engineering Workspace")

    if st.button("＋ New Project", use_container_width=True):
        new_id = DB.create_project("Untitled Project", "Describe the project objective and constraints here.")
        st.session_state.project_id = new_id
        st.session_state.conversation_id = DB.list_conversations(new_id)[0]["id"]
        st.rerun()

    projects = DB.list_projects()
    project_labels = {row["id"]: row["name"] for row in projects}
    current_index = list(project_labels).index(project_id) if project_id in project_labels else 0
    selected_project = st.selectbox(
        "Projects",
        list(project_labels.keys()),
        index=current_index,
        format_func=lambda x: project_labels[x],
        key="project_selector",
    )
    if int(selected_project) != project_id:
        st.session_state.project_id = int(selected_project)
        st.session_state.pop("conversation_id", None)
        st.rerun()

    project = DB.get_project(project_id)
    conversations = DB.list_conversations(project_id)
    conv_ids = [row["id"] for row in conversations]
    conv_titles = {row["id"]: row["title"] for row in conversations}
    current_conv = int(st.session_state.get("conversation_id", conv_ids[0]))
    if current_conv not in conv_ids:
        current_conv = conv_ids[0]
        st.session_state.conversation_id = current_conv

    if st.button("＋ New Conversation", use_container_width=True):
        new_conv = DB.create_conversation(project_id, "New Conversation")
        st.session_state.conversation_id = new_conv
        st.rerun()

    selected_conv = st.selectbox(
        "Conversations",
        conv_ids,
        index=conv_ids.index(current_conv),
        format_func=lambda x: conv_titles[x],
        key="conversation_selector",
    )
    if int(selected_conv) != current_conv:
        st.session_state.conversation_id = int(selected_conv)
        st.rerun()

    st.divider()
    st.markdown("### AI Mode")
    st.session_state.mode = st.selectbox("Choose workflow", list(MODES), index=list(MODES).index(st.session_state.mode))

    with st.expander("Project settings"):
        new_name = st.text_input("Name", value=project["name"])
        new_desc = st.text_area("Description", value=project["description"], height=100)
        if st.button("Save project", use_container_width=True):
            DB.update_project(project_id, name=new_name, description=new_desc)
            st.success("Saved")
            st.rerun()
        if st.button("Delete project", use_container_width=True):
            projects_now = DB.list_projects()
            DB.delete_project(project_id)
            remaining = [p for p in projects_now if p["id"] != project_id]
            if remaining:
                st.session_state.project_id = remaining[0]["id"]
            else:
                st.session_state.project_id = DB.create_project("My First Sathtern AI Project")
            st.session_state.pop("conversation_id", None)
            st.rerun()

    if st.button("🧹 Clear current conversation", use_container_width=True):
        DB.clear_conversation(current_conv)
        st.rerun()

    api_status = "Connected" if AI.available else "Demo mode"
    st.divider()
    st.markdown(f"**AI status:** {api_status}")
    st.caption(f"Model: `{settings.groq_model}`")
    if not AI.available:
        st.caption("Set `GROQ_API_KEY` to enable live AI responses.")


# ---------- Main header ----------
st.markdown(
    f"""
<div class="hero">
  <div class="badge">PROJECT INTELLIGENCE PLATFORM</div>
  <h1>{project['name']}</h1>
  <p>{project['description'] or 'Transform software ideas into architecture, implementation plans, tests, and engineering decisions.'}</p>
</div>
""",
    unsafe_allow_html=True,
)

stats = DB.stats(project_id)
col1, col2, col3, col4 = st.columns(4)
for col, label, value in [
    (col1, "Messages", stats["messages"]),
    (col2, "Tasks", stats["tasks"]),
    (col3, "Completed", stats["completed_tasks"]),
    (col4, "Conversations", stats["conversations"]),
]:
    with col:
        st.markdown(f'<div class="metric-card"><div class="small-muted">{label}</div><div style="font-size:25px;font-weight:800">{value}</div></div>', unsafe_allow_html=True)


# ---------- Tabs ----------
tab_chat, tab_project, tab_search, tab_export = st.tabs(["💬 Workspace", "🧩 Project Memory", "🔎 Search", "📦 Export"])

with tab_chat:
    messages = DB.list_messages(current_conv)
    if not messages:
        st.markdown("### Start with an idea")
        st.write("Describe a product, feature, codebase, architecture decision, or engineering problem. Sathtern AI will build the context from there.")
        examples = [
            "Design an AI-powered education platform for university students.",
            "Create a scalable architecture for an intelligent inventory system.",
            "Review the security of my FastAPI authentication flow.",
            "Generate a testing strategy for a Streamlit + SQLite application.",
        ]
        for i, example in enumerate(examples):
            st.markdown(f'<div class="example">💡 {example}</div>', unsafe_allow_html=True)
            if st.button("Use this idea", key=f"ex_{i}"):
                st.session_state.pending_prompt = example
                st.rerun()

    for message in messages:
        if message["role"] not in {"user", "assistant"}:
            continue
        with st.chat_message("user" if message["role"] == "user" else "assistant"):
            st.markdown(message["content"])
            st.caption(f"{friendly_timestamp(message['created_at'])}{' · ' + message['mode'] if message['mode'] else ''}")

    pending = st.session_state.pop("pending_prompt", "")
    prompt = st.chat_input("Ask about your project…", key="chat_input")
    user_text = prompt or pending

    if user_text:
        DB.add_message(current_conv, "user", user_text, st.session_state.mode)
        history_rows = DB.list_messages(current_conv, limit=settings.max_history_messages)
        history = [{"role": row["role"], "content": row["content"]} for row in history_rows[:-1] if row["role"] in {"user", "assistant"}]
        memory = DB.get_memory(project_id)
        tasks = [dict(row) for row in DB.list_tasks(project_id)]
        project_dict = dict(project)
        system_prompt = build_system_prompt(st.session_state.mode, project_dict, memory, tasks)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            collected: list[str] = []

            def on_token(token: str) -> None:
                collected.append(token)
                placeholder.markdown("".join(collected) + "▌")

            with st.spinner("Thinking through the engineering context…"):
                try:
                    answer = AI.respond(
                        user_text=user_text,
                        system_prompt=system_prompt,
                        history=history,
                        stream=AI.available,
                        on_token=on_token if AI.available else None,
                    )
                except AIServiceError as exc:
                    answer = f"**AI request could not be completed.**\n\n{exc}\n\nYou can still use demo mode features, or configure `GROQ_API_KEY`."
            placeholder.markdown(answer)
            st.caption(f"{st.session_state.mode} · just now")

        DB.add_message(current_conv, "assistant", answer, st.session_state.mode)
        save_extracted_memory(DB, project_id, user_text, answer)

        if "new conversation" not in conv_titles[current_conv].lower() and len(history) == 0:
            title = " ".join(user_text.split()[:6]).strip() or "Conversation"
            DB.update_project(project_id, description=project["description"])
            with DB.connect() as conn:
                conn.execute("UPDATE conversations SET title=?, updated_at=? WHERE id=?", (title[:60], __import__('database').utc_now(), current_conv))
        st.rerun()

with tab_project:
    memory = DB.get_memory(project_id)
    left, right = st.columns([1.05, 1.2])
    with left:
        st.markdown("### Saved technical decisions")
        if memory:
            for key, value in memory.items():
                st.write(f"**{key.title()}**: {value}")
        else:
            st.info("Important choices are learned from conversation context and saved here automatically when they are confidently detected.")
    with right:
        st.markdown("### Project tasks")
        tasks = DB.list_tasks(project_id)
        for task in tasks:
            checked = st.checkbox(task["title"], value=bool(task["completed"]), key=f"task_{task['id']}")
            if checked != bool(task["completed"]):
                DB.set_task_completed(task["id"], checked)
                st.rerun()
        new_task = st.text_input("Add a task", key="new_task")
        if st.button("Add task") and new_task.strip():
            DB.add_task(project_id, new_task)
            st.rerun()

with tab_search:
    st.markdown("### Search project conversations")
    q = st.text_input("Search for requirements, decisions, errors, technologies…")
    if q.strip():
        results = DB.search_messages(project_id, q)
        if not results:
            st.info("No matching messages.")
        for row in results:
            st.markdown(f"**{row['role'].title()} · {row['conversation_title']}**")
            st.write(row["content"][:1000])
            st.caption(friendly_timestamp(row["created_at"]))
            st.divider()

with tab_export:
    st.markdown("### Export this project")
    all_messages = [dict(row) for row in DB.list_messages(current_conv)]
    memory = DB.get_memory(project_id)
    tasks = [dict(row) for row in DB.list_tasks(project_id)]
    project_dict = dict(project)
    markdown = markdown_export(project_dict, all_messages, memory, tasks)
    st.download_button("⬇️ Download Markdown", data=markdown.encode("utf-8"), file_name="sathtern_ai_project.md", mime="text/markdown")
    try:
        pdf = pdf_export(project_dict, all_messages, memory, tasks)
        st.download_button("⬇️ Download PDF", data=pdf, file_name="sathtern_ai_project.pdf", mime="application/pdf")
    except RuntimeError as exc:
        st.warning(str(exc))
    st.download_button(
        "⬇️ Download TXT",
        data=markdown.replace("# ", "").encode("utf-8"),
        file_name="sathtern_ai_project.txt",
        mime="text/plain",
    )
    st.caption("Exports contain the currently selected project's saved memory, tasks, and conversation history.")

st.caption("Sathtern AI Chatbot · Streamlit + SQLite + Groq-compatible chat API")
