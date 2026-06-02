import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.data == b'OK'


def test_database_endpoint_success(monkeypatch):
    def mock_get_db_connection():
        class MockConn:
            info = type('Info', (), {'status': 0})()
            def close(self): pass
        return MockConn()

    monkeypatch.setattr('app.get_db_connection', mock_get_db_connection)

    with app.test_client() as client:
        response = client.get('/database')
        assert response.status_code == 200
        assert b'Connected' in response.data


def test_database_endpoint_failure(monkeypatch):
    def mock_get_db_connection():
        raise Exception("Connection failed")

    monkeypatch.setattr('app.get_db_connection', mock_get_db_connection)

    with app.test_client() as client:
        response = client.get('/database')
        assert response.status_code == 500
        assert b'Error' in response.data


def test_metrics_endpoint_success(monkeypatch):
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

    monkeypatch.setattr('app.get_db_connection', mock_get_db_connection)

    with app.test_client() as client:
        response = client.get('/metrics')
        assert response.status_code == 200
        assert b'"connected": true' in response.data or b'"connected": True' in response.data


def test_index_endpoint():
    with app.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200
        assert b'Python Status' in response.data