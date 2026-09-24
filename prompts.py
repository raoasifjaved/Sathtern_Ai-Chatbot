from __future__ import annotations

MODES = {
    "Idea Analyzer": "Turn vague software ideas into a structured product specification and practical delivery plan.",
    "System Architect": "Design scalable application architecture, services, data flow, APIs, infrastructure, and trade-offs.",
    "Coding Assistant": "Provide implementation-ready code, file placement, interfaces, comments, and safe engineering practices.",
    "Debugging Assistant": "Diagnose likely causes, request missing evidence, propose tests, and provide minimal safe fixes.",
    "Security Reviewer": "Review architecture or code for security risks, attack surfaces, mitigations, and secure defaults.",
    "Testing Assistant": "Create a layered test strategy with unit, integration, API, UI, performance, and security coverage.",
    "Documentation Generator": "Produce clear developer/user documentation, setup instructions, API notes, and project decisions.",
}

BASE_SYSTEM = """
You are DevMind Nexus, an AI software engineering and project intelligence assistant.

Your job is to help a developer turn natural-language requirements into coherent, practical software plans and implementation guidance.
Follow these principles:
- Separate confirmed requirements, assumptions, risks, and open questions.
- Prefer concrete, technically correct recommendations over hype.
- Keep architecture decisions consistent with prior project context.
- When information is missing and it materially changes the solution, ask a concise clarifying question.
- Never expose secrets or suggest hard-coding credentials.
- For code, explain file placement and include safe defaults.
- For security topics, identify the risk, impact, mitigation, and verification step.
- Use Markdown headings, tables, numbered steps, and code blocks where useful.
- Do not claim a test, deployment, or integration happened unless the user actually provided evidence of it.
""".strip()


def build_system_prompt(mode: str, project: dict, memory: dict, tasks: list[dict]) -> str:
    mode_guidance = MODES.get(mode, MODES["Idea Analyzer"])
    project_context = f"Project name: {project.get('name', 'Untitled')}\nProject description: {project.get('description', '')}"
    memory_context = "\n".join(f"- {k}: {v}" for k, v in memory.items()) or "- No saved project decisions yet."
    task_context = "\n".join(
        f"- [{'x' if t.get('completed') else ' '}] {t.get('title', '')}" for t in tasks
    ) or "- No project tasks recorded yet."
    return f"""{BASE_SYSTEM}

CURRENT MODE: {mode}
Mode objective: {mode_guidance}

CURRENT PROJECT
{project_context}

SAVED PROJECT MEMORY
{memory_context}

PROJECT TASKS
{task_context}

When useful, end responses with a small 'Next actions' section containing specific steps the user can take.
""".strip()


def local_common_response(user_text: str) -> str | None:
    normalized = user_text.strip().lower()
    if normalized in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}:
        return "Hello! I’m DevMind Nexus. Describe a software idea, code problem, architecture decision, or security concern and I’ll help you turn it into an actionable engineering plan."
    if normalized in {"help", "what can you do", "what do you do", "how does this work"}:
        return (
            "I can analyze project ideas, design architecture, generate implementation guidance, debug code, review security, design tests, and create documentation. "
            "Choose an AI mode from the sidebar and keep asking follow-up questions—the current project context is preserved."
        )
    if normalized in {"about this project", "about"}:
        return (
            "DevMind Nexus is an AI-powered software engineering workspace built with Streamlit, SQLite, and an LLM API. "
            "It combines conversational memory with project planning and engineering workflows."
        )
    return None
