from fastapi.testclient import TestClient

import app.routers.recommend as recommend
from app.main import app


# Un indirizzo che non esiste mostra la pagina del sito, non il JSON di FastAPI
def test_404_page(client):
    response = client.get("/pippo")
    assert response.status_code == 404
    assert "error-code" in response.text
    assert "Back to home" in response.text


# Le API rispondono ancora in JSON: il JavaScript non saprebbe leggere una pagina
def test_404_api_json(client):
    response = client.get("/api/pippo")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


# Parametri non validi nell'indirizzo: pagina d'errore invece del JSON
def test_invalid_param_page(client):
    response = client.get("/similar", params={"movie": "abc"})
    assert response.status_code == 422
    assert "Something went wrong" in response.text


# Errore imprevisto: pagina generica, senza dettagli tecnici
def test_500_page(monkeypatch):
    def broken(movie_id):
        raise RuntimeError("secret detail")

    monkeypatch.setattr(recommend, "get_movie", broken)
    # raise_server_exceptions=False: il test riceve la pagina invece dell'eccezione.
    # Senza "with" non parte lifespan, quindi il database vero non viene toccato
    test_client = TestClient(app, raise_server_exceptions=False)
    response = test_client.get("/similar", params={"movie": 1})
    assert response.status_code == 500
    assert "problem on our side" in response.text
    assert "secret detail" not in response.text