import httpx

from app import posters
from app.routers import movies

PLACEHOLDER = "/static/poster-placeholder.svg"
FAKE_URL = "https://image.tmdb.org/t/p/w342/fake.jpg"

# Se TMDB dà la locandina, la route rimanda il browser lì (TMDB finto: nessuna chiamata vera)
def test_poster_redirects_to_tmdb(client, monkeypatch):
    monkeypatch.setattr(movies, "get_poster_url", lambda movie_id, size: FAKE_URL)
    response = client.get("/api/poster/157336", follow_redirects=False)
    assert response.headers["location"] == FAKE_URL

# Se TMDB non risponde, si vede il placeholder
def test_poster_placeholder_when_tmdb_fails(client, monkeypatch):
    monkeypatch.setattr(movies, "get_poster_url", lambda movie_id, size: None)
    response = client.get("/api/poster/157336", follow_redirects=False)
    assert response.headers["location"] == PLACEHOLDER

# Un film fuori dal catalogo dà il placeholder senza chiedere nulla a TMDB
def test_poster_placeholder_for_unknown_movie(client):
    response = client.get("/api/poster/1", follow_redirects=False)
    assert response.headers["location"] == PLACEHOLDER

# Circuit Breaker: dopo FAILURE_LIMIT errori di fila smettiamo di chiamare TMDB
def test_circuit_breaker_stops_calling_tmdb(monkeypatch):
    calls = []

    # TMDB finto che fallisce sempre, e conta quante volte viene chiamato
    def broken_get(*args, **kwargs):
        calls.append(1)
        raise httpx.ConnectError("no connection")

    monkeypatch.setattr(posters.httpx, "get", broken_get)
    monkeypatch.setenv("TMDB_TOKEN", "fake-token")
    # Partiamo da zero: nessun errore, salvavita a posto, memoria vuota
    monkeypatch.setattr(posters, "_failures", 0)
    monkeypatch.setattr(posters, "_open_until", 0.0)
    monkeypatch.setattr(posters, "_cache", {})

    for _ in range(posters.FAILURE_LIMIT):
        assert posters.get_poster_url(157336) is None
    assert len(calls) == posters.FAILURE_LIMIT

    # Salvavita saltato: la richiesta dopo non arriva nemmeno a TMDB
    assert posters.get_poster_url(157336) is None
    assert len(calls) == posters.FAILURE_LIMIT