import uuid

from httpx import AsyncClient


def _email() -> str:
    return f"user-{uuid.uuid4()}@example.com"


async def _register_and_login(
    client: AsyncClient, email: str, password: str = "correct-horse-1"
) -> dict[str, str]:
    await client.post("/auth/register", json={"email": email, "password": password})
    response = await client.post("/auth/login", json={"email": email, "password": password})
    result: dict[str, str] = response.json()
    return result


async def test_register_creates_user(client: AsyncClient) -> None:
    email = _email()

    response = await client.post(
        "/auth/register", json={"email": email, "password": "correct-horse-1"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == email
    assert "password" not in body
    assert "hashed_password" not in body


async def test_register_duplicate_email_returns_409(client: AsyncClient) -> None:
    email = _email()
    await client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})

    response = await client.post(
        "/auth/register", json={"email": email, "password": "another-pass-1"}
    )

    assert response.status_code == 409


async def test_login_success_returns_token_pair(client: AsyncClient) -> None:
    email = _email()
    await client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})

    response = await client.post(
        "/auth/login", json={"email": email, "password": "correct-horse-1"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


async def test_login_wrong_password_returns_401(client: AsyncClient) -> None:
    email = _email()
    await client.post("/auth/register", json={"email": email, "password": "correct-horse-1"})

    response = await client.post("/auth/login", json={"email": email, "password": "wrong-password"})

    assert response.status_code == 401


async def test_me_returns_current_user_with_valid_token(client: AsyncClient) -> None:
    email = _email()
    tokens = await _register_and_login(client, email)

    response = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == email


async def test_me_without_credentials_returns_403(client: AsyncClient) -> None:
    response = await client.get("/auth/me")

    assert response.status_code == 403


async def test_me_with_garbage_token_returns_401(client: AsyncClient) -> None:
    response = await client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code == 401


async def test_refresh_returns_new_working_token_pair(client: AsyncClient) -> None:
    tokens = await _register_and_login(client, _email())

    response = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert response.status_code == 200
    new_tokens = response.json()
    # Not asserting access_token differs from the original: JWT iat/exp have
    # second-level granularity, so two tokens minted within the same second
    # for the same user are legitimately byte-identical - that's not a bug.
    # The refresh token is always fresh random bytes, so it must differ.
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    me_response = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
    )
    assert me_response.status_code == 200


async def test_refresh_token_is_single_use(client: AsyncClient) -> None:
    tokens = await _register_and_login(client, _email())

    first = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200

    reused = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401


async def test_refresh_reuse_revokes_the_whole_family(client: AsyncClient) -> None:
    tokens = await _register_and_login(client, _email())

    first = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    rotated = first.json()["refresh_token"]

    # Replaying the original (now-revoked) token is reuse - this should burn
    # the whole family, including the token that replaced it.
    replay = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401

    now_also_revoked = await client.post("/auth/refresh", json={"refresh_token": rotated})
    assert now_also_revoked.status_code == 401


async def test_unknown_refresh_token_returns_401(client: AsyncClient) -> None:
    response = await client.post("/auth/refresh", json={"refresh_token": "not-a-real-token"})

    assert response.status_code == 401


async def test_logout_revokes_the_refresh_token(client: AsyncClient) -> None:
    tokens = await _register_and_login(client, _email())

    logout_response = await client.post(
        "/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert logout_response.status_code == 204

    refresh_response = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_response.status_code == 401
