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
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlists (
    user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, movie_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""

def init_db() -> None:
    """Crea le tabelle se non esistono già."""
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.close()