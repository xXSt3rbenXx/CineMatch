from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.catalog import get_movie, search_movies
from app.posters import get_poster_url

router = APIRouter()

# Suggerimenti per la casella di ricerca: pochi film, solo i dati per riconoscerli
@router.get("/api/search")
def search_suggestions(q: str = ""):
    if len(q.strip()) < 2:
        return []  # con una lettera sola i risultati sarebbero troppi e poco utili
    movies = search_movies(q, limit=8)
    return [{"id": m["id"], "title": m["title"], "year": m["year"]} for m in movies]

# Misure di locandina accettate: media per la scheda, originale per lo schermo intero
POSTER_SIZES = {"w342", "original"}

# Locandina di un film: rimanda il browser all'immagine su TMDB, oppure al placeholder
# se TMDB non risponde, il film non ha locandina o non è nel nostro catalogo
@router.get("/api/poster/{movie_id}")
def poster(movie_id: int, size: str = "w342"):
    if size not in POSTER_SIZES:
        size = "w342"  # misura sconosciuta: usiamo quella normale
    url = None
    if get_movie(movie_id) is not None:  # chiediamo a TMDB solo film del catalogo
        url = get_poster_url(movie_id, size=size)
    return RedirectResponse(url or "/static/img/poster-placeholder.svg")

