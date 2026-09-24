# DevMind Nexus

DevMind Nexus is an original AI-powered software engineering workspace. It combines conversational AI with persistent project sessions, technical memory, task tracking, search, and export features.

## What it demonstrates

This project covers the core requirements of an AI chatbot task:

- Responds to user questions using a Groq-compatible LLM API.
- Includes predefined local responses for greetings/help/common queries.
- Maintains conversation history in SQLite.
- Supports project and conversation sessions.
- Provides a professional Streamlit user interface.

It also adds engineering-oriented features:

- Seven AI workflow modes.
- Project memory for technical decisions.
- Project task tracking.
- Conversation search.
- Markdown/TXT/PDF export.
- Demo mode when an API key is not configured.
- Modular architecture rather than one monolithic script.

## Architecture

```text
Streamlit UI (app.py)
        │
        ├── AI Service (ai_service.py)
        │       └── Groq Chat Completions API
        │
        ├── Prompt Engine (prompts.py)
        │
        ├── Memory Layer (memory.py)
        │
        ├── Database Layer (database.py)
        │       ├── projects
        │       ├── conversations
        │       ├── messages
        │       ├── project_memory
        │       └── tasks
        │
        └── Export Utilities (utils.py)
                ├── Markdown
                ├── TXT
                └── PDF
```

## Requirements

- Python 3.10+
- A Groq API key for live AI responses

The official Groq Python package is installed with `pip install groq`, and chat completions accept a list of role/content messages. The default model in this project is `openai/gpt-oss-20b`; change `GROQ_MODEL` in `.env` when needed.

## Installation

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Linux/macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set:

```text
GROQ_API_KEY=your_real_key
```

## Run

```bash
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

## Demo mode

Without `GROQ_API_KEY`, DevMind Nexus still launches and handles common queries plus a safe structured demo analysis. This makes classroom demonstrations possible before configuring the external API.

## Suggested test conversation

1. Create a project called `Smart Campus Navigator`.
2. Ask: `Design an AI-powered campus navigation system for students.`
3. Follow up: `Now design the database.`
4. Switch to `Security Reviewer` and ask: `Review the authentication risks.`
5. Switch to `Testing Assistant` and ask for a full test strategy.
6. Open **Project Memory** to inspect saved technical choices.
7. Add project tasks and mark completed items.
8. Use **Export** to download Markdown, TXT, or PDF.

## Future upgrades

- Retrieval-augmented generation over uploaded technical documents.
- GitHub repository analysis.
- Vector database for semantic project memory.
- Autonomous code review agents.
- Multi-agent planning and verification workflows.
- Browser/search tools for current technical documentation.
- User authentication and multi-user projects.
- Cloud deployment with PostgreSQL and object storage.
