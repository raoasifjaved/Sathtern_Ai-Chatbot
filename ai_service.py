from __future__ import annotations

from typing import Callable, Iterable

from config import settings
from prompts import local_common_response

try:
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None  # type: ignore


class AIServiceError(RuntimeError):
    pass


class AIService:
    def __init__(self) -> None:
        self.api_key = settings.groq_api_key
        self.model = settings.groq_model
        self._client = Groq(api_key=self.api_key) if (Groq and self.api_key) else None

    @property
    def available(self) -> bool:
        return self._client is not None

    def respond(
        self,
        user_text: str,
        system_prompt: str,
        history: Iterable[dict[str, str]],
        stream: bool = True,
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        local = local_common_response(user_text)
        if local:
            if on_token:
                on_token(local)
            return local

        if not self._client:
            return self._demo_fallback(user_text)

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_text})

        try:
            if stream:
                stream_result = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    max_completion_tokens=3000,
                    stream=True,
                )
                chunks: list[str] = []
                for chunk in stream_result:
                    token = getattr(chunk.choices[0].delta, "content", None) or ""
                    if token:
                        chunks.append(token)
                        if on_token:
                            on_token(token)
                return "".join(chunks).strip()

            result = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_completion_tokens=3000,
                stream=False,
            )
            return (result.choices[0].message.content or "").strip()
        except Exception as exc:  # provider SDK exceptions vary by version
            message = str(exc).strip() or "Unknown provider error"
            lowered = message.lower()
            if "rate limit" in lowered:
                raise AIServiceError("The AI provider rate limit was reached. Please retry after a short wait.") from exc
            if "401" in lowered or "authentication" in lowered or "api key" in lowered:
                raise AIServiceError("The Groq API key was rejected. Check GROQ_API_KEY and try again.") from exc
            raise AIServiceError(f"AI provider error: {message}") from exc

    @staticmethod
    def _demo_fallback(user_text: str) -> str:
        """Useful for classroom demonstrations when no API key is configured."""
        idea = user_text.strip()
        return f"""## Demo Analysis

I received your requirement:
> {idea}

### Suggested breakdown
| Area | Initial direction |
|---|---|
| Goal | Convert the requirement into a measurable software outcome |
| Interface | Use a clear web UI with guided inputs and visible results |
| Backend | Separate business logic from the UI layer |
| Data | Store durable project state in SQLite or a managed database |
| Security | Keep secrets in environment variables; validate all inputs |
| Testing | Add unit, integration, and user-flow tests |

### Recommended next step
Configure `GROQ_API_KEY` to enable live AI generation. Until then, DevMind Nexus runs in safe demo mode for greetings, help, and basic requirement analysis."""
