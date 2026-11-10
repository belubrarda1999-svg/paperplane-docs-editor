import io

import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-key",
            "DATABASE": str(tmp_path / "test.db"),
        }
    )
    return app.test_client()


def switch_user(client, email):
    return client.post("/api/session", json={"email": email})


def test_document_creation_and_rich_text_saving(client):
    switch_user(client, "belen@ajaia.test")
    created = client.post(
        "/api/documents",
        json={"title": "Project notes", "content": "<p>First draft</p>"},
    )
    assert created.status_code == 201
    document = created.json["document"]

    saved = client.patch(
        f"/api/documents/{document['id']}",
        json={
            "content": (
                '<h2>Update</h2><p><strong>Bold</strong> and <u>underlined</u></p>'
                '<ol><li data-list="bullet">A list item</li></ol>'
            )
        },
    )
    assert saved.status_code == 200
    assert "<h2>Update</h2>" in saved.json["document"]["content"]
    assert "<strong>Bold</strong>" in saved.json["document"]["content"]
    assert "<u>underlined</u>" in saved.json["document"]["content"]
    assert '<li data-list="bullet">A list item</li>' in saved.json["document"]["content"]


def test_file_import_creates_owned_document(client):
    switch_user(client, "alex@ajaia.test")
    response = client.post(
        "/api/documents/import",
        data={"file": (io.BytesIO(b"Line one\nLine two"), "meeting.txt")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    document = response.json["document"]
    assert document["title"] == "meeting"
    assert document["owner_email"] == "alex@ajaia.test"
    assert "Line one<br>Line two" in document["content"]


def test_markdown_import_sanitizes_rendered_content(client):
    switch_user(client, "belen@ajaia.test")
    response = client.post(
        "/api/documents/import",
        data={
            "file": (io.BytesIO(b"# Hello"), "notes.md"),
            "rendered_content": "<h1>Hello</h1><script>alert(1)</script>",
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    assert "<h1>Hello</h1>" in response.json["document"]["content"]
    assert "<script>" not in response.json["document"]["content"]


def test_sharing_grants_access_and_owner_only_management(client):
    switch_user(client, "belen@ajaia.test")
    created = client.post("/api/documents", json={"title": "Shared", "content": "<p>Hi</p>"})
    document_id = created.json["document"]["id"]

    switch_user(client, "alex@ajaia.test")
    assert client.get(f"/api/documents/{document_id}").status_code == 404
    assert client.post(
        f"/api/documents/{document_id}/shares",
        json={"email": "sam@ajaia.test"},
    ).status_code == 404

    switch_user(client, "belen@ajaia.test")
    shared = client.post(
        f"/api/documents/{document_id}/shares",
        json={"email": "alex@ajaia.test"},
    )
    assert shared.status_code == 201

    switch_user(client, "alex@ajaia.test")
    assert client.get(f"/api/documents/{document_id}").status_code == 200
    assert client.patch(
        f"/api/documents/{document_id}",
        json={"content": "<p>Edited by Alex</p>"},
    ).status_code == 200
    assert client.patch(
        f"/api/documents/{document_id}",
        json={"title": "Renamed"},
    ).status_code == 403
    assert client.get(f"/api/documents/{document_id}/shares").status_code == 403

    switch_user(client, "belen@ajaia.test")
    assert client.get(f"/api/documents/{document_id}/shares").json["shared_with"] == [
        "alex@ajaia.test"
    ]


def test_validation_and_unsupported_import(client):
    switch_user(client, "sam@ajaia.test")
    assert client.post("/api/documents", json={"title": "  "}).status_code == 400
    response = client.post(
        "/api/documents/import",
        data={"file": (io.BytesIO(b"nope"), "notes.pdf")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json["error"]
