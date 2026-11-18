from app.stats import (
    bars, decades, duration, overview, popularity, ratings, records, taste, top_directors, top_genres, votes, watch_next,
)

# Film inventati: bastano i campi che usano le statistiche, niente catalogo né database
MOVIES = [
    {"id": 1, "title": "A", "genres": ["Drama"], "year": 1994, "runtime": 142,
     "director": "Darabont", "vote_average": 8.7, "vote_count": 500},
    {"id": 2, "title": "B", "genres": ["Comedy", "Drama"], "year": 2005, "runtime": 95,
     "director": "Nolan", "vote_average": 6.5, "vote_count": 900},
    {"id": 3, "title": "C", "genres": ["Action"], "year": 2010, "runtime": 148,
     "director": "Nolan", "vote_average": 8.3, "vote_count": 2000},
    {"id": 4, "title": "D", "genres": ["Comedy"], "year": 1999, "runtime": 85,
     "director": "", "vote_average": 7.0, "vote_count": 100},
]


# La barra più lunga è piena, le altre in proporzione
def test_bars():
    assert bars([("x", 4), ("y", 1)]) == [
        {"label": "x", "count": 4, "width": 100},
        {"label": "y", "count": 1, "width": 25},
    ]
    assert bars([]) == []


# 470 minuti in tutto, 290 visti (film 1 e 3): ne restano 180, cioè 2 serate da 2 ore
def test_overview():
    assert overview(MOVIES, {1, 3}) == {
        "saved": 4, "watched": 2, "percent": 50,
        "minutes_watched": 290, "minutes_to_watch": 180, "evenings": 2,
    }


# Watchlist vuota: tutto a zero, senza dividere per zero
def test_overview_empty():
    assert overview([], set())["percent"] == 0


# Un film conta in tutti i suoi generi; a parità, ordine alfabetico
def test_top_genres():
    assert [(g["label"], g["count"]) for g in top_genres(MOVIES)] == [
        ("Comedy", 2), ("Drama", 2), ("Action", 1),
    ]


# Decenni in ordine di tempo, non dal più frequente
def test_decades():
    assert [(d["label"], d["count"]) for d in decades(MOVIES)] == [
        ("1990s", 2), ("2000s", 1), ("2010s", 1),
    ]


# Prima chi ha più film (Nolan, 2), poi gli altri; il regista mancante non conta.
# Di ogni regista c'è anche il film col voto più alto
def test_top_directors():
    result = top_directors(MOVIES)
    assert [(d["name"], d["count"], d["best"]["title"]) for d in result] == [
        ("Nolan", 2, "C"), ("Darabont", 1, "A"),
    ]


# A parità di film conta il voto del film migliore, non l'ordine alfabetico
def test_top_directors_tie():
    allen = {"id": 5, "title": "E", "director": "Allen", "vote_average": 7.0, "vote_count": 300}
    result = top_directors([allen, MOVIES[2]])  # Allen 7.0, Nolan 8.3
    assert [d["name"] for d in result] == ["Nolan", "Allen"]


# Voti di un catalogo inventato da 10 film, in ordine crescente
CATALOG_VOTES = [50, 80, 150, 450, 600, 800, 1000, 1500, 2500, 3000]


# 500 voti: 4 film su 10 ne hanno meno, quindi è più votato del 40% del catalogo
def test_popularity():
    assert popularity(500, CATALOG_VOTES) == 40
    assert popularity(10, CATALOG_VOTES) == 0
    assert popularity(5000, CATALOG_VOTES) == 100


# Popolarità dei 4 film: 40, 60, 80, 20 -> media 50, "un po' e un po'".
# Il meno votato è D, ed è anche la gemma (voto 7.0, sopra la media): compare una volta sola, come gemma
def test_taste():
    result = taste(MOVIES, CATALOG_VOTES, 6.1)
    assert result["popularity"] == 50
    assert result["niche"] == 50
    assert result["verdict"] == "mixed"
    assert result["most_known"]["title"] == "C"
    assert result["hidden_gem"]["title"] == "D"
    assert result["least_known"] is None


# Solo film molto votati: mainstream; solo film poco votati: nicchia
def test_taste_verdicts():
    assert taste([MOVIES[2]], CATALOG_VOTES)["verdict"] == "mainstream"
    assert taste([MOVIES[3]], CATALOG_VOTES)["verdict"] == "niche"


def test_taste_empty():
    assert taste([], CATALOG_VOTES, 6.1) is None


# Media dei film salvati 7.6 contro 6.1 del catalogo: sopra la media
def test_ratings_higher():
    result = ratings(MOVIES, catalog_average=6.1)
    assert result["yours"] == 7.6
    assert result["yours_width"] == 76
    assert result["verdict"] == "higher"
    assert result["top_rated"]["title"] == "A"
    assert result["lowest_rated"]["title"] == "B"


# Differenza piccola: "nella media"; catalogo più alto: "sotto la media"
def test_ratings_close_and_lower():
    assert ratings(MOVIES, catalog_average=7.5)["verdict"] == "close"
    assert ratings(MOVIES, catalog_average=8.5)["verdict"] == "lower"


def test_records():
    result = records(MOVIES)
    assert result["longest"]["title"] == "C"
    assert result["shortest"]["title"] == "D"
    assert result["newest"]["title"] == "C"
    assert result["oldest"]["title"] == "A"
    assert records([]) is None


# Non visti 2 (6.5, 95 min) e 4 (7.0, 85 min): il 4 è il best rated, quindi il quick one è il 2
def test_watch_next():
    result = watch_next(MOVIES, {1, 3})
    assert result["best_rated"]["title"] == "D"
    assert result["quick_one"]["title"] == "B"


# Un solo film da vedere: è il best rated, e non c'è un quick one diverso da lui
def test_watch_next_one_movie():
    result = watch_next(MOVIES, {1, 2, 3})
    assert result["best_rated"]["title"] == "D"
    assert result["quick_one"] is None


# Non visti 1 e 3, entrambi oltre i 100 minuti: niente quick one
def test_watch_next_no_short_movie():
    result = watch_next(MOVIES, {2, 4})
    assert result["best_rated"]["title"] == "A"
    assert result["quick_one"] is None


# Tutto visto: niente consigli
def test_watch_next_all_watched():
    assert watch_next(MOVIES, {1, 2, 3, 4}) is None


# Film con pochi voti: il loro voto TMDB è falsato (9.5 con 3 voti, 0.0 senza voti)
FEW_VOTES = [
    {"id": 6, "title": "F", "genres": ["Drama"], "year": 2001, "runtime": 90,
     "director": "Nolan", "vote_average": 9.5, "vote_count": 3},
    {"id": 7, "title": "G", "genres": ["Drama"], "year": 2002, "runtime": 90,
     "director": "Nolan", "vote_average": 0.0, "vote_count": 0},
]


# I film con pochi voti non diventano né il top né il lowest rated
def test_ratings_ignore_few_votes():
    result = ratings(MOVIES + FEW_VOTES, catalog_average=6.1)
    assert result["yours"] == 7.6  # la media resta quella dei 4 film affidabili
    assert result["top_rated"]["title"] == "A"
    assert result["lowest_rated"]["title"] == "B"


# Se tutti i film hanno pochi voti, si sceglie comunque tra tutti
def test_ratings_only_few_votes():
    result = ratings(FEW_VOTES, catalog_average=6.1)
    assert result["top_rated"]["title"] == "F"
    assert result["lowest_rated"]["title"] == "G"


# Anche il best dei registi e i consigli di Watch next ignorano i film con pochi voti
def test_best_ignores_few_votes():
    nolan = top_directors(MOVIES + FEW_VOTES)[0]
    assert (nolan["name"], nolan["count"], nolan["best"]["title"]) == ("Nolan", 4, "C")
    result = watch_next(MOVIES + FEW_VOTES, {1, 3})
    assert result["best_rated"]["title"] == "D"
    assert result["quick_one"]["title"] == "B"


# Durata leggibile: ore e minuti, solo le parti che servono
def test_duration():
    assert duration(290) == "4 h 50 min"
    assert duration(180) == "3 h"
    assert duration(45) == "45 min"
    assert duration(0) == "0 min"


# Il meno conosciuto è G (0 voti), ma la gemma è D: voto affidabile e sopra la media
def test_hidden_gem_and_least_known():
    result = taste(MOVIES + FEW_VOTES, CATALOG_VOTES, 6.1)
    assert result["hidden_gem"]["title"] == "D"
    assert result["least_known"]["title"] == "G"


# Con la media del catalogo a 7.5 la gemma è A (D ha 7.0); a 9.0 nessun film è sopra la media: niente gemma
def test_hidden_gem_needs_good_rating():
    assert taste(MOVIES, CATALOG_VOTES, 7.5)["hidden_gem"]["title"] == "A"
    result = taste(MOVIES, CATALOG_VOTES, 9.0)
    assert result["hidden_gem"] is None
    assert result["least_known"]["title"] == "D"


# Un solo film, molto votato: non è una gemma "nascosta", e il più e il meno votato coincidono
def test_taste_one_popular_movie():
    result = taste([MOVIES[2]], CATALOG_VOTES, 6.1)
    assert result["hidden_gem"] is None
    assert result["least_known"] is None


# Voti al singolare e al plurale, con il separatore delle migliaia
def test_votes():
    assert votes(1) == "1 vote"
    assert votes(0) == "0 votes"
    assert votes(13752) == "13,752 votes"


# Con un limite più alto si mostrano più generi (qui tutti e 3)
def test_top_genres_limit():
    assert len(top_genres(MOVIES, limit=2)) == 2
    assert len(top_genres(MOVIES, limit=10)) == 3