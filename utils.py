from __future__ import annotations

import io
import re
from datetime import datetime


def markdown_export(project: dict, messages: list[dict], memory: dict, tasks: list[dict]) -> str:
    lines = [f"# {project.get('name', 'DevMind Nexus Project')}", ""]
    if project.get("description"):
        lines += [project["description"], ""]
    lines += ["## Saved Project Memory", ""]
    if memory:
        lines += [f"- **{k}:** {v}" for k, v in memory.items()]
    else:
        lines.append("No saved decisions yet.")
    lines += ["", "## Tasks", ""]
    if tasks:
        lines += [f"- [{'x' if t.get('completed') else ' '}] {t.get('title')}" for t in tasks]
    else:
        lines.append("No tasks recorded.")
    lines += ["", "## Conversation", ""]
    for message in messages:
        role = message.get("role", "unknown").capitalize()
        timestamp = message.get("created_at", "")
        lines += [f"### {role} — {timestamp}", "", message.get("content", ""), ""]
    return "\n".join(lines)


def pdf_export(project: dict, messages: list[dict], memory: dict, tasks: list[dict]) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PDF export requires reportlab. Install dependencies from requirements.txt.") from exc

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=42)
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    body.fontSize = 9
    body.leading = 13
    h1 = styles["Title"]
    h2 = styles["Heading2"]
    small = ParagraphStyle("Small", parent=body, fontSize=7.5, textColor="#555555")

    story = [Paragraph(_escape(project.get("name", "DevMind Nexus Project")), h1), Spacer(1, 10)]
    if project.get("description"):
        story += [Paragraph(_escape(project["description"]), body), Spacer(1, 8)]

    story += [Paragraph("Saved Project Memory", h2)]
    if memory:
        for key, value in memory.items():
            story.append(Paragraph(f"<b>{_escape(str(key))}</b>: {_escape(str(value))}", body))
    else:
        story.append(Paragraph("No saved decisions yet.", body))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Tasks", h2))
    if tasks:
        for task in tasks:
            mark = "✓" if task.get("completed") else "□"
            story.append(Paragraph(f"{mark} {_escape(str(task.get('title', '')))}", body))
    else:
        story.append(Paragraph("No tasks recorded.", body))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Conversation", h2))
    for message in messages:
        role = _escape(str(message.get("role", "unknown")).capitalize())
        timestamp = _escape(str(message.get("created_at", "")))
        content = _markdown_to_basic_html(str(message.get("content", "")))
        story += [Paragraph(f"<b>{role}</b> <font size='7' color='#666666'>{timestamp}</font>", small)]
        story += [Paragraph(content, body), Spacer(1, 7)]

    doc.build(story)
    return buffer.getvalue()


def _escape(text: str) -> str:
    replacements = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}
    return "".join(replacements.get(ch, ch) for ch in text)


def _markdown_to_basic_html(text: str) -> str:
    text = _escape(text)
    text = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", text)
    text = text.replace("\n", "<br/>")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return text


def friendly_timestamp(iso_value: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_value.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y %I:%M %p")
    except Exception:
        return iso_value
