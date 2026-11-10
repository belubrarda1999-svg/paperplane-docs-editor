# Submission

## Included files

- `app.py` — Flask application and JSON API
- `templates/index.html` — application page
- `static/app.js` and `static/styles.css` — browser behavior and styling
- `test_app.py` — automated Flask tests
- `requirements.txt` — Python dependencies, including Gunicorn
- `Procfile` — Render web process (`web: gunicorn app:app`)
- `.gitignore` — excludes Python cache, local database files, and virtual environments
- `README.md` — project overview, local setup, and API summary
- `ARCHITECTURE.md` — stack, schema, access control, and follow-up work
- `AI_WORKFLOW.md` — AI-assisted development and verification summary

The runtime SQLite database is created locally and is excluded from version control.

## Demo accounts

- `belen@ajaia.test`
- `alex@ajaia.test`
- `sam@ajaia.test`

## Run locally

1. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Start the app:
   ```powershell
   python app.py
   ```
4. Open `http://127.0.0.1:5000`. Run the test suite with `pytest -q`.

Render starts the app using the included Procfile. SQLite data on Render requires a configured persistent disk; the default filesystem may be ephemeral.

## Scope

**Complete:** demo account switching, owned and shared document lists, rich-text editing with automatic saves, `.txt` and `.md` import, sanitized HTML, and owner-managed sharing with collaborator content editing.

**Intentionally out of scope:** production authentication and user management, real-time multi-user editing, fine-grained roles, version history, and conflict resolution.

## Deployment links

- Live URL: `[Add the deployed Render URL]`
- Video Walkthrough URL: `[Add the walkthrough URL]`
