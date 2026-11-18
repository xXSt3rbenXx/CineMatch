# Statistiche della watchlist: funzioni pure, testabili senza HTTP, login né database.
# Ricevono i film salvati (dizionari come quelli di get_movie) e restituiscono i numeri per la pagina
import math
from bisect import bisect_left
from collections import Counter

from app.watchlist_filters import decade_of

TOP_GENRES = 5           # quanti generi mostrare
TOP_DIRECTORS = 5        # quanti registi mostrare al massimo
EVENING_MINUTES = 120    # una "serata" di film, per dire quante ne servono a finire la lista
CLOSE_RATING = 0.3       # entro questa differenza dal catalogo, il voto medio è "nella media"
MAINSTREAM = 80          # popolarità media da qui in su: "big hits"
MIXED = 50               # da qui a MAINSTREAM: un po' e un po'; sotto: "hidden gems"
QUICK_MINUTES = 100      # durata massima del "Quick one for tonight"
MIN_VOTES = 50           # sotto questi voti il voto TMDB non è affidabile (es. 10 con 1 voto, 0 senza voti)


# Barre di un grafico: la più lunga è piena (100%), le altre in proporzione
def bars(counts: list[tuple[str, int]]) -> list[dict]:
    if not counts:
        return []
    top = max(count for _, count in counts)
    return [{"label": label, "count": count, "width": round(count / top * 100)} for label, count in counts]


# Durata leggibile: 290 -> "4 h 50 min", 180 -> "3 h", 45 -> "45 min", 0 -> "0 min"
def duration(minutes: int) -> str:
    hours, minutes = divmod(minutes, 60)
    if hours and minutes:
        return f"{hours} h {minutes} min"
    if hours:
        return f"{hours} h"
    return f"{minutes} min"


# Numero di voti leggibile: 1 -> "1 vote", 13752 -> "13,752 votes"
def votes(count: int) -> str:
    return f"{count:,} {'vote' if count == 1 else 'votes'}"


# Numeri principali: film salvati e visti, ore viste e da vedere, serate per finire la lista
def overview(movies: list[dict], watched_ids: set[int]) -> dict:
    watched = [m for m in movies if m["id"] in watched_ids]
    minutes_watched = sum(m["runtime"] for m in watched)
    minutes_to_watch = sum(m["runtime"] for m in movies) - minutes_watched
    return {
        "saved": len(movies),
        "watched": len(watched),
        "percent": round(len(watched) / len(movies) * 100) if movies else 0,
        "minutes_watched": minutes_watched,
        "minutes_to_watch": minutes_to_watch,
        "evenings": math.ceil(minutes_to_watch / EVENING_MINUTES),
    }


# I generi più presenti; un film conta in ognuno dei suoi generi.
# A parità di film vale l'ordine alfabetico, così il risultato non cambia da una visita all'altra
def top_genres(movies: list[dict], limit: int = TOP_GENRES) -> list[dict]:
    counts = Counter(g for m in movies for g in m["genres"])
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return bars(ordered[:limit])


# Tutti i decenni presenti, in ordine di tempo, come una linea del tempo
def decades(movies: list[dict]) -> list[dict]:
    counts = Counter(decade_of(m["year"]) for m in movies)
    return bars([(f"{decade}s", counts[decade]) for decade in sorted(counts)])


# I film con un voto affidabile, cioè con almeno MIN_VOTES voti: servono per scegliere il film
# col voto più alto o più basso, così un 10 con 1 voto non diventa il "top" e uno 0 senza voti il "lowest".
# Se nessun film ne ha abbastanza li teniamo tutti, così la scelta non resta vuota
def reliable(movies: list[dict]) -> list[dict]:
    return [m for m in movies if m["vote_count"] >= MIN_VOTES] or movies


