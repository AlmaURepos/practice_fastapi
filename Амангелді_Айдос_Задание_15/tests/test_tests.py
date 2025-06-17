import pytest
import asyncio

@pytest.mark.asyncio
async def test_register_user(client):
    response = await client.post("/register", json={"username": "test_register_user", "password": "12345"})
    assert response.status_code == 200
    assert response.json()["username"] == "test_register_user"

@pytest.mark.asyncio
async def test_register_duplicate_user(client):
    await client.post("/register", json={"username": "duplicate_user", "password": "12345"})
    response = await client.post("/register", json={"username": "duplicate_user", "password": "12345"})
    assert response.status_code == 400
    assert response.json()["detail"] == "User duplicate_user already exists"

@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/register", json={"username": "login_success", "password": "12345"})
    response = await client.post("/login", json={"username": "login_success", "password": "12345"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    await client.post("/register", json={"username": "invalid_login", "password": "12345"})
    response = await client.post("/login", json={"username": "invalid_login", "password": "wrongpass"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"

@pytest.mark.asyncio
async def test_get_current_user_success(client):
    await client.post("/register", json={"username": "current_user_test", "password": "12345"})
    login_response = await client.post("/login", json={"username": "current_user_test", "password": "12345"})
    token = login_response.json()["access_token"]
    response = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["username"] == "current_user_test"

@pytest.mark.asyncio
async def test_get_current_user_no_token(client):
    response = await client.get("/users/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_create_note(client):
    await client.post("/register", json={"username": "note_creator", "password": "12345"})
    login_response = await client.post("/login", json={"username": "note_creator", "password": "12345"})
    token = login_response.json()["access_token"]
    response = await client.post("/notes", json={"text": "Test note"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["text"] == "Test note"

@pytest.mark.asyncio
async def test_get_own_notes(client):
    await client.post("/register", json={"username": "notes_user1", "password": "12345"})
    await client.post("/register", json={"username": "notes_user2", "password": "12345"})
    login1 = await client.post("/login", json={"username": "notes_user1", "password": "12345"})
    login2 = await client.post("/login", json={"username": "notes_user2", "password": "12345"})
    token1 = login1.json()["access_token"]
    token2 = login2.json()["access_token"]

    await client.post("/notes", json={"text": "Note 1"}, headers={"Authorization": f"Bearer {token1}"})
    await client.post("/notes", json={"text": "Note 2"}, headers={"Authorization": f"Bearer {token2}"})

    response = await client.get("/notes", headers={"Authorization": f"Bearer {token1}"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["text"] == "Note 1"

@pytest.mark.asyncio
async def test_delete_own_and_foreign_note(client):
    await client.post("/register", json={"username": "note_owner", "password": "12345"})
    await client.post("/register", json={"username": "note_attacker", "password": "12345"})
    login1 = await client.post("/login", json={"username": "note_owner", "password": "12345"})
    login2 = await client.post("/login", json={"username": "note_attacker", "password": "12345"})
    token1 = login1.json()["access_token"]
    token2 = login2.json()["access_token"]

    note_response1 = await client.post("/notes", json={"text": "Owner Note"}, headers={"Authorization": f"Bearer {token1}"})
    note_id1 = note_response1.json()["id"]

    delete_response1 = await client.delete(f"/notes/{note_id1}", headers={"Authorization": f"Bearer {token1}"})
    assert delete_response1.status_code == 204

    note_response2 = await client.post("/notes", json={"text": "Attacker Note"}, headers={"Authorization": f"Bearer {token2}"})
    note_id2 = note_response2.json()["id"]

    delete_response2 = await client.delete(f"/notes/{note_id2}", headers={"Authorization": f"Bearer {token1}"})
    assert delete_response2.status_code == 404
    assert delete_response2.json()["detail"] == "Note not found or access denied"
