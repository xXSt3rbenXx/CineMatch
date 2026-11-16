import os
from pathlib import Path

from dotenv import load_dotenv

# Impostazioni del Core, lette dal file core/.env (o dalle variabili d'ambiente di Docker).
# Qui ci sono solo i nomi e i default innocui: i valori veri restano nel .env, che non va su git

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Chiave che firma il cookie di sessione: obbligatoria, quindi niente default
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    # Meglio fermarsi subito che avviare un'app con sessioni non sicure
    raise RuntimeError("SECRET_KEY mancante o troppo corta (minimo 32 caratteri): crea il file core/.env")

# In locale usiamo http; con HTTPS metti COOKIE_SECURE=true nel .env
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

# Token di TMDB per le locandine: facoltativo, senza si vedono i placeholder
TMDB_TOKEN = os.getenv("TMDB_TOKEN")