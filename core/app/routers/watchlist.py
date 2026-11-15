from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.catalog import get_movie
from app.database import add_to_watchlist, get_watchlist, remove_from_watchlist, set_watched
from app.templating import get_current_user, templates
from app.security import safe_next

from app.watchlist_filters import (
    RUNTIME_OPTIONS, SORT_OPTIONS, STATUS_OPTIONS, apply_filters, menu_options, sort_movies,
)

router = APIRouter()

# Vero se la richiesta arriva dal JavaScript del cuore (che non vuole ricaricare la pagina)
def wants_json(request: Request) -> bool:
    return request.headers.get("X-Requested-With") == "fetch"

@router.post("/watchlist/add")
def watchlist_add(request: Request, movie_id: int = Form(...), next_url: str = Form("/")):
    user = get_current_user(request)
    if user is None:
        if wants_json(request):
            return JSONResponse({"error": "login required"}, status_code=401)
        return RedirectResponse("/login", status_code=303)
    if get_movie(movie_id) is not None:  # salviamo solo film che esistono nel catalogo
        add_to_watchlist(user["id"], movie_id)
    if wants_json(request):
        return {"saved": True}
    return RedirectResponse(safe_next(next_url), status_code=303)

@router.post("/watchlist/remove")
def watchlist_remove(request: Request, movie_id: int = Form(...), next_url: str = Form("/")):
    user = get_current_user(request)
    if user is None:
        if wants_json(request):
            return JSONResponse({"error": "login required"}, status_code=401)
        return RedirectResponse("/login", status_code=303)
    remove_from_watchlist(user["id"], movie_id)
    if wants_json(request):
        return {"saved": False}
    return RedirectResponse(safe_next(next_url), status_code=303)

# Segna un film della watchlist come visto (watched=1) o da vedere (watched=0): il ✓ sulla scheda
@router.post("/watchlist/watched")
def watchlist_watched(
    request: Request,
    movie_id: int = Form(...),
    watched: bool = Form(...),
    next_url: str = Form("/watchlist"),
):
    user = get_current_user(request)
    if user is None:
        if wants_json(request):
            return JSONResponse({"error": "login required"}, status_code=401)
        return RedirectResponse("/login", status_code=303)
    set_watched(user["id"], movie_id, watched)
    if wants_json(request):
        return {"watched": watched}
    return RedirectResponse(safe_next(next_url), status_code=303)

# Pagina del profilo con i film salvati
@router.get("/watchlist", response_class=HTMLResponse)
def watchlist_page(
    request: Request,
    genre: str = "",
    decade: str = "",
    runtime: str = "",
    status: str = "",
    sort: str = "recent",
):
    user = get_current_user(request)
    if user is None:
        # Dopo il login l'utente tornerà alla watchlist
        return RedirectResponse("/login?next_url=/watchlist", status_code=303)

    rows = get_watchlist(user["id"])
    ids = [row["movie_id"] for row in rows]

    # Id dei film già visti, per disegnare il ✓ acceso o spento
    watched_ids = {row["movie_id"] for row in rows if row["watched"]}

    # Dati dei film salvati, saltando quelli che non esistono più nel catalogo
    movies = [m for m in (get_movie(movie_id) for movie_id in ids) if m is not None]

    # Numeri per il contatore in cima alla pagina: tutta la watchlist, prima dei filtri
    total = len(movies)
    watched_count = sum(1 for m in movies if m["id"] in watched_ids)

    # Voci dei menu, calcolate su tutta la watchlist (prima di filtrare)
    genres, decades = menu_options(movies)

    # Valori non validi o non più presenti (es. hai tolto l'ultimo film di quel genere): li ignoriamo
    if genre not in genres:
        genre = ""
    if not decade.isdigit() or int(decade) not in decades:
        decade = ""
    if runtime not in RUNTIME_OPTIONS:
        runtime = ""
    if status not in STATUS_OPTIONS:
        status = ""
    if sort not in SORT_OPTIONS:
        sort = "recent"

    movies = apply_filters(movies, watched_ids, genre, decade, runtime, status)
    movies = sort_movies(movies, sort)

    return templates.TemplateResponse(
        request,
        "watchlist.html",
        {
            "title": "My watchlist",
            "movies": movies,
            "genres": genres,
            "genre": genre,
            "decades": decades,
            "decade": decade,
            "runtime": runtime,
            "runtime_options": RUNTIME_OPTIONS,
            "sort": sort,
            "sort_options": SORT_OPTIONS,
            "saved_ids": set(ids),
            "watched_ids": watched_ids,
            "status": status,
            "status_options": STATUS_OPTIONS,
            "total": total,
            "watched_count": watched_count,
        },
    )