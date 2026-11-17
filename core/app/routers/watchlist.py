from urllib.parse import urlencode

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app import stats
from app.catalog import catalog_numbers, get_movie, random_movie
from app.database import add_to_watchlist, get_watchlist, remove_from_watchlist, set_watched
from app.templating import get_current_user, templates, wants_json
from app.security import safe_next

from app.watchlist_filters import (
    RUNTIME_OPTIONS, SORT_OPTIONS, STATUS_OPTIONS, apply_filters, menu_options, sort_movies,
)

router = APIRouter()


# Risposta per chi non ha fatto login: 401 al JavaScript, altrimenti rimando alla pagina di login
def login_required(request: Request):
    if wants_json(request):
        return JSONResponse({"error": "login required"}, status_code=401)
    return RedirectResponse("/login", status_code=303)


@router.post("/watchlist/add")
def watchlist_add(request: Request, movie_id: int = Form(...), next_url: str = Form("/")):
    user = get_current_user(request)
    if user is None:
        return login_required(request)
    if get_movie(movie_id) is not None:  # salviamo solo film che esistono nel catalogo
        add_to_watchlist(user["id"], movie_id)
    if wants_json(request):
        return {"saved": True}
    return RedirectResponse(safe_next(next_url), status_code=303)


@router.post("/watchlist/remove")
def watchlist_remove(request: Request, movie_id: int = Form(...), next_url: str = Form("/")):
    user = get_current_user(request)
    if user is None:
        return login_required(request)
    remove_from_watchlist(user["id"], movie_id)
    if wants_json(request):
        return {"saved": False}
    return RedirectResponse(safe_next(next_url), status_code=303)


# Il ✓ sulla scheda: watched=1 visto, watched=0 da vedere
@router.post("/watchlist/watched")
def watchlist_watched(
    request: Request,
    movie_id: int = Form(...),
    watched: bool = Form(...),
    next_url: str = Form("/watchlist"),
):
    user = get_current_user(request)
    if user is None:
        return login_required(request)
    set_watched(user["id"], movie_id, watched)
    if wants_json(request):
        return {"watched": watched}
    return RedirectResponse(safe_next(next_url), status_code=303)


# Film salvati da un utente, dal più recente, e id di quelli già visti (per il ✓ e le statistiche).
# I film che non esistono più nel catalogo si saltano
def saved_movies(user_id: int) -> tuple[list[dict], set[int]]:
    rows = get_watchlist(user_id)
    watched_ids = {row["movie_id"] for row in rows if row["watched"]}
    movies = [m for m in (get_movie(row["movie_id"]) for row in rows) if m is not None]
    return movies, watched_ids


@router.get("/watchlist", response_class=HTMLResponse)
def watchlist_page(
    request: Request,
    genre: str = "",
    decade: str = "",
    runtime: str = "",
    status: str = "",
    sort: str = "recent",
    movie: int | None = None,
):
    user = get_current_user(request)
    if user is None:
        # Dopo il login l'utente tornerà alla watchlist
        return RedirectResponse("/login?next_url=/watchlist", status_code=303)

    movies, watched_ids = saved_movies(user["id"])

    # Numeri per il contatore: tutta la watchlist (con un filtro attivo, i visti si ricontano più sotto)
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

    # Con un filtro attivo il contatore parla dei film mostrati ("Showing 3 of 42 movies · 1 watched").
    # L'ordinamento non conta: cambia l'ordine, non quanti film si vedono
    filtered = any([genre, decade, runtime, status])
    if filtered:
        watched_count = sum(1 for m in movies if m["id"] in watched_ids)

    # Film scelto dalla ricerca in cima alla pagina (?movie=id), per poterlo aggiungere
    selected = get_movie(movie) if movie is not None else None

    # "Clear" toglie solo i filtri: l'ordinamento e il film scelto con la ricerca restano
    keep = {}
    if sort != "recent":
        keep["sort"] = sort
    if selected is not None:
        keep["movie"] = selected["id"]
    clear_url = "/watchlist?" + urlencode(keep) if keep else "/watchlist"


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
            "saved_ids": {m["id"] for m in movies},
            "watched_ids": watched_ids,
            "status": status,
            "status_options": STATUS_OPTIONS,
            "total": total,
            "watched_count": watched_count,
            "filtered": filtered,
            "clear_url": clear_url,
            "movie": selected,
            "movie_id": movie,
        },
    )

# Statistiche della watchlist: i calcoli sono in app/stats.py, qui si raccolgono per la pagina
@router.get("/stats", response_class=HTMLResponse)
def stats_page(request: Request, skip: int | None = None):
    user = get_current_user(request)
    if user is None:
        return RedirectResponse("/login?next_url=/stats", status_code=303)

    movies, watched_ids = saved_movies(user["id"])
    numbers = catalog_numbers()
    watch_next = stats.watch_next(movies, watched_ids)

    # Generi e decenni stanno affiancati: se i decenni sono più di 5, mostriamo altrettanti generi,
    # così le due sezioni finiscono alla stessa altezza
    decades = stats.decades(movies)
    genres = stats.top_genres(movies, limit=max(stats.TOP_GENRES, len(decades)))

    # Tutto visto: un film a caso tra quelli non salvati. skip è il film mostrato prima di
    # cliccare "Show another": escluso anche lui, il nuovo è sempre diverso
    random_pick = None
    if movies and watch_next is None:
        exclude = {m["id"] for m in movies}
        if skip is not None:
            exclude.add(skip)
        random_pick = random_movie(exclude)

    return templates.TemplateResponse(
        request,
        "stats.html",
        {
            "title": "My stats",
            "overview": stats.overview(movies, watched_ids),
            "genres": genres,
            "decades": decades,
            "taste": stats.taste(movies, numbers["sorted_votes"]),
            "directors": stats.top_directors(movies),
            "ratings": stats.ratings(movies, numbers["average_rating"]),
            "records": stats.records(movies),
            "watch_next": watch_next,
            "random_movie": random_pick,
            "saved_ids": {m["id"] for m in movies},  # per il cuore sulla scheda del film a caso
        },
    )