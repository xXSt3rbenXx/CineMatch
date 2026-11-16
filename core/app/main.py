import os
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.database import init_db
from app.routers import auth, home, movies, recommend, watchlist
from app.catalog import load_catalog

BASE_DIR = Path(__file__).resolve().parent

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
    load_catalog()
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
app.include_router(home.router)
app.include_router(movies.router)
app.include_router(recommend.router)
app.include_router(watchlist.router)


@app.get("/health")
def health():
    return {"status": "ok"}
