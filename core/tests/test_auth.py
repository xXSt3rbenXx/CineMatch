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

# Manda il form di login, senza seguire il redirect
def login(client, username=USERNAME, password=PASSWORD):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )

# Registrazione corretta: redirect (303) e utente già loggato
def test_register_ok(client):
    response = register(client)
    assert response.status_code == 303
    # il pulsante "Logout" compare solo se l'utente è loggato
    assert "Logout" in client.get("/").text

# Lo stesso username con maiuscole diverse conta come duplicato
def test_register_duplicate_ignores_case(client):
    register(client)
    response = register(client, username="MARIO")
    assert response.status_code == 400
    assert "Username already taken" in response.text

# Un carattere non ammesso (lo spazio) viene rifiutato
def test_register_invalid_username(client):
    response = register(client, username="ma rio")
    assert response.status_code == 400
    assert "letters, numbers" in response.text

# Una password sotto gli 8 caratteri viene rifiutata
def test_register_short_password(client):
    response = register(client, password="short")
    assert response.status_code == 400
    assert "at least 8 characters" in response.text

# Registrazione, logout e poi login: il login non distingue le maiuscole
def test_login_ok(client):
    register(client)
    client.post("/logout")
    response = login(client, username="MARIO")
    assert response.status_code == 303
    assert "Logout" in client.get("/").text

# Password sbagliata: errore 401 e messaggio generico
def test_login_wrong_password(client):
    register(client)
    client.post("/logout")
    response = login(client, password="sbagliata123")
    assert response.status_code == 401
    assert "Invalid username or password" in response.text

# Dopo il logout l'utente risulta scollegato
def test_logout(client):
    register(client)
    client.post("/logout")
    assert "Log out" not in client.get("/").text

# Dopo il login si torna alla pagina indicata (es. la watchlist)
def test_login_redirects_to_next_url(client):
    register(client)
    client.post("/logout")
    response = client.post(
        "/login",
        data={"username": USERNAME, "password": PASSWORD, "next_url": "/watchlist"},
        follow_redirects=False,
    )
    assert response.headers["location"] == "/watchlist"

# Un indirizzo esterno come pagina di ritorno viene ignorato: si va alla home
def test_login_blocks_external_next_url(client):
    register(client)
    client.post("/logout")
    response = client.post(
        "/login",
        data={"username": USERNAME, "password": PASSWORD, "next_url": "//evil.com"},
        follow_redirects=False,
    )
    assert response.headers["location"] == "/"
