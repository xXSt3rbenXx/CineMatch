from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.catalog import get_movie
from app.templating import templates

router = APIRouter()


# "What do you like?": l'utente sceglie un film, l'AI troverà quelli simili.
# Aperta a tutti: il login serve solo per salvare i consigli nella watchlist.
@router.get("/similar", response_class=HTMLResponse)
def similar(request: Request, movie: int | None = None):
    selected = get_movie(movie) if movie is not None else None
    # saved_ids=None: la scheda del film scelto non ha il cuore, serve solo come punto di partenza
    return templates.TemplateResponse(
        request,
        "similar.html",
        {"title": "What do you like? - CineMatch", "movie": selected, "movie_id": movie, "saved_ids": None},
    )


# "Feeling lucky": per ora solo un segnaposto, le domande del quiz sono ancora da decidere
@router.get("/feeling-lucky", response_class=HTMLResponse)
def feeling_lucky(request: Request):
    return templates.TemplateResponse(request, "feeling_lucky.html", {"title": "Feeling lucky - CineMatch"})
