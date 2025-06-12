import pytest

@pytest.mark.asyncio
async def test_register_user(client):
    response = await client.post("/register", json={"username": "testuser", "password": "testpass"})
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"

@pytest.mark.asyncio
async def test_register_duplicate_user(client):
    await client.post("/register", json={"username": "testuser", "password": "testpass"})
    response = await client.post("/register", json={"username": "testuser", "password": "testpass"})
    assert response.status_code == 400
    assert response.json()["detail"] == "User testuser is already existing!"

@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/register", json={"username": "testuser", "password": "testpass"})
    response = await client.post("/login", json={"username": "testuser", "password": "testpass"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    await client.post("/register", json={"username": "testuser", "password": "testpass"})
    response = await client.post("/login", json={"username": "testuser", "password": "wrongpass"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid access data"

@pytest.mark.asyncio
async def test_get_current_user_success(client):
    await client.post("/register", json={"username": "testuser", "password": "testpass"})
    login_response = await client.post("/login", json={"username": "testuser", "password": "testpass"})
    token = login_response.json()["access_token"]
    response = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"

@pytest.mark.asyncio
async def test_get_current_user_no_token(client):
    response = await client.get("/users/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"

@pytest.mark.asyncio
async def test_create_note(client):
    await client.post("/register", json={"username": "testuser", "password": "testpass"})
    login_response = await client.post("/login", json={"username": "testuser", "password": "testpass"})
    token = login_response.json()["access_token"]
    response = await client.post("/notes", json={"text": "Test note"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["text"] == "Test note"

@pytest.mark.asyncio
async def test_get_own_notes(client):
    await client.post("/register", json={"username": "user1", "password": "pass1"})
    await client.post("/register", json={"username": "user2", "password": "pass2"})
    login1 = await client.post("/login", json={"username": "user1", "password": "pass1"})
    token1 = login1.json()["access_token"]
    login2 = await client.post("/login", json={"username": "user2", "password": "pass2"})
    token2 = login2.json()["access_token"]
    await client.post("/notes", json={"text": "Note 1"}, headers={"Authorization": f"Bearer {token1}"})
    await client.post("/notes", json={"text": "Note 2"}, headers={"Authorization": f"Bearer {token2}"})
    response = await client.get("/notes", headers={"Authorization": f"Bearer {token1}"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["text"] == "Note 1"

@pytest.mark.asyncio
async def test_delete_own_and_foreign_note(client):
    await client.post("/register", json={"username": "user1", "password": "pass1"})
    await client.post("/register", json={"username": "user2", "password": "pass2"})
    login1 = await client.post("/login", json={"username": "user1", "password": "pass1"})
    token1 = login1.json()["access_token"]
    login2 = await client.post("/login", json={"username": "user2", "password": "pass2"})
    token2 = login2.json()["access_token"]
    note_response = await client.post("/notes", json={"text": "Note 1"}, headers={"Authorization": f"Bearer {token1}"})
    note_id = note_response.json()["id"]
    response = await client.delete(f"/notes/{note_id}", headers={"Authorization": f"Bearer {token1}"})
    assert response.status_code == 200
    assert response.json()["message"] == "Note is deleted"
    note_response = await client.post("/notes", json={"text": "Note 2"}, headers={"Authorization": f"Bearer {token2}"})
    note_id = note_response.json()["id"]
    response = await client.delete(f"/notes/{note_id}", headers={"Authorization": f"Bearer {token1}"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Note is not found or access error"
