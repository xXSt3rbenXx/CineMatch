from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.catalog import get_movie
from app.database import get_watchlist_ids
from app.templating import get_current_user, templates

router = APIRouter()


# Home: casella di ricerca e, se è stato scelto un film (?movie=id), la sua scheda
@router.get("/", response_class=HTMLResponse)
def index(request: Request, movie: int | None = None):
    selected = get_movie(movie) if movie is not None else None
    # Per il cuore pieno o vuoto; None se l'utente non ha fatto login (niente cuore)
    user = get_current_user(request)
    saved_ids = set(get_watchlist_ids(user["id"])) if user else None
    return templates.TemplateResponse(
        request,
        "index.html",
        {"title": "CineMatch", "movie": selected, "movie_id": movie, "saved_ids": saved_ids},
    )
