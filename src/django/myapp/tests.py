import pytest
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

import django
django.setup()

from django.test import Client


@pytest.fixture
def client():
    return Client()


def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.content == b'OK'


def test_database_endpoint_success(client, monkeypatch):
    def mock_get_db_connection():
        class MockConn:
            info = type('Info', (), {'status': 0})()
            def close(self): pass
        return MockConn()

    import myapp.views
    monkeypatch.setattr('myapp.views.get_db_connection', mock_get_db_connection)

    response = client.get('/database')
    assert response.status_code == 200
    assert b'Connected' in response.content


def test_database_endpoint_failure(client, monkeypatch):
    def mock_get_db_connection():
        raise Exception("Connection failed")

    import myapp.views
    monkeypatch.setattr('myapp.views.get_db_connection', mock_get_db_connection)

    response = client.get('/database')
    assert response.status_code == 500
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

    import myapp.views
    monkeypatch.setattr('myapp.views.get_db_connection', mock_get_db_connection)

    response = client.get('/metrics')
    assert response.status_code == 200
    assert b'"framework": "django"' in response.content


def test_django_info_endpoint(client):
    response = client.get('/django')
    assert response.status_code == 200
    assert b'"framework": "django"' in response.content
    assert b'"status": "working"' in response.content


def test_index_endpoint(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Django Status' in response.content