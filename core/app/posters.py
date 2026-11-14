import os
import time

import httpx

TMDB_MOVIE_URL = "https://api.themoviedb.org/3/movie/{}"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/"

# Circuit Breaker: dopo troppi errori di fila smettiamo di chiamare TMDB per un po'
FAILURE_LIMIT = 3        # errori di fila prima di "far saltare il salvavita"
COOLDOWN_SECONDS = 60    # quanto restiamo senza chiamare TMDB
TIMEOUT_SECONDS = 2      # oltre questo tempo una risposta conta come errore

_failures = 0            # errori di fila finora
_open_until = 0.0        # fino a questo momento non chiamiamo TMDB
_cache = {}              # id del film -> percorso della locandina (None se non ce l'ha)

# Costruisce il link dell'immagine; size è la larghezza (w185 piccola, w342 media, w500 grande)
def _to_url(path: str | None, size: str) -> str | None:
    return IMAGE_BASE_URL + size + path if path else None

# Restituisce il link della locandina, oppure None se non c'è o TMDB non risponde
def get_poster_url(movie_id: int, size: str = "w185") -> str | None:
    global _failures, _open_until

    # Già chiesto in passato: rispondiamo dalla memoria
    if movie_id in _cache:
        return _to_url(_cache[movie_id], size)

    token = os.getenv("TMDB_TOKEN")
    if not token:
        return None  # senza token l'app funziona lo stesso, solo senza locandine

    # Salvavita saltato: non proviamo nemmeno
    if time.monotonic() < _open_until:
        return None

    try:
        response = httpx.get(
            TMDB_MOVIE_URL.format(movie_id),
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT_SECONDS,
        )
        if response.status_code == 404:  # TMDB non conosce il film: non è un guasto
            _cache[movie_id] = None
            return None
        response.raise_for_status()  # altri errori (es. token sbagliato, TMDB giù)
    except httpx.HTTPError:
        _failures += 1
        if _failures >= FAILURE_LIMIT:
            _open_until = time.monotonic() + COOLDOWN_SECONDS
            _failures = 0
        return None

    _failures = 0  # TMDB ha risposto bene: azzeriamo il conteggio
    path = response.json().get("poster_path")
    _cache[movie_id] = path
    return _to_url(path, size)