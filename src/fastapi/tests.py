import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.text == 'OK'


def test_database_endpoint_success(client, monkeypatch):
    def mock_get_db_connection():
        class MockConn:
            info = type('Info', (), {'status': 0})()
            def close(self): pass
        return MockConn()

    monkeypatch.setattr('main.get_db_connection', mock_get_db_connection)

    response = client.get('/database')
    assert response.status_code == 200
    assert b'Connected' in response.content


def test_database_endpoint_failure(client, monkeypatch):
    def mock_get_db_connection():
        raise Exception("Connection failed")

    monkeypatch.setattr('main.get_db_connection', mock_get_db_connection)

    response = client.get('/database')
    assert response.status_code == 200
    assert b'Error' in response.content


def test_metrics_endpoint_success(client, monkeypatch):
    def mock_get_db_connection():
        class MockConn:
            info = type('Info', (), {'status': 0})()
            def cursor(self):
                class Cursor:
                    def execute(self, q, p): pass
                    def fetchone(self): return (1024000, 5)
                    def close(self): pass
                return Cursor()
            def close(self): pass
        return MockConn()

    monkeypatch.setattr('main.get_db_connection', mock_get_db_connection)

    response = client.get('/metrics')
    assert response.status_code == 200
    assert 'framework' in response.text


def test_fastapi_info_endpoint(client):
    response = client.get('/fastapi')
    assert response.status_code == 200
    assert 'framework' in response.text
    assert 'fastapi' in response.text.lower()


def test_index_endpoint(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'FastAPI Status' in response.content