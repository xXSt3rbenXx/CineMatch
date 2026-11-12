import os
import re
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.database import create_user, get_user_by_username, init_db
from app.security import hash_password, verify_password

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
templates = Jinja2Templates(directory=BASE_DIR / "templates")

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"title": "CineMatch"})

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(
        request, "register.html", {"title": "Register", "error": None}
    )

@app.post("/register", response_class=HTMLResponse)
def register(request: Request, username: str = Form(...), password: str = Form(...)):
    username = username.strip()

    # Controlli lato server (quelli del browser si possono aggirare)
    error = None
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,30}", username):
        error = "Username must be 3 to 30 characters long and can only contain letters, numbers, underscores ( _ ), dots ( . ) and hyphens ( - )."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."
    elif len(password.encode("utf-8")) > 72:
        # bcrypt non accetta password più lunghe di 72 byte
        error = "Password is too long."

    if error is None:
        user_id = create_user(username, hash_password(password))
        if user_id is None:
            error = "Username already taken."

    if error:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"title": "Register", "error": error},
            status_code=400,
        )

    # Registrazione riuscita: salviamo l'id nella sessione (utente già loggato)
    request.session["user_id"] = user_id
    return RedirectResponse("/", status_code=303)

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request, "login.html", {"title": "Log in", "error": None}
    )

@app.post("/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    username = username.strip()
    user = get_user_by_username(username)

    # bcrypt non accetta password oltre i 72 byte: non possono corrispondere a nessun hash
    valid = (
        user is not None
        and len(password.encode("utf-8")) <= 72
        and verify_password(password, user["password_hash"])
    )

    if not valid:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"title": "Log in", "error": "Invalid username or password."},
            status_code=401,
        )

    # Login riuscito: svuota la sessione precedente e salva l'id dell'utente
    request.session.clear()
    request.session["user_id"] = user["id"]
    return RedirectResponse("/", status_code=303)

@app.post("/logout")
def logout(request: Request):
    request.session.clear()  # cancella i dati della sessione, l'utente risulta scollegato
    return RedirectResponse("/", status_code=303)