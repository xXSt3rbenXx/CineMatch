from pathlib import Path

import pandas as pd

# Il file generato da scripts/build_catalog.py (si trova nella cartella principale del progetto)
CATALOG_PATH = Path(__file__).resolve().parents[2] / "dataset" / "catalog" / "catalog.csv"

# Il catalogo resta in memoria: viene caricato una volta sola, all'avvio
_catalog = None


# Legge catalog.csv e lo tiene in memoria, indicizzato per id
def load_catalog() -> None:
    global _catalog
    if not CATALOG_PATH.exists():
        raise RuntimeError(
            "catalog.csv mancante: dalla cartella principale lancia "
            "python scripts/build_catalog.py --catalog-only"
        )
    # keep_default_na=False: i campi vuoti (es. regista) restano testo vuoto
    df = pd.read_csv(CATALOG_PATH, keep_default_na=False)
    _catalog = df.set_index("id", drop=False)


# Restituisce i dati di un film come dizionario, oppure None se l'id non è nel catalogo
def get_movie(movie_id: int) -> dict | None:
    if _catalog is None or movie_id not in _catalog.index:
        return None
    movie = _catalog.loc[movie_id].to_dict()
    movie["genres"] = movie["genres"].split("|")  # da "Crime|Comedy" a ["Crime", "Comedy"]
    return movie

# Cerca i film il cui titolo contiene il testo cercato, senza distinguere le maiuscole.
# I risultati sono ordinati dal più votato, così i film più noti compaiono per primi.
def search_movies(query: str, limit: int = 20) -> list[dict]:
    query = query.strip()
    if _catalog is None or not query:
        return []
    # regex=False: il testo è cercato così com'è, anche con simboli come "(" o "?"
    found = _catalog[_catalog["title"].str.contains(query, case=False, regex=False)]
    found = found.sort_values("vote_count", ascending=False).head(limit)
    return [get_movie(movie_id) for movie_id in found["id"]]
