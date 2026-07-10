import uuid

from httpx import AsyncClient


def _email() -> str:
    return f"user-{uuid.uuid4()}@example.com"


async def _auth_headers(client: AsyncClient, password: str = "correct-horse-1") -> dict[str, str]:
    email = _email()
    await client.post("/auth/register", json={"email": email, "password": password})
    login = await client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_create_bookmark_returns_bookmark_with_tags(client: AsyncClient) -> None:
    headers = await _auth_headers(client)

    response = await client.post(
        "/bookmarks",
        headers=headers,
        json={
            "url": "https://fastapi.tiangolo.com",
            "title": "FastAPI docs",
            "description": "reference",
            "tags": ["python", "web"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "FastAPI docs"
    assert sorted(body["tags"]) == ["python", "web"]


async def test_bookmarks_require_authentication(client: AsyncClient) -> None:
    response = await client.get("/bookmarks")

    assert response.status_code == 403


async def test_list_bookmarks_returns_only_current_users_bookmarks(client: AsyncClient) -> None:
    headers_a = await _auth_headers(client)
    headers_b = await _auth_headers(client)

    await client.post(
        "/bookmarks", headers=headers_a, json={"url": "https://a.example", "title": "A's link"}
    )
    await client.post(
        "/bookmarks", headers=headers_b, json={"url": "https://b.example", "title": "B's link"}
    )

    response = await client.get("/bookmarks", headers=headers_a)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "A's link"


async def test_list_bookmarks_filters_by_tag(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    await client.post(
        "/bookmarks",
        headers=headers,
        json={"url": "https://a.example", "title": "Tagged", "tags": ["devops"]},
    )
    await client.post(
        "/bookmarks",
        headers=headers,
        json={"url": "https://b.example", "title": "Untagged"},
    )

    response = await client.get("/bookmarks", headers=headers, params={"tag": "devops"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Tagged"


async def test_list_bookmarks_search_matches_title_or_url(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    await client.post(
        "/bookmarks",
        headers=headers,
        json={"url": "https://terraform.io", "title": "Terraform docs"},
    )
    await client.post(
        "/bookmarks", headers=headers, json={"url": "https://example.com", "title": "Unrelated"}
    )

    response = await client.get("/bookmarks", headers=headers, params={"q": "terraform"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Terraform docs"


async def test_list_bookmarks_pagination(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    for i in range(5):
        await client.post(
            "/bookmarks", headers=headers, json={"url": f"https://x.example/{i}", "title": f"L{i}"}
        )

    response = await client.get("/bookmarks", headers=headers, params={"limit": 2, "offset": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["limit"] == 2
    assert body["offset"] == 0


async def test_get_bookmark_by_id(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    created = await client.post(
        "/bookmarks", headers=headers, json={"url": "https://example.com", "title": "Example"}
    )
    bookmark_id = created.json()["id"]

    response = await client.get(f"/bookmarks/{bookmark_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == bookmark_id


async def test_get_nonexistent_bookmark_returns_404(client: AsyncClient) -> None:
    headers = await _auth_headers(client)

    response = await client.get(f"/bookmarks/{uuid.uuid4()}", headers=headers)

    assert response.status_code == 404


async def test_get_other_users_bookmark_returns_404(client: AsyncClient) -> None:
    headers_a = await _auth_headers(client)
    headers_b = await _auth_headers(client)
    created = await client.post(
        "/bookmarks", headers=headers_a, json={"url": "https://example.com", "title": "A's link"}
    )
    bookmark_id = created.json()["id"]

    response = await client.get(f"/bookmarks/{bookmark_id}", headers=headers_b)

    assert response.status_code == 404


async def test_update_bookmark_partial_update_leaves_other_fields_untouched(
    client: AsyncClient,
) -> None:
    headers = await _auth_headers(client)
    created = await client.post(
        "/bookmarks",
        headers=headers,
        json={"url": "https://example.com", "title": "Original", "tags": ["keep"]},
    )
    bookmark_id = created.json()["id"]

    response = await client.patch(
        f"/bookmarks/{bookmark_id}", headers=headers, json={"title": "Updated"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Updated"
    assert body["url"] == "https://example.com"
    assert body["tags"] == ["keep"]


async def test_update_bookmark_tags_replaces_tag_set(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    created = await client.post(
        "/bookmarks",
        headers=headers,
        json={"url": "https://example.com", "title": "T", "tags": ["old"]},
    )
    bookmark_id = created.json()["id"]

    response = await client.patch(
        f"/bookmarks/{bookmark_id}", headers=headers, json={"tags": ["new-a", "new-b"]}
    )

    assert response.status_code == 200
    assert sorted(response.json()["tags"]) == ["new-a", "new-b"]


async def test_delete_bookmark_removes_it(client: AsyncClient) -> None:
    headers = await _auth_headers(client)
    created = await client.post(
        "/bookmarks", headers=headers, json={"url": "https://example.com", "title": "Gone soon"}
    )
    bookmark_id = created.json()["id"]

    delete_response = await client.delete(f"/bookmarks/{bookmark_id}", headers=headers)
    assert delete_response.status_code == 204

    get_response = await client.get(f"/bookmarks/{bookmark_id}", headers=headers)
    assert get_response.status_code == 404
