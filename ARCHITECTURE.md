# Architecture

## Stack

- **Flask** serves the page and JSON API from one small Python application. It keeps the demo straightforward to run and deploy.
- **SQLite** stores documents and sharing records without a separate database service. It is a good fit for a compact demo, but a Render deployment needs a persistent disk to retain a SQLite database across restarts; SQLite is also not a good fit for multiple app instances.
- **Quill.js** provides the rich-text editor and toolbar in the browser.
- **Marked.js** converts imported Markdown to HTML before it is sent to the server. The server sanitizes stored HTML with Bleach.

The browser uses vanilla JavaScript, and Quill and Marked are loaded from CDNs.

## Data model

The database has two tables:

- `documents`: `id`, `title`, `content`, `owner_email`, and `updated_at`.
- `shares`: `id`, `document_id`, and `shared_with_email`. `document_id` references `documents.id` with cascading deletion, and a unique constraint prevents duplicate shares to the same account.

Demo accounts are configured in the application rather than stored in a users table.

## Access control

The session identifies one of three demo accounts. A user can read a document if they own it or it has been shared with them. Owners can rename documents and add or remove collaborators. Owners and shared collaborators can edit document content. API routes enforce these checks on the server.

## Trade-offs and next steps

To keep the time-limited implementation focused, the app uses a single Flask module, a simple session-based demo account switcher instead of real authentication, and SQLite instead of a managed production database. It does not provide simultaneous-edit conflict resolution, version history, or granular roles.

In the next 2–4 hours, the highest-value follow-up would be to move persistent data to a managed database (or explicitly configure and test a Render persistent disk), then add:

1. Real-time change notifications or collaborative editing over WebSockets, with a clear conflict policy.
2. Role-based permissions beyond owner and collaborator.
3. Version history with restore support.

These are planned extensions, not current capabilities.
