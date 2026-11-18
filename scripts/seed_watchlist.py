#!/usr/bin/env python3

# Riempie la watchlist di un utente con film vari, per provare filtri, ordinamenti e statistiche.
# Prima copre ogni "parametro" (ogni genere, decennio, fascia di durata, di voto e di popolarità,
# più i casi limite), poi completa a rotazione sui generi; circa il 40% dei film viene segnato come visto.
# Con lo stesso --seed escono sempre gli stessi film.

# Uso (dalla cartella core, con il .venv attivo; l'utente deve essere già registrato):
#   python ../scripts/seed_watchlist.py nomeutente
#   python ../scripts/seed_watchlist.py nomeutente --count 50 --seed 7 --reset

import argparse
import random
import sys
from pathlib import Path

# Permette di importare il pacchetto "app" del Core da qualsiasi cartella
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from app import catalog, database  # noqa: E402
from app.stats import MIN_VOTES  # noqa: E402
from app.watchlist_filters import decade_of  # noqa: E402

WATCHED_SHARE = 0.4  # quota di film segnati come visti


# Tutti i "parametri" da coprire: nome leggibile -> condizione sul film
def categories(movies: list[dict]) -> dict:
    groups = {}
    for genre in sorted({g for m in movies for g in m["genres"]}):
        groups[f"genre {genre}"] = lambda m, g=genre: g in m["genres"]
    for decade in sorted({decade_of(m["year"]) for m in movies}):
        groups[f"decade {decade}s"] = lambda m, d=decade: decade_of(m["year"]) == d
    # Durata: una fascia per ogni voce del filtro, più i film oltre i 180 minuti
    groups["runtime <= 90"] = lambda m: m["runtime"] <= 90
    groups["runtime 91-120"] = lambda m: 90 < m["runtime"] <= 120
    groups["runtime 121-150"] = lambda m: 120 < m["runtime"] <= 150
    groups["runtime 151-180"] = lambda m: 150 < m["runtime"] <= 180
    groups["runtime > 180"] = lambda m: m["runtime"] > 180
    # Voto (solo voti affidabili)
    groups["rating < 5"] = lambda m: m["vote_count"] >= MIN_VOTES and m["vote_average"] < 5
    groups["rating 5-6.4"] = lambda m: m["vote_count"] >= MIN_VOTES and 5 <= m["vote_average"] < 6.5
    groups["rating 6.5-7.4"] = lambda m: m["vote_count"] >= MIN_VOTES and 6.5 <= m["vote_average"] < 7.5
    groups["rating >= 7.5"] = lambda m: m["vote_count"] >= MIN_VOTES and m["vote_average"] >= 7.5
    # Popolarità (numero di voti)
    groups["votes 1-49"] = lambda m: 0 < m["vote_count"] < MIN_VOTES
    groups["votes 50-499"] = lambda m: MIN_VOTES <= m["vote_count"] < 500
    groups["votes 500-2999"] = lambda m: 500 <= m["vote_count"] < 3000
    groups["votes >= 3000"] = lambda m: m["vote_count"] >= 3000
    # Casi limite per le statistiche
    groups["no votes (0.0)"] = lambda m: m["vote_count"] == 0
    groups["high rating, few votes"] = lambda m: m["vote_count"] < MIN_VOTES and m["vote_average"] >= 8
    groups["no director"] = lambda m: not m["director"]
    return groups


def pick_movies(movies: list[dict], count: int, rng: random.Random) -> list[dict]:
    chosen, chosen_ids = [], set()

    def take(candidates):
        candidates = [m for m in candidates if m["id"] not in chosen_ids]
        if candidates and len(chosen) < count:
            movie = rng.choice(candidates)
            chosen.append(movie)
            chosen_ids.add(movie["id"])

    # 1) Almeno un film per ogni parametro (se nessun film scelto lo copre già)
    for condition in categories(movies).values():
        if not any(condition(m) for m in chosen):
            take([m for m in movies if condition(m)])

    # 2) Il resto a rotazione sui generi, così nessun genere domina
    genres = sorted({g for m in movies for g in m["genres"]})
    while len(chosen) < count and len(chosen_ids) < len(movies):
        for genre in rng.sample(genres, len(genres)):
            take([m for m in movies if genre in m["genres"]])
    return chosen


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggiunge film vari alla watchlist di un utente")
    parser.add_argument("username")
    parser.add_argument("--count", type=int, default=100, help="quanti film aggiungere (default 100)")
    parser.add_argument("--seed", type=int, default=42, help="stesso seed = stessi film")
    parser.add_argument("--reset", action="store_true", help="svuota prima la watchlist dell'utente")
    args = parser.parse_args()

    database.init_db()
    user = database.get_user_by_username(args.username)
    if user is None:
        sys.exit(f"Utente '{args.username}' non trovato: registralo prima dal sito")

    if args.reset:
        for movie_id in database.get_watchlist_ids(user["id"]):
            database.remove_from_watchlist(user["id"], movie_id)

    catalog.load_catalog()
    already = set(database.get_watchlist_ids(user["id"]))
    movies = [catalog.get_movie(int(i)) for i in catalog._catalog["id"] if int(i) not in already]

    rng = random.Random(args.seed)
    chosen = pick_movies(movies, args.count, rng)
    rng.shuffle(chosen)  # ordine di aggiunta mescolato, per l'ordinamento "Recently added"

    watched = 0
    for movie in chosen:
        database.add_to_watchlist(user["id"], movie["id"])
        if rng.random() < WATCHED_SHARE:
            database.set_watched(user["id"], movie["id"], True)
            watched += 1

    print(f"Aggiunti {len(chosen)} film alla watchlist di {user['username']} ({watched} segnati come visti)")
    # Parametri rimasti scoperti (succede solo con --count piccolo o catalogo diverso)
    missing = [name for name, cond in categories(movies).items() if not any(cond(m) for m in chosen)]
    if missing:
        print("Non coperti:", ", ".join(missing))


if __name__ == "__main__":
    main()
