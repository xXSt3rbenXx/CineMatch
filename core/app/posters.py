import os

import httpx

from app.circuit_breaker import CircuitBreaker

TMDB_MOVIE_URL = "https://api.themoviedb.org/3/movie/{}"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"

# Parametri: 1 s per collegarsi a TMDB, 2 s per ricevere la risposta
TIMEOUT = httpx.Timeout(2.0, connect=1.0)

# Circuit Breaker per TMDB: si apre dopo 3 errori di fila, fa una prova dopo 30 s
breaker = CircuitBreaker(failure_limit=3, cooldown_seconds=30)

_cache = {}  # id del film -> percorso della locandina (None se non ce l'ha)

# Costruisce il link dell'immagine; size è la larghezza (w185 piccola, w342 media, w500 grande)
def _to_url(path: str | None, size: str) -> str | None:
    return IMAGE_BASE_URL + size + path if path else None

# Restituisce il link della locandina, oppure None se non c'è o TMDB non risponde
def get_poster_url(movie_id: int, size: str = "w185") -> str | None:
    # Già chiesto in passato: rispondiamo dalla memoria
    if movie_id in _cache:
        return _to_url(_cache[movie_id], size)

    token = os.getenv("TMDB_TOKEN")
    if not token:
        return None  # senza token l'app funziona lo stesso, solo senza locandine

    # Circuito aperto: non proviamo nemmeno, chi ci chiama mostrerà il placeholder
    if not breaker.allow_request():
        return None

    try:
        response = httpx.get(
            TMDB_MOVIE_URL.format(movie_id),
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT,
        )
        if response.status_code == 404:  # TMDB non conosce il film: ha risposto, quindi funziona
            breaker.record_success()
            _cache[movie_id] = None
            return None
        response.raise_for_status()  # altri errori (es. token sbagliato, TMDB giù)
    except httpx.HTTPError:
        breaker.record_failure()
        return None

    breaker.record_success()
    path = response.json().get("poster_path")
    _cache[movie_id] = path
    return _to_url(path, size)
