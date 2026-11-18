from app.watchlist_filters import apply_filters, decade_of, menu_options, sort_movies

# Film inventati: bastano i campi che usano i filtri, niente catalogo né database
MOVIES = [
    {"id": 1, "genres": ["Drama"], "year": 1994, "runtime": 142, "vote_average": 8.7, "vote_count": 500},
    {"id": 2, "genres": ["Comedy", "Drama"], "year": 2005, "runtime": 95, "vote_average": 6.5, "vote_count": 900},
    {"id": 3, "genres": ["Action"], "year": 2010, "runtime": 148, "vote_average": 8.3, "vote_count": 2000},
    {"id": 4, "genres": ["Comedy"], "year": 1999, "runtime": 85, "vote_average": 7.0, "vote_count": 100},
]


def ids(movies):
    return [m["id"] for m in movies]


def test_decade_of():
    assert decade_of(1994) == 1990
    assert decade_of(2000) == 2000


# I menu contengono solo generi e decenni presenti, in ordine e senza doppioni
def test_menu_options():
    genres, decades = menu_options(MOVIES)
    assert genres == ["Action", "Comedy", "Drama"]
    assert decades == [1990, 2000, 2010]


# Senza filtri tornano tutti i film, nello stesso ordine
def test_no_filters():
    assert ids(apply_filters(MOVIES, set())) == [1, 2, 3, 4]


def test_filter_genre():
    assert ids(apply_filters(MOVIES, set(), genre="Comedy")) == [2, 4]


def test_filter_decade():
    assert ids(apply_filters(MOVIES, set(), decade="1990")) == [1, 4]


# "Up to 95 min" comprende anche i film di 95 minuti esatti
def test_filter_runtime():
    assert ids(apply_filters(MOVIES, set(), runtime="95")) == [2, 4]


def test_filter_status():
    watched = {1, 3}
    assert ids(apply_filters(MOVIES, watched, status="watched")) == [1, 3]
    assert ids(apply_filters(MOVIES, watched, status="to_watch")) == [2, 4]


# Più filtri insieme si sommano
def test_filters_combined():
    assert ids(apply_filters(MOVIES, set(), genre="Comedy", decade="1990")) == [4]


def test_sort_rating():
    assert ids(sort_movies(MOVIES, "rating")) == [1, 3, 4, 2]


def test_sort_votes():
    assert ids(sort_movies(MOVIES, "votes")) == [3, 2, 1, 4]


# Voto dal più basso
def test_sort_lowest():
    assert ids(sort_movies(MOVIES, "lowest")) == [2, 4, 3, 1]


def test_sort_newest_and_oldest():
    assert ids(sort_movies(MOVIES, "newest")) == [3, 2, 4, 1]
    assert ids(sort_movies(MOVIES, "oldest")) == [1, 4, 2, 3]


# "recent" lascia l'ordine di arrivo, e la lista originale non viene modificata
def test_sort_recent_keeps_order():
    result = sort_movies(MOVIES, "recent")
    assert ids(result) == [1, 2, 3, 4]
    assert result is not MOVIES
