from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.database import get_user_by_id

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=BASE_DIR / "templates")


# Restituisce l'utente della sessione, oppure None se non è loggato o non esiste più
def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    user = get_user_by_id(user_id)
    if user is None:
        request.session.clear()  # l'utente non esiste più: togliamo l'id dalla sessione
    return user


# Rende la funzione usabile dentro i template
templates.env.globals["get_current_user"] = get_current_user
