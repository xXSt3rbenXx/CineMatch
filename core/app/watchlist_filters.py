# Filtri e ordinamento della watchlist: funzioni pure, testabili senza HTTP, login né database

SORT_OPTIONS = {
    "recent": "Recently added",
    "rating": "Highest rated",
    "votes": "Most voted",
    "newest": "Newest releases",
    "oldest": "Oldest releases",
}

# Durata massima: valore nell'indirizzo (minuti) -> testo nel menu
RUNTIME_OPTIONS = {
    "90": "Up to 90 min",
    "120": "Up to 120 min",
    "150": "Up to 150 min",
    "180": "Up to 180 min",
}

# Stato di visione: valore nell'indirizzo -> testo nel menu
STATUS_OPTIONS = {
    "watched": "Watched",
    "to_watch": "To watch",
}


# Decennio di un anno: 1994 -> 1990
def decade_of(year: int) -> int:
    return year // 10 * 10


# Voci dei menu: generi e decenni presenti tra i film dati
def menu_options(movies: list[dict]) -> tuple[list[str], list[int]]:
    genres = sorted({g for m in movies for g in m["genres"]})
    decades = sorted({decade_of(m["year"]) for m in movies})
    return genres, decades


# Tiene solo i film che rispettano i filtri; un valore vuoto significa "nessun filtro"
def apply_filters(movies, watched_ids, genre="", decade="", runtime="", status=""):
    if genre:
        movies = [m for m in movies if genre in m["genres"]]
    if decade:
        movies = [m for m in movies if decade_of(m["year"]) == int(decade)]
    if runtime:
        movies = [m for m in movies if m["runtime"] <= int(runtime)]
    if status == "watched":
        movies = [m for m in movies if m["id"] in watched_ids]
    elif status == "to_watch":
        movies = [m for m in movies if m["id"] not in watched_ids]
    return movies


# Ordina i film; "recent" lascia l'ordine di arrivo (dal più recente salvato)
def sort_movies(movies, sort):
    if sort == "rating":
        return sorted(movies, key=lambda m: m["vote_average"], reverse=True)
    if sort == "votes":
        return sorted(movies, key=lambda m: m["vote_count"], reverse=True)
    if sort == "newest":
        return sorted(movies, key=lambda m: m["year"], reverse=True)
    if sort == "oldest":
        return sorted(movies, key=lambda m: m["year"])
    return list(movies)
