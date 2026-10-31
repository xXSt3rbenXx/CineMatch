#!/usr/bin/env python3
"""Costruisce il catalogo statico di CineMatch e gli embedding associati.

si esegue una sola volta in fase di preparazione dei dati.
I container leggono soltanto i file prodotti.


Output (dataset/catalog/):
    catalog.csv     metadati dei film (id TMDB, titolo, anno, durata, generi,
                    parole chiave, regia, sinossi, voti), ordinati per id
    embeddings.npy  matrice float32 (n_film x dim), normalizzata L2; la riga i
                    corrisponde alla riga i di catalog.csv
    meta.json       versione del catalogo (hash), modello, numero di film, dimensione

La versione e' un hash di catalog.csv + nome del modello: Core e AI Service la
confrontano all'avvio per garantire di lavorare sullo stesso catalogo.

Uso:
    python scripts/build_catalog.py
    python scripts/build_catalog.py --catalog-only   # senza embedding (niente modello)
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

DEFAULT_MODEL = "all-MiniLM-L6-v2"
MAX_KEYWORDS_IN_TEXT = 15
SEPARATOR = "|"

CATALOG_COLUMNS = [
    "id", "title", "year", "runtime", "genres", "keywords",
    "director", "overview", "vote_average", "vote_count",
]


# --------------------------------------------------------------------------- #
# Parsing dei campi JSON presenti nel CSV
# --------------------------------------------------------------------------- #
def parse_json_list(value) -> list:
    """Interpreta una cella JSON (lista); restituisce [] se vuota o malformata."""
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def extract_names(value) -> list[str]:
    return [
        item["name"].strip()
        for item in parse_json_list(value)
        if isinstance(item, dict) and item.get("name")
    ]


def extract_director(value) -> str:
    for member in parse_json_list(value):
        if isinstance(member, dict) and member.get("job") == "Director" and member.get("name"):
            return member["name"].strip()
    return ""


# --------------------------------------------------------------------------- #
# Costruzione del catalogo
# --------------------------------------------------------------------------- #
def load_raw(movies_path: Path, credits_path: Path) -> pd.DataFrame:
    movies = pd.read_csv(movies_path)
    credits = pd.read_csv(credits_path).rename(columns={"movie_id": "id"})
    credits = credits[["id", "crew"]].drop_duplicates("id")
    return movies.merge(credits, on="id", how="left")


def build_catalog(raw: pd.DataFrame) -> pd.DataFrame:
    """Pulisce i dati grezzi e restituisce il catalogo, ordinato per id."""
    df = raw.copy()
    df = df.dropna(subset=["title"])
    df["title"] = df["title"].astype(str).str.strip()
    df["overview"] = df["overview"].fillna("").astype(str).str.strip()
    df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")
    df["runtime"] = pd.to_numeric(df["runtime"], errors="coerce")
    if "status" in df.columns:
        df = df[df["status"] == "Released"]

    df["genres_list"] = df["genres"].map(extract_names)

    df = df[
        (df["title"] != "")
        & (df["overview"] != "")
        & df["release_date"].notna()
        & (df["runtime"] > 0)
        & (df["genres_list"].map(len) > 0)
    ]
    df = df.drop_duplicates("id").sort_values("id")

    catalog = pd.DataFrame(
        {
            "id": df["id"].astype(int),
            "title": df["title"],
            "year": df["release_date"].dt.year.astype(int),
            "runtime": df["runtime"].astype(int),
            "genres": df["genres_list"].map(SEPARATOR.join),
            "keywords": df["keywords"].map(lambda v: SEPARATOR.join(extract_names(v))),
            "director": df["crew"].map(extract_director),
            "overview": df["overview"],
            "vote_average": pd.to_numeric(df["vote_average"], errors="coerce").fillna(0).round(1),
            "vote_count": pd.to_numeric(df["vote_count"], errors="coerce").fillna(0).astype(int),
        }
    )
    return catalog[CATALOG_COLUMNS].reset_index(drop=True)


def movie_text(row) -> str:
    """Testo da codificare: titolo, generi, parole chiave, regia e sinossi."""
    parts = [f"{row.title}."]
    genres = [g for g in str(row.genres).split(SEPARATOR) if g]
    if genres:
        parts.append("Genres: " + ", ".join(genres) + ".")
    keywords = [k for k in str(row.keywords).split(SEPARATOR) if k][:MAX_KEYWORDS_IN_TEXT]
    if keywords:
        parts.append("Keywords: " + ", ".join(keywords) + ".")
    if row.director:
        parts.append(f"Director: {row.director}.")
    parts.append(str(row.overview))
    return " ".join(parts)


# --------------------------------------------------------------------------- #
# Embedding e versione
# --------------------------------------------------------------------------- #
def compute_embeddings(
    texts: list[str],
    model_name: str = DEFAULT_MODEL,
    encoder: Callable | None = None,
) -> np.ndarray:
    """Codifica i testi e restituisce vettori float32 normalizzati (norma L2 = 1).

    `encoder` permette di iniettare un codificatore alternativo (usato nei test).
    Con vettori normalizzati la cosine similarity e' un semplice prodotto scalare.
    """
    if encoder is None:
        from sentence_transformers import SentenceTransformer 

        encoder = SentenceTransformer(model_name).encode
    vectors = encoder(texts, batch_size=64, show_progress_bar=True, normalize_embeddings=True)
    vectors = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.clip(norms, 1e-12, None)


def catalog_version(csv_bytes: bytes, model_name: str) -> str:
    return hashlib.sha256(csv_bytes + b"\0" + model_name.encode()).hexdigest()[:12]


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #
def run(
    movies_path: Path,
    credits_path: Path,
    out_dir: Path,
    model_name: str = DEFAULT_MODEL,
    catalog_only: bool = False,
    encoder: Callable | None = None,
) -> dict:
    raw = load_raw(movies_path, credits_path)
    catalog = build_catalog(raw)
    if catalog.empty:
        raise SystemExit("Il catalogo e' vuoto dopo la pulizia: controlla i file di input.")
    if not catalog["id"].is_unique:
        raise SystemExit("ID duplicati nel catalogo.")

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "catalog.csv"
    catalog.to_csv(csv_path, index=False, lineterminator="\n")

    meta = {
        "version": catalog_version(csv_path.read_bytes(), model_name),
        "model": model_name,
        "count": int(len(catalog)),
        "dim": None,
    }

    if not catalog_only:
        texts = [movie_text(row) for row in catalog.itertuples(index=False)]
        embeddings = compute_embeddings(texts, model_name, encoder)
        if embeddings.shape[0] != len(catalog):
            raise SystemExit("Numero di embedding diverso dal numero di film.")
        np.save(out_dir / "embeddings.npy", embeddings)
        meta["dim"] = int(embeddings.shape[1])

    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Costruisce catalog.csv, embeddings.npy e meta.json.")
    parser.add_argument("--movies", type=Path, default=Path("dataset/tmdb_5000_movies.csv"))
    parser.add_argument("--credits", type=Path, default=Path("dataset/tmdb_5000_credits.csv"))
    parser.add_argument("--out-dir", type=Path, default=Path("dataset/catalog"))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--catalog-only", action="store_true", help="genera solo catalog.csv e meta.json")
    args = parser.parse_args()

    for path in (args.movies, args.credits):
        if not path.exists():
            raise SystemExit(f"File non trovato: {path}\nScarica il dataset da Kaggle e mettilo in dataset/.")

    meta = run(args.movies, args.credits, args.out_dir, args.model, args.catalog_only)
    print(f"Catalogo: {meta['count']} film, versione {meta['version']}, dim embedding: {meta['dim']}")


if __name__ == "__main__":
    main()