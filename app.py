import html
import os
import sqlite3
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

import bleach
from flask import Flask, g, jsonify, render_template, request, session


DEMO_USERS = (
    "belen@ajaia.test",
    "alex@ajaia.test",
    "sam@ajaia.test",
)
ALLOWED_TAGS = {
    "p", "br", "strong", "b", "em", "i", "u", "h1", "h2", "h3",
    "ol", "ul", "li", "blockquote", "pre", "code",
}


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "local-demo-key-change-me"),
        DATABASE=os.environ.get("DATABASE", str(Path(__file__).with_name("docs.db"))),
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        db = get_db()
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                owner_email TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                shared_with_email TEXT NOT NULL,
                UNIQUE(document_id, shared_with_email)
            );
            """
        )
        db.commit()

    def require_user(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            email = session.get("user_email")
            if email not in DEMO_USERS:
                return jsonify(error="Select a demo account to continue."), 401
            return view(*args, **kwargs)

        return wrapped

    def document_for_user(document_id):
        return get_db().execute(
            """
            SELECT d.*, (d.owner_email = ?) AS is_owner
            FROM documents d
            LEFT JOIN shares s ON s.document_id = d.id AND s.shared_with_email = ?
            WHERE d.id = ? AND (d.owner_email = ? OR s.id IS NOT NULL)
            """,
            (session["user_email"], session["user_email"], document_id, session["user_email"]),
        ).fetchone()

    def clean_content(content):
        return bleach.clean(
            content,
            tags=ALLOWED_TAGS,
            attributes={
                "li": lambda _tag, name, value: name == "data-list" and value in {"bullet", "ordered"}
            },
            protocols=[],
            strip=True,
        )

    def document_json(row):
        return {
            "id": row["id"],
            "title": row["title"],
            "content": row["content"],
            "owner_email": row["owner_email"],
            "updated_at": row["updated_at"],
            "is_owner": bool(row["is_owner"]),
        }

    def error(message, status=400):
        return jsonify(error=message), status

    @app.errorhandler(413)
    def request_too_large(_error):
        return error("The uploaded request is too large.", 413)

    @app.get("/")
    def index():
        return render_template("index.html", demo_users=DEMO_USERS)

    @app.get("/api/session")
    def get_session():
        return jsonify(users=DEMO_USERS, user_email=session.get("user_email"))

    @app.post("/api/session")
    def switch_user():
        data = request.get_json(silent=True)
        email = data.get("email") if isinstance(data, dict) else None
        if email not in DEMO_USERS:
            return error("Choose one of the available demo accounts.")
        session["user_email"] = email
        return jsonify(user_email=email)

    @app.get("/api/documents")
    @require_user
    def list_documents():
        rows = get_db().execute(
            """
            SELECT DISTINCT d.*, (d.owner_email = ?) AS is_owner
            FROM documents d
            LEFT JOIN shares s ON s.document_id = d.id
            WHERE d.owner_email = ? OR s.shared_with_email = ?
            ORDER BY d.updated_at DESC, d.id DESC
            """,
            (session["user_email"], session["user_email"], session["user_email"]),
        ).fetchall()
        owned = [document_json(row) for row in rows if row["is_owner"]]
        shared = [document_json(row) for row in rows if not row["is_owner"]]
        return jsonify(owned=owned, shared=shared)

    @app.post("/api/documents")
    @require_user
    def create_document():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return error("Send a valid document.")
        title = data.get("title", "Untitled document")
        content = data.get("content", "")
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > 120:
            return error("Document title must be between 1 and 120 characters.")
        if not isinstance(content, str) or len(content) > 500_000:
            return error("Document content must be text under 500,000 characters.")
        db = get_db()
        cursor = db.execute(
            "INSERT INTO documents (title, content, owner_email, updated_at) VALUES (?, ?, ?, ?)",
            (title.strip(), clean_content(content), session["user_email"], timestamp()),
        )
        db.commit()
        row = document_for_user(cursor.lastrowid)
        return jsonify(document=document_json(row)), 201

    @app.post("/api/documents/import")
    @require_user
    def import_document():
        uploaded = request.files.get("file")
        if uploaded is None or not uploaded.filename:
            return error("Choose a .txt or .md file to import.")
        filename = Path(uploaded.filename).name
        extension = Path(filename).suffix.lower()
        if extension not in {".txt", ".md"}:
            return error("Unsupported file type. Please choose a .txt or .md file.")
        try:
            raw_text = uploaded.read(500_001).decode("utf-8-sig")
        except UnicodeDecodeError:
            return error("The selected file must be valid UTF-8 text.")
        if len(raw_text) > 500_000:
            return error("The selected file is too large (maximum 500 KB).")
        if extension == ".md":
            content = request.form.get("rendered_content")
            if not isinstance(content, str):
                return error("Markdown import requires rendered content from the editor.")
        else:
            content = "<p>" + html.escape(raw_text).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>") + "</p>"
        title = Path(filename).stem.strip()[:120] or "Imported document"
        db = get_db()
        cursor = db.execute(
            "INSERT INTO documents (title, content, owner_email, updated_at) VALUES (?, ?, ?, ?)",
            (title, clean_content(content), session["user_email"], timestamp()),
        )
        db.commit()
        return jsonify(document=document_json(document_for_user(cursor.lastrowid))), 201

    @app.get("/api/documents/<int:document_id>")
    @require_user
    def get_document(document_id):
        row = document_for_user(document_id)
        if row is None:
            return error("Document not found or you do not have access.", 404)
        return jsonify(document=document_json(row))

    @app.patch("/api/documents/<int:document_id>")
    @require_user
    def update_document(document_id):
        row = document_for_user(document_id)
        if row is None:
            return error("Document not found or you do not have access.", 404)
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return error("Send a valid document update.")
        updates = {}
        if "title" in data:
            title = data["title"]
            if not isinstance(title, str) or not title.strip() or len(title.strip()) > 120:
                return error("Document title must be between 1 and 120 characters.")
            if not row["is_owner"]:
                return error("Only the document owner can rename it.", 403)
            updates["title"] = title.strip()
        if "content" in data:
            content = data["content"]
            if not isinstance(content, str) or len(content) > 500_000:
                return error("Document content must be text under 500,000 characters.")
            updates["content"] = clean_content(content)
        if not updates:
            return error("Provide a title or content to update.")
        updates["updated_at"] = timestamp()
        assignments = ", ".join(f"{key} = ?" for key in updates)
        get_db().execute(
            f"UPDATE documents SET {assignments} WHERE id = ?",
            (*updates.values(), document_id),
        )
        get_db().commit()
        return jsonify(document=document_json(document_for_user(document_id)))

    @app.get("/api/documents/<int:document_id>/shares")
    @require_user
    def list_shares(document_id):
        row = document_for_user(document_id)
        if row is None:
            return error("Document not found or you do not have access.", 404)
        if not row["is_owner"]:
            return error("Only the document owner can manage sharing.", 403)
        shares = get_db().execute(
            "SELECT shared_with_email FROM shares WHERE document_id = ? ORDER BY shared_with_email",
            (document_id,),
        ).fetchall()
        return jsonify(shared_with=[share["shared_with_email"] for share in shares])

    @app.post("/api/documents/<int:document_id>/shares")
    @require_user
    def add_share(document_id):
        row = document_for_user(document_id)
        if row is None:
            return error("Document not found or you do not have access.", 404)
        if not row["is_owner"]:
            return error("Only the document owner can share it.", 403)
        data = request.get_json(silent=True)
        email = data.get("email") if isinstance(data, dict) else None
        if email not in DEMO_USERS:
            return error("Choose a valid demo user to share with.")
        if email == row["owner_email"]:
            return error("A document cannot be shared with its owner.")
        try:
            get_db().execute(
                "INSERT INTO shares (document_id, shared_with_email) VALUES (?, ?)",
                (document_id, email),
            )
            get_db().commit()
        except sqlite3.IntegrityError:
            return error("This document is already shared with that user.", 409)
        return jsonify(shared_with=email), 201

    @app.delete("/api/documents/<int:document_id>/shares")
    @require_user
    def remove_share(document_id):
        row = document_for_user(document_id)
        if row is None:
            return error("Document not found or you do not have access.", 404)
        if not row["is_owner"]:
            return error("Only the document owner can manage sharing.", 403)
        data = request.get_json(silent=True)
        email = data.get("email") if isinstance(data, dict) else None
        cursor = get_db().execute(
            "DELETE FROM shares WHERE document_id = ? AND shared_with_email = ?",
            (document_id, email),
        )
        get_db().commit()
        if not cursor.rowcount:
            return error("That user does not have access to this document.", 404)
        return jsonify(shared_with=email)

    with app.app_context():
        init_db()

    return app


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
