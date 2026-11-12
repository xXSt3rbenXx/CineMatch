# Dati di prova usati in più test
USERNAME = "mario"
PASSWORD = "password123"

# Manda il form di registrazione, senza seguire il redirect
def register(client, username=USERNAME, password=PASSWORD):
    return client.post(
        "/register",
        data={"username": username, "password": password},
        follow_redirects=False,
    )

def login(client, username=USERNAME, password=PASSWORD):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )

def test_register_ok(client):
    response = register(client)
    assert response.status_code == 303
    # dopo la registrazione l'utente è già loggato
    assert "Log out" in client.get("/").text

def test_register_duplicate_ignores_case(client):
    register(client)
    response = register(client, username="MARIO")
    assert response.status_code == 400
    assert "Username already taken" in response.text

def test_register_invalid_username(client):
    response = register(client, username="ma rio")
    assert response.status_code == 400
    assert "letters, numbers" in response.text

def test_register_short_password(client):
    response = register(client, password="short")
    assert response.status_code == 400
    assert "at least 8 characters" in response.text

def test_login_ok(client):
    register(client)
    client.post("/logout")
    response = login(client, username="MARIO")  # il login non distingue le maiuscole
    assert response.status_code == 303
    assert "Log out" in client.get("/").text

def test_login_wrong_password(client):
    register(client)
    client.post("/logout")
    response = login(client, password="sbagliata123")
    assert response.status_code == 401
    assert "Invalid username or password" in response.text

def test_logout(client):
    register(client)
    client.post("/logout")
    assert "Log out" not in client.get("/").text