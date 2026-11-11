from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Cartella in cui si trova questo file (core/app), indipendente da dove lanci uvicorn
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="CineMatch Core")  # è la variabile cercata da "uvicorn app.main:app"

# Rende accessibile la cartella static/ all'indirizzo /static/... (CSS, immagini)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Dice a Jinja2 dove cercare i file HTML da riempire con i dati
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Decoratore: "quando arriva un GET su / esegui la funzione qui sotto"
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    # Carica index.html e sostituisce {{ title }} col valore del dizionario
    return templates.TemplateResponse(request, "index.html", {"title": "CineMatch"})


@app.get("/health")
def health():
    # Un dict Python viene convertito automaticamente in JSON da FastAPI
    return {"status": "ok"}