# Suggerimenti per "star": più film, al massimo 8, il più votato per primo
def test_suggestions_star(client):
    response = client.get("/api/search", params={"q": "star"})
    assert response.status_code == 200
    movies = response.json()
    assert 1 < len(movies) <= 8
    assert movies[0]["title"] == "Star Wars"


# Con meno di 2 lettere non ci sono suggerimenti
def test_suggestions_too_short(client):
    assert client.get("/api/search", params={"q": "s"}).json() == []


# Un testo che non corrisponde a nessun titolo dà una lista vuota
def test_suggestions_no_match(client):
    assert client.get("/api/search", params={"q": "zzzz"}).json() == []


# "What do you like?" con un film scelto mostra la sua scheda, senza cuore
def test_similar_selected_movie(client):
    response = client.get("/similar", params={"movie": 157336})
    assert response.status_code == 200
    assert "Interstellar" in response.text
    assert "Christopher Nolan" in response.text
    assert "Add to watchlist" not in response.text


# Un id che non è nel catalogo mostra un messaggio
def test_similar_movie_not_found(client):
    response = client.get("/similar", params={"movie": 1})
    assert "Movie not found" in response.text


# "Feeling lucky" per ora mostra solo il segnaposto
def test_feeling_lucky_placeholder(client):
    response = client.get("/feeling-lucky")
    assert response.status_code == 200
    assert "Coming soon" in response.text
