import bcrypt

# Trasforma la password in un hash da salvare nel database
def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


# Controlla se la password corrisponde all'hash salvato
def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

# Dopo un'azione torniamo alla pagina di partenza, ma solo se è un indirizzo del nostro sito
# (evita che un link costruito ad arte mandi l'utente su un sito esterno)
def safe_next(next_url: str) -> str:
    if next_url.startswith("/") and not next_url.startswith("//") and "\\" not in next_url:
        return next_url
    return "/"
