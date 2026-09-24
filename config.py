from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().with_name(".env"))


@dataclass(frozen=True)
class Settings:
    app_name: str = "Sathtern AI Chatbot"
    groq_api_key: str | None = os.getenv("GROQ_API_KEY", "").strip() or None
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()
    groq_timeout: float = float(os.getenv("GROQ_TIMEOUT", "60"))
    max_history_messages: int = int(os.getenv("MAX_HISTORY_MESSAGES", "18"))
    database_path: str = os.getenv("DATABASE_PATH", "devmind_nexus.db")


settings = Settings()
