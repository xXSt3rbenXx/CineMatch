from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.catalog import get_movie
from app.database import add_to_watchlist, remove_from_watchlist
from app.templating import get_current_user

router = APIRouter()

# Dopo il clic torniamo alla pagina di partenza, ma solo se è un indirizzo del nostro sito
def safe_next(next_url: str) -> str:
    if next_url.startswith("/") and not next_url.startswith("//") and "\\" not in next_url:
        return next_url
    return "/"

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