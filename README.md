# Paperplane

A lightweight collaborative document editor built with Flask, SQLite, Quill, and vanilla JavaScript. It includes three password-free demo accounts, owner/shared document lists, rich-text editing, `.txt`/`.md` imports, and owner-managed sharing.

## Requirements

- Python 3.10+
- A modern browser with internet access for the Quill and Marked CDN assets

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). The SQLite database (`docs.db`) is created beside `app.py` on first run. Set `DATABASE` to use another database path and `SECRET_KEY` to provide a private session key. For local debugging only, set `FLASK_DEBUG=1`.

Switch between `belen@ajaia.test`, `alex@ajaia.test`, and `sam@ajaia.test` from the account selector in the top bar. Owners can invite another demo account; invited collaborators can edit document content, while only the owner can rename or manage sharing. Markdown is rendered in the browser with Marked, and imported/editor HTML is sanitized on the server before it is stored.

## Run tests

```powershell
pytest -q
```

## API overview

- `GET /api/session`, `POST /api/session` — inspect/switch the current demo user.
- `GET /api/documents`, `POST /api/documents` — list or create documents.
- `GET /api/documents/<id>`, `PATCH /api/documents/<id>` — read or update an accessible document.
- `POST /api/documents/import` — import a multipart `.txt` or `.md` file. Markdown requests include `rendered_content` produced by Marked.
- `GET|POST|DELETE /api/documents/<id>/shares` — list, add, or remove shares (owner only).

Document endpoints require a selected demo account. Requests for inaccessible documents return `404`; attempts to manage shares or rename as a non-owner return `403`.
