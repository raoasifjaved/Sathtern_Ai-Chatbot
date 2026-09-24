from __future__ import annotations

import re
from typing import Any

from database import Database


def extract_memory(user_text: str, assistant_text: str) -> dict[str, str]:
    """Lightweight heuristics for important project decisions; the DB remains the source of truth."""
    blob = f"{user_text}\n{assistant_text}"
    patterns = {
        "language": r"\b(?:python|javascript|typescript|java|c\+\+|c#|go|rust|php)\b",
        "frontend": r"\b(?:streamlit|react|next\.js|vue|angular)\b",
        "backend": r"\b(?:fastapi|flask|django|node\.js|express)\b",
        "database": r"\b(?:sqlite|postgresql|mysql|mongodb|redis)\b",
        "architecture": r"\b(?:monolith|microservices|serverless|event[- ]driven|layered architecture)\b",
    }
    memory: dict[str, str] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, blob, flags=re.IGNORECASE)
        if match:
            memory[key] = match.group(0)
    return memory


def save_extracted_memory(db: Database, project_id: int, user_text: str, assistant_text: str) -> dict[str, str]:
    extracted = extract_memory(user_text, assistant_text)
    for key, value in extracted.items():
        db.set_memory(project_id, key, value)
    return extracted


def memory_lines(memory: dict[str, Any]) -> str:
    if not memory:
        return "No saved decisions yet."
    return "\n".join(f"{key}: {value}" for key, value in memory.items())
