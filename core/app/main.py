import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.database import init_db
from app.templating import templates
from app.routers import auth

BASE_DIR = Path(__file__).resolve().parent

# Legge core/.env e carica le variabili nell'ambiente
load_dotenv(BASE_DIR.parent / ".env")
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # Meglio fermarsi subito che avviare un'app con sessioni non sicure
    raise RuntimeError("SECRET_KEY mancante: crea il file core/.env")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # eseguito una volta all'avvio del server
    yield

app = FastAPI(title="CineMatch Core", lifespan=lifespan)

# Cookie di sessione firmato con la chiave segreta.
# same_site="lax" limita l'invio del cookie da siti esterni.
# https_only=False perché in locale usiamo http (da attivare con HTTPS in produzione).
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",
    https_only=False,
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(auth.router)

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"title": "CineMatch"})

@app.get("/health")
def health():
    return {"status": "ok"}