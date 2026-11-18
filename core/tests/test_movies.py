from app.catalog import normalize

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


# Errori di battitura: se la ricerca normale non trova niente, si cercano i titoli più somiglianti
def test_suggestions_typo(client):
    assert client.get("/api/search", params={"q": "imception"}).json()[0]["title"] == "Inception"
    assert client.get("/api/search", params={"q": "godfater"}).json()[0]["title"] == "The Godfather"


# Un errore di battitura non cambia i risultati quando la ricerca normale trova già qualcosa
def test_suggestions_typo_only_as_fallback(client):
    titles = [m["title"] for m in client.get("/api/search", params={"q": "inception"}).json()]
    assert titles == ["Inception"]


# Prima i titoli che iniziano con il testo scritto: "st" dà Star Wars, non Interstellar
def test_suggestions_title_start_first(client):
    movies = client.get("/api/search", params={"q": "st"}).json()
    assert movies[0]["title"] == "Star Wars"
    assert "Interstellar" not in [m["title"] for m in movies]


# L'articolo iniziale si può saltare
def test_suggestions_skip_article(client):
    movies = client.get("/api/search", params={"q": "godfather"}).json()
    assert movies[0]["title"] == "The Godfather"


# Trattini e accenti non contano
def test_suggestions_ignore_punctuation_and_accents(client):
    assert client.get("/api/search", params={"q": "spiderman"}).json()[0]["title"] == "Spider-Man"
    assert client.get("/api/search", params={"q": "amelie"}).json()[0]["title"] == "Amélie"


# Il testo pulito: minuscole, niente accenti, niente punteggiatura, spazi singoli
def test_normalize():
    assert normalize("Spider-Man") == "spiderman"
    assert normalize("Amélie") == "amelie"
    assert normalize("  The   Godfather: Part II ") == "the godfather part ii"


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


# Un film senza voti non mostra 0.0/10; con un voto solo, "vote" al singolare
def test_card_votes(client):
    assert "No votes yet" in client.get("/similar", params={"movie": 43743}).text  # Fabled, 0 voti
    text = client.get("/similar", params={"movie": 89861}).text  # Stiff Upper Lips, 1 voto
    assert "1 vote<" in text and "/10" in text