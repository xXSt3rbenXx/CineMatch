import re

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.database import create_user, get_user_by_username
from app.security import hash_password, safe_next, verify_password
from app.templating import templates

router = APIRouter()

@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(
        request, "register.html", {"title": "Register", "error": None}
    )

@router.post("/register", response_class=HTMLResponse)
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

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next_url: str = "/"):
    # next_url: la pagina dove tornare dopo il login (es. /login?next_url=/watchlist)
    return templates.TemplateResponse(
        request,
        "login.html",
        {"title": "Log in", "error": None, "next_url": safe_next(next_url)},
    )

@router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next_url: str = Form("/"),
):
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
            {"title": "Log in", "error": "Invalid username or password.", "next_url": safe_next(next_url)},
            status_code=401,
        )

    # Login riuscito: svuota la sessione precedente e salva l'id dell'utente
    request.session.clear()
    request.session["user_id"] = user["id"]
    return RedirectResponse(safe_next(next_url), status_code=303)

@router.post("/logout")
def logout(request: Request):
    request.session.clear()  # cancella i dati della sessione, l'utente risulta scollegato
    return RedirectResponse("/", status_code=303)