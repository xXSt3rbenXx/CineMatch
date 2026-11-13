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

# I 4 film di prova, salvati in quest'ordine (l'ultimo salvato è 12 Angry Men)
TEST_MOVIES = [11, 157336, 808, 389]

# Salva i film di prova nella watchlist dell'utente loggato
def save_test_movies(client):
    for movie_id in TEST_MOVIES:
        client.post("/watchlist/add", data={"movie_id": movie_id}, headers=FETCH)

# Vero se i titoli compaiono nella pagina esattamente in quest'ordine
def in_order(text, titles):
    positions = [text.index(title) for title in titles]
    return positions == sorted(positions)

# Da non loggato la pagina rimanda al login
def test_watchlist_requires_login(client):
    response = client.get("/watchlist", follow_redirects=False)
    assert response.headers["location"] == "/login?next_url=/watchlist"

# Watchlist vuota: compare l'invito a cercare un film
def test_watchlist_empty(client):
    login_user(client)
    assert "Your watchlist is empty" in client.get("/watchlist").text

# Senza filtri: tutti i film, dal più recente
def test_watchlist_recent_first(client):
    login_user(client)
    save_test_movies(client)
    text = client.get("/watchlist").text
    assert in_order(text, ["12 Angry Men", "Shrek", "Interstellar", "Star Wars"])

# Filtro per genere
def test_filter_genre(client):
    login_user(client)
    save_test_movies(client)
    text = client.get("/watchlist", params={"genre": "Drama"}).text
    assert "Interstellar" in text and "12 Angry Men" in text
    assert "Star Wars" not in text and "Shrek" not in text

# Filtro per decennio
def test_filter_decade(client):
    login_user(client)
    save_test_movies(client)
    text = client.get("/watchlist", params={"decade": "2000"}).text
    assert "Shrek" in text
    assert "Interstellar" not in text and "Star Wars" not in text and "12 Angry Men" not in text

# Filtro per durata massima (90 minuti inclusi)
def test_filter_runtime(client):
    login_user(client)
    save_test_movies(client)
    text = client.get("/watchlist", params={"runtime": "90"}).text
    assert "Shrek" in text
    assert "12 Angry Men" not in text  # 96 minuti

# Filtri combinati senza risultati: messaggio con il link per toglierli
def test_filters_no_match(client):
    login_user(client)
    save_test_movies(client)
    text = client.get("/watchlist", params={"genre": "Animation", "decade": "1950"}).text
    assert "No saved movies match these filters" in text

# Un genere che non è nella watchlist viene ignorato: si vedono tutti i film
def test_unknown_genre_is_ignored(client):
    login_user(client)
    save_test_movies(client)
    text = client.get("/watchlist", params={"genre": "Western"}).text
    assert "Star Wars" in text and "Shrek" in text

# Ordinamento per anno di uscita, dal più vecchio
def test_sort_oldest(client):
    login_user(client)
    save_test_movies(client)
    text = client.get("/watchlist", params={"sort": "oldest"}).text
    assert in_order(text, ["12 Angry Men", "Star Wars", "Shrek", "Interstellar"])

# Ordinamento per numero di voti (i più noti prima)
def test_sort_votes(client):
    login_user(client)
    save_test_movies(client)
    text = client.get("/watchlist", params={"sort": "votes"}).text
    assert in_order(text, ["Interstellar", "Star Wars", "Shrek", "12 Angry Men"])

# Segna (watched=1) o toglie (watched=0) il ✓ di un film, come fa il JavaScript
def set_watched(client, movie_id, watched):
    return client.post(
        "/watchlist/watched",
        data={"movie_id": movie_id, "watched": watched},
        headers=FETCH,
    )

# Da non loggato il ✓ non si può usare
def test_watched_requires_login(client):
    assert set_watched(client, 11, 1).status_code == 401

# Segnare e togliere il ✓ cambia lo stato mostrato nella watchlist
def test_mark_and_unmark_watched(client):
    login_user(client)
    client.post("/watchlist/add", data={"movie_id": 11}, headers=FETCH)
    assert set_watched(client, 11, 1).json() == {"watched": True}
    assert "Mark as not watched" in client.get("/watchlist").text  # ✓ verde
    assert set_watched(client, 11, 0).json() == {"watched": False}
    assert "Mark as not watched" not in client.get("/watchlist").text  # ✓ grigio

# Un film non salvato non può essere segnato come visto (e non viene aggiunto)
def test_watched_on_unsaved_movie_does_nothing(client):
    login_user(client)
    set_watched(client, 11, 1)
    assert "Your watchlist is empty" in client.get("/watchlist").text

# Filtri "Watched" e "To watch"
def test_filter_watched_status(client):
    login_user(client)
    save_test_movies(client)
    set_watched(client, 808, 1)  # Shrek visto
    watched = client.get("/watchlist", params={"status": "watched"}).text
    assert "Shrek" in watched and "Interstellar" not in watched
    to_watch = client.get("/watchlist", params={"status": "to_watch"}).text
    assert "Interstellar" in to_watch and "Shrek" not in to_watch

# Il ✓ compare solo nella watchlist, non nella scheda della home
def test_check_only_in_watchlist(client):
    login_user(client)
    client.post("/watchlist/add", data={"movie_id": 11}, headers=FETCH)
    assert "Mark as watched" in client.get("/watchlist").text
    assert "Mark as watched" not in client.get("/?movie=11").text

# Il contatore conta tutta la watchlist, anche quando un filtro ne mostra solo una parte
def test_counter(client):
    login_user(client)
    save_test_movies(client)
    set_watched(client, 808, 1)
    text = client.get("/watchlist", params={"genre": "Animation"}).text
    assert '<span id="count-total">4</span>' in text
    assert '<span id="count-watched">1</span>' in text
