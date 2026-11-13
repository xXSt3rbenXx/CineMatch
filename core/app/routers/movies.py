from fastapi import APIRouter

from app.catalog import search_movies

router = APIRouter()


# Suggerimenti per la casella di ricerca: pochi film, solo i dati per riconoscerli
@router.get("/api/search")
def search_suggestions(q: str = ""):
    if len(q.strip()) < 2:
        return []  # con una lettera sola i risultati sarebbero troppi e poco utili
    movies = search_movies(q, limit=8)
    return [{"id": m["id"], "title": m["title"], "year": m["year"]} for m in movies]