# I registi più presenti nella lista: prima chi ha più film, a parità chi ha il film col voto più alto.
# Così la classifica è piena anche quando ogni regista compare una volta sola (il regista mancante non conta)
def top_directors(movies: list[dict]) -> list[dict]:
    films = {}  # regista -> i suoi film
    for m in movies:
        if m["director"]:
            films.setdefault(m["director"], []).append(m)
    # Il film col voto più alto di ogni regista, tra quelli con un voto affidabile
    best = {name: max(reliable(group), key=lambda m: m["vote_average"]) for name, group in films.items()}
    ordered = sorted(films, key=lambda name: (-len(films[name]), -best[name]["vote_average"], name))
    return [{"name": name, "count": len(films[name]), "best": best[name]} for name in ordered[:TOP_DIRECTORS]]


# Popolarità di un film: la percentuale di film del catalogo con meno voti (64 = più votato del 64%).
# catalog_votes sono i voti di tutto il catalogo, in ordine crescente (vedi catalog_numbers)
def popularity(votes: int, catalog_votes: list[int]) -> int:
    return round(bisect_left(catalog_votes, votes) / len(catalog_votes) * 100)


# Nicchia o mainstream: la popolarità media dei film salvati, confrontata con tutto il catalogo
def taste(movies: list[dict], catalog_votes: list[int]) -> dict | None:
    if not movies:
        return None
    average = round(sum(popularity(m["vote_count"], catalog_votes) for m in movies) / len(movies))
    if average >= MAINSTREAM:
        verdict = "mainstream"
    elif average >= MIXED:
        verdict = "mixed"
    else:
        verdict = "niche"
    gem = min(movies, key=lambda m: m["vote_count"])
    return {
        "popularity": average,
        "niche": 100 - average,  # posizione del segno sulla scala, da Mainstream (0) a Niche (100)
        "verdict": verdict,
        "hidden_gem": gem,
        "most_known": max(movies, key=lambda m: m["vote_count"]),
        "gem_popularity": popularity(gem["vote_count"], catalog_votes),
    }


# Voto medio dei film salvati, confrontato con quello di tutto il catalogo.
# Contano solo i film con un voto affidabile: un film senza voti (0.0) abbasserebbe la media senza motivo
def ratings(movies: list[dict], catalog_average: float) -> dict:
    rated = reliable(movies)
    average = sum(m["vote_average"] for m in rated) / len(rated) if movies else 0
    difference = average - catalog_average

    if difference >= CLOSE_RATING:
        verdict = "higher"
    elif difference <= -CLOSE_RATING:
        verdict = "lower"
    else:
        verdict = "close"
    return {
        "yours": round(average, 1),
        "catalog": round(catalog_average, 1),
        # Larghezza delle barre su una scala da 0 a 10
        "yours_width": round(average * 10),
        "catalog_width": round(catalog_average * 10),
        "verdict": verdict,
        # Il più alto e il più basso tra i film con un voto affidabile
        "top_rated": max(rated, key=lambda m: m["vote_average"]) if movies else None,
        "lowest_rated": min(rated, key=lambda m: m["vote_average"]) if movies else None,
    }


# Primati tra i film salvati; a parità vince il primo trovato (il salvato più di recente)
def records(movies: list[dict]) -> dict | None:
    if not movies:
        return None
    return {
        "longest": max(movies, key=lambda m: m["runtime"]),
        "shortest": min(movies, key=lambda m: m["runtime"]),
        "newest": max(movies, key=lambda m: m["year"]),
        "oldest": min(movies, key=lambda m: m["year"]),
    }


# Consigli dalla propria lista, tra i film non visti:
# - best_rated: quello col voto più alto
# - quick_one: il voto più alto tra quelli di QUICK_MINUTES o meno, escluso best_rated (None se non c'è)
def watch_next(movies: list[dict], watched_ids: set[int]) -> dict | None:
    to_watch = [m for m in movies if m["id"] not in watched_ids]
    if not to_watch:
        return None
    best = max(reliable(to_watch), key=lambda m: m["vote_average"])
    quick = [m for m in to_watch if m["runtime"] <= QUICK_MINUTES and m is not best]
    return {
        "best_rated": best,
        "quick_one": max(reliable(quick), key=lambda m: m["vote_average"]) if quick else None,
    }