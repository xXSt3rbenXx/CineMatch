import httpx

from app import posters
from app.routers import movies
from app.circuit_breaker import CircuitBreaker

PLACEHOLDER = "/static/img/poster-placeholder.svg"
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


# Circuit Breaker collegato a TMDB: dopo 3 errori di fila smettiamo di chiamarlo
def test_circuit_breaker_stops_calling_tmdb(monkeypatch):
    calls = []

    # TMDB finto che fallisce sempre, e conta quante volte viene chiamato
    def broken_get(*args, **kwargs):
        calls.append(1)
        raise httpx.ConnectError("no connection")

    monkeypatch.setattr(posters.httpx, "get", broken_get)
    monkeypatch.setattr(posters, "TMDB_TOKEN", "fake-token")
    # Partiamo da zero: circuito nuovo e memoria vuota
    monkeypatch.setattr(posters, "breaker", CircuitBreaker(failure_limit=3, cooldown_seconds=30))
    monkeypatch.setattr(posters, "_cache", {})

    for _ in range(3):
        assert posters.get_poster_url(157336) is None
    assert len(calls) == 3

    # Circuito aperto: la richiesta dopo non arriva nemmeno a TMDB
    assert posters.get_poster_url(157336) is None
    assert len(calls) == 3


# La misura grande arriva fino a TMDB; una misura sconosciuta diventa quella normale
def test_poster_size(client, monkeypatch):
    sizes = []
    monkeypatch.setattr(movies, "get_poster_url", lambda movie_id, size: sizes.append(size) or FAKE_URL)
    client.get("/api/poster/157336", params={"size": "original"}, follow_redirects=False)
    client.get("/api/poster/157336", params={"size": "huge"}, follow_redirects=False)
    assert sizes == ["original", "w342"]
