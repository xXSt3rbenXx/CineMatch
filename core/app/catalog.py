import re
import unicodedata
from pathlib import Path

import pandas as pd

# Il file generato da scripts/build_catalog.py (si trova nella cartella principale del progetto)
CATALOG_PATH = Path(__file__).resolve().parents[2] / "dataset" / "catalog" / "catalog.csv"

# Il catalogo resta in memoria: viene caricato una volta sola, all'avvio
_catalog = None
_search = None  # i titoli in versione "pulita", per la ricerca (vedi normalize)


def load_catalog() -> None:
    global _catalog, _search
    if not CATALOG_PATH.exists():
        raise RuntimeError(
            "catalog.csv mancante: dalla cartella principale lancia "
            "python scripts/build_catalog.py --catalog-only"
        )
    # keep_default_na=False: i campi vuoti (es. regista) restano testo vuoto
    df = pd.read_csv(CATALOG_PATH, keep_default_na=False)
    _catalog = df.set_index("id", drop=False)

    # Titoli puliti, preparati una volta sola all'avvio invece che a ogni ricerca
    words = _catalog["title"].map(normalize)
    _search = pd.DataFrame({
        "words": words,                                    # "the godfather part ii"
        "compact": words.str.replace(" ", ""),             # "thegodfatherpartii"
        "no_article": words.str.replace(r"^(the|a|an) ", "", regex=True).str.replace(" ", ""),
    })
  

# Numeri di tutto il catalogo, per confrontare i gusti dell'utente nella pagina delle statistiche.
# Calcolati dal catalogo caricato, così valgono anche se un giorno il catalogo cambia
def catalog_numbers() -> dict:
    return {
        "average_rating": float(_catalog["vote_average"].mean()),
        "sorted_votes": sorted(_catalog["vote_count"]),  # voti di tutti i film, dal meno votato
    }


# Un film a caso del catalogo, escludendo gli id dati (es. quelli già in watchlist); None se non ne resta nessuno
def random_movie(exclude_ids: set[int]) -> dict | None:
    candidates = _catalog[~_catalog["id"].isin(exclude_ids)]
    if candidates.empty:
        return None
    return get_movie(int(candidates["id"].sample().iloc[0]))


# Restituisce i dati di un film come dizionario, oppure None se l'id non è nel catalogo
def get_movie(movie_id: int) -> dict | None:
    if _catalog is None or movie_id not in _catalog.index:
        return None
    movie = _catalog.loc[movie_id].to_dict()
    movie["genres"] = movie["genres"].split("|")  # da "Crime|Comedy" a ["Crime", "Comedy"]
    return movie


# Versione "pulita" di un testo, per confrontare titoli e ricerche senza badare alla forma:
# minuscole, niente accenti, niente punteggiatura ("Spider-Man" -> "spiderman", "Amélie" -> "amelie")
def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())  # separa le lettere dagli accenti...
    text = "".join(c for c in text if not unicodedata.combining(c))  # ...e toglie gli accenti
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())  # spazi doppi ridotti a uno


# Cerca i film per titolo, ordinati per come il testo corrisponde e poi per popolarità:
# 1) il titolo inizia così (anche saltando "The", "A", "An": "godfather" trova "The Godfather")
# 2) una parola del titolo inizia così ("potter" trova "Harry Potter and...")
# 3) le lettere sono in mezzo a una parola ("st" trova "Interstellar"): ultimi, ma non spariscono
def search_movies(query: str, limit: int = 20) -> list[dict]:
    words = normalize(query)
    compact = words.replace(" ", "")  # senza spazi: "spider man" trova anche "Spider-Man"
    if _catalog is None or not compact:
        return []

    starts = _search["no_article"].str.startswith(compact) | _search["compact"].str.startswith(compact)
    word_starts = _search["words"].str.contains(r"\b" + re.escape(words), regex=True)
    inside = _search["compact"].str.contains(compact, regex=False)

    # Livello di ogni film: si parte da 3 e si sale se corrisponde meglio
    rank = pd.Series(3, index=_catalog.index).mask(word_starts, 2).mask(starts, 1)
    found = _catalog.assign(rank=rank)[starts | word_starts | inside]
    found = found.sort_values(["rank", "vote_count"], ascending=[True, False]).head(limit)
    return [get_movie(movie_id) for movie_id in found["id"]]