# Header usato dal JavaScript del cuore
FETCH = {"X-Requested-With": "fetch"}

# Registra un utente di prova (la registrazione lo lascia già loggato)
def login_user(client):
    client.post("/register", data={"username": "mario", "password": "password123"})

# Da non loggato la watchlist non si può modificare
def test_add_requires_login(client):
    response = client.post("/watchlist/add", data={"movie_id": 11}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"

# Dal JavaScript, da non loggato, la risposta è un errore 401
def test_add_requires_login_fetch(client):
    response = client.post("/watchlist/add", data={"movie_id": 11}, headers=FETCH)
    assert response.status_code == 401

# Aggiungere e togliere un film cambia il cuore sulla scheda
def test_add_and_remove(client):
    login_user(client)
    assert client.post("/watchlist/add", data={"movie_id": 11}, headers=FETCH).json() == {"saved": True}
    assert "Remove from watchlist" in client.get("/?movie=11").text  # cuore pieno
    assert client.post("/watchlist/remove", data={"movie_id": 11}, headers=FETCH).json() == {"saved": False}
    assert "Add to watchlist" in client.get("/?movie=11").text  # cuore vuoto

# Dopo il clic dal form si torna alla pagina di partenza
def test_add_redirects_back(client):
    login_user(client)
    response = client.post(
        "/watchlist/add",
        data={"movie_id": 11, "next_url": "/?movie=11"},
        follow_redirects=False,
    )
    assert response.headers["location"] == "/?movie=11"

# Un indirizzo esterno come pagina di ritorno viene ignorato
def test_redirect_to_external_site_is_blocked(client):
    login_user(client)
    response = client.post(
        "/watchlist/add",
        data={"movie_id": 11, "next_url": "//evil.com"},
        follow_redirects=False,
    )
    assert response.headers["location"] == "/"

# Da non loggato la scheda non mostra il cuore
def test_no_heart_when_logged_out(client):
    text = client.get("/?movie=11").text
    assert "Add to watchlist" not in text
    assert "Remove from watchlist" not in text