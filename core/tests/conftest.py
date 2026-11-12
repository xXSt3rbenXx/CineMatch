import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app

# Ogni test usa un database temporaneo, così non tocca core/data/cinematch.db
@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    # con il with parte anche lifespan, quindi viene creato il database vuoto
    with TestClient(app) as test_client:
        yield test_client
