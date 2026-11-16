from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.database import init_db
from app.config import COOKIE_SECURE, SECRET_KEY
from app.errors import http_error, server_error, validation_error
from app.routers import auth, home, movies, recommend, watchlist
from app.catalog import load_catalog

BASE_DIR = Path(__file__).resolve().parent


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

# Pagine di errore con la grafica del sito (JSON per il JavaScript e per le API)
app.add_exception_handler(HTTPException, http_error)
app.add_exception_handler(RequestValidationError, validation_error)
app.add_exception_handler(Exception, server_error)


@app.get("/health")
def health():
    return {"status": "ok"}
