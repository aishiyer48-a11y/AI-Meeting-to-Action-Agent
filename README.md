# AI Meeting-to-Action Agent

A real agentic AI college project that converts meeting transcripts into structured actions, routes them to the correct tool, pauses for human approval before external calendar writes, and reports the result.

## Core workflow

**Transcript → Understand → Structured Extraction → Action Classification → Conditional Routing → Tool Decision → Human Approval → Tool Execution → Confirmation**

## Architecture

- **Streamlit**: user interface and session state.
- **OpenAI Responses API + Pydantic**: structured meeting understanding and action extraction.
- **LangGraph**: stateful conditional workflow, routing, interrupt/resume HITL.
- **SQLite**: persistent normal-task storage with CRUD.
- **Google Calendar API**: real calendar event creation after explicit approval.
- **Google OAuth 2.0**: secure user authorization.

## Folder structure

```text
project/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── agent/
│   ├── graph.py
│   ├── state.py
│   └── nodes.py
├── llm/
│   ├── client.py
│   ├── prompts.py
│   └── schemas.py
├── tools/
│   ├── task_tool.py
│   └── calendar_tool.py
├── database/
│   ├── db.py
│   ├── models.py
│   └── crud.py
├── google_calendar/
│   ├── auth.py
│   └── service.py
├── utils/
│   └── helpers.py
└── tests/
```

## Windows installation

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

If PowerShell blocks activation for the current user, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## OpenAI setup

1. Create an OpenAI API key.
2. Put it in `.env` as `OPENAI_API_KEY`.
3. Keep the model configurable through `OPENAI_MODEL`.
4. The app uses Pydantic structured parsing rather than free-form JSON parsing.

## Google Calendar setup

1. Create a Google Cloud project.
2. Enable the Google Calendar API.
3. Configure Google Auth Platform / OAuth consent screen.
4. Create an OAuth 2.0 Client ID for a **Desktop app**.
5. Download the JSON client secret and save it as `credentials.json` in the project root.
6. Do not commit it.
7. On first approved calendar execution, the app opens Google's OAuth flow. The resulting `token.json` is also ignored by Git.

The application requests the Calendar Events scope and writes only after approval.

## Run

```powershell
streamlit run app.py
```

Open the local Streamlit URL shown in the terminal.

## Demo transcript

> We discussed the final project architecture. Rahul will update the backend documentation by Friday. We also need to have a meeting with the Manager and Team Lead on Wednesday at 3 PM to review the architecture.

The current date is used to resolve relative dates. For a demo run on Tuesday 15 September 2026, Wednesday resolves to 16 September 2026. The meeting must still have an end time/duration; the agent asks for it instead of guessing.

For actual Calendar attendees, use email addresses. Role names such as “Manager” and “Team Lead” are displayed as participants but cannot be sent to Google Calendar as attendee email addresses unless email addresses are supplied.

## Mock/demo fallback

The MVP does **not** falsely claim a real Calendar event was created when OAuth/API access is unavailable. If OAuth is not configured, the app surfaces the real error. For a college presentation, you can demonstrate the proposed action and approval boundary without pretending an external write occurred.

## Security

- Secrets are stored outside source code.
- OAuth credentials and token are Git-ignored.
- API calls are executed only after approval.
- Missing critical meeting information is not guessed.
- External tool failures are surfaced to the UI.

## Testing

Run:

```powershell
python -m pytest -q
```

The included tests cover SQLite CRUD and meeting validation. External Google/OpenAI behavior should be tested with live credentials separately because those are external integrations.

## Future scope

- Gmail follow-up drafting/sending with a second approval boundary.
- Real participant email resolution from contacts.
- Persistent production checkpointer such as Postgres.
- Calendar conflict detection.
- Meeting audio transcription.
- Multi-user authentication and RBAC.
- Audit logs and action history.
