# Base: Linux leggero con Python 3.14, la stessa versione che usiamo in locale
FROM python:3.14-slim

WORKDIR /app

# Prima solo le librerie: se cambia il codice ma non requirements.txt, Docker non le reinstalla
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Poi il codice dell'app
COPY app ./app

# Per sicurezza l'app non gira come amministratore; data/ ospiterà il database
RUN useradd --create-home appuser && mkdir data && chown appuser data
USER appuser

EXPOSE 8000

# 0.0.0.0 rende l'app raggiungibile da fuori dal container (127.0.0.1 no)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]