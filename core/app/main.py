import os
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.database import get_watchlist_ids, init_db
from app.templating import get_current_user, templates
from app.routers import auth, movies, watchlist
from app.catalog import get_movie, load_catalog

BASE_DIR = Path(__file__).resolve().parent

# Legge core/.env e carica le variabili nell'ambiente
load_dotenv(BASE_DIR.parent / ".env")
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY or len(SECRET_KEY) < 32:
    # Meglio fermarsi subito che avviare un'app con sessioni non sicure
    raise RuntimeError("SECRET_KEY mancante o troppo corta (minimo 32 caratteri): crea il file core/.env")

# In locale usiamo http; con HTTPS metti COOKIE_SECURE=true nel .env
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # eseguito una volta all'avvio del server
    load_catalog()  # carica catalog.csv in memoria
    yield

app = FastAPI(title="CineMatch Core", lifespan=lifespan)

# Cookie di sessione firmato con la chiave segreta.
# same_site="lax" limita l'invio del cookie da siti esterni.
# https_only si attiva con COOKIE_SECURE=true nel .env (serve HTTPS).
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",
    https_only=COOKIE_SECURE,
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(auth.router)
app.include_router(movies.router)
app.include_router(watchlist.router)

@app.get("/", response_class=HTMLResponse)
def index(request: Request, movie: int | None = None):
    # movie è l'id del film scelto dai suggerimenti (None se non è stato scelto nulla)
    selected = get_movie(movie) if movie is not None else None
    # Id dei film salvati, per disegnare il cuore pieno o vuoto (None se l'utente non è loggato)
    user = get_current_user(request)
    saved_ids = set(get_watchlist_ids(user["id"])) if user else None
    return templates.TemplateResponse(
        request,
        "index.html",
        {"title": "CineMatch", "movie": selected, "movie_id": movie, "saved_ids": saved_ids},
    )

@app.get("/health")
def health():
    return {"status": "ok"}