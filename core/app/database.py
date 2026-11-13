import sqlite3
from pathlib import Path

# Il database sarà il file core/data/cinematch.db (i file *.db sono già ignorati da git)
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "cinematch.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)  # crea la cartella data/ se non esiste
    conn = sqlite3.connect(DB_PATH)  # se il file non esiste SQLite lo crea
    conn.row_factory = sqlite3.Row  # permette di leggere le colonne per nome
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite non controlla le chiavi esterne se non attivo
    return conn

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlists (
    user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, movie_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""

# Crea le tabelle se non esistono già
def init_db() -> None:
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.close()

# Inserisce un nuovo utente; restituisce il suo id, oppure None se lo username esiste già
def create_user(username: str, password_hash: str) -> int | None:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
        conn.commit()  # senza commit la modifica non viene salvata
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        # lo username è UNIQUE: il database rifiuta i duplicati
        return None
    finally:
        conn.close()

# Cerca un utente per id; restituisce la riga oppure None
def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT id, username FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

# Cerca un utente per username; restituisce la riga oppure None
def get_user_by_username(username: str) -> sqlite3.Row | None:
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    finally:
        conn.close() 

# Aggiunge un film alla watchlist dell'utente (se c'è già, non fa nulla)
def add_to_watchlist(user_id: int, movie_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO watchlists (user_id, movie_id) VALUES (?, ?)",
            (user_id, movie_id),
        )
        conn.commit()
    finally:
        conn.close()


# Toglie un film dalla watchlist dell'utente (se non c'è, non fa nulla)
def remove_from_watchlist(user_id: int, movie_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM watchlists WHERE user_id = ? AND movie_id = ?",
            (user_id, movie_id),
        )
        conn.commit()
    finally:
        conn.close()


# Dice se un film è già nella watchlist dell'utente
def is_in_watchlist(user_id: int, movie_id: int) -> bool:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM watchlists WHERE user_id = ? AND movie_id = ?",
            (user_id, movie_id),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


# Restituisce gli id dei film salvati dall'utente, dal più recente al più vecchio
def get_watchlist_ids(user_id: int) -> list[int]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT movie_id FROM watchlists WHERE user_id = ? ORDER BY rowid DESC",
            (user_id,),
        ).fetchall()
        return [row["movie_id"] for row in rows]
    finally:
        conn.close()
