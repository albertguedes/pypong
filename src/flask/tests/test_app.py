import pytest
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "ok"
    assert data["database"] == "connected"


def test_health_endpoint_db_down(monkeypatch):
    def mock_fail(*a, **kw):
        raise Exception("DB down")

    monkeypatch.setattr("app.get_db_connection", mock_fail)
    with app.test_client() as client:
        response = client.get("/health")
        assert response.status_code == 503
        data = json.loads(response.data)
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_database_endpoint_success(monkeypatch):
    def mock_get_db_connection():
        class MockConn:
            info = type("Info", (), {"status": 0})()

            def close(self):
                pass

        return MockConn()

    monkeypatch.setattr("app.get_db_connection", mock_get_db_connection)

    with app.test_client() as client:
        response = client.get("/database")
        assert response.status_code == 200
        assert b"Connected" in response.data


def test_database_endpoint_failure(monkeypatch):
    def mock_get_db_connection():
        raise Exception("Connection failed")

    monkeypatch.setattr("app.get_db_connection", mock_get_db_connection)

    with app.test_client() as client:
        response = client.get("/database")
        assert response.status_code == 500


def test_metrics_endpoint_success(monkeypatch):
    def mock_get_db_connection():
        class MockConn:
            info = type("Info", (), {"status": 0})()

            def cursor(self):
                class Cursor:
                    def execute(self, q, p):
                        pass

                    def fetchone(self):
                        return (1024000, 5)

                    def close(self):
                        pass

                return Cursor()

            def close(self):
                pass

        return MockConn()

    monkeypatch.setattr("app.get_db_connection", mock_get_db_connection)

    with app.test_client() as client:
        response = client.get("/metrics")
        assert response.status_code == 200
        assert b"pypong_database_connected" in response.data
        assert response.content_type == "text/plain; charset=utf-8"


def test_flask_info_endpoint(client):
    with app.test_client() as client:
        response = client.get("/v1")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["framework"] == "flask"
        assert data["status"] == "working"


def test_index_endpoint(client):
    with app.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200
        assert b"Flask" in response.data


def test_auth_register_success(client):
    response = client.post(
        "/flask/v1/auth/register",
        data=json.dumps({"username": "testuser", "password": "securepass123"}),
        content_type="application/json",
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["username"] == "testuser"


def test_auth_register_missing_fields(client):
    response = client.post(
        "/flask/v1/auth/register",
        data=json.dumps({"username": ""}),
        content_type="application/json",
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_auth_register_weak_password(client):
    response = client.post(
        "/flask/v1/auth/register",
        data=json.dumps({"username": "testuser2", "password": "short"}),
        content_type="application/json",
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_auth_token_success(client):
    client.post(
        "/flask/v1/auth/register",
        data=json.dumps({"username": "logintest", "password": "securepass123"}),
        content_type="application/json",
    )
    response = client.post(
        "/flask/v1/auth/token",
        data=json.dumps({"username": "logintest", "password": "securepass123"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"


def test_auth_token_wrong_password(client):
    client.post(
        "/flask/v1/auth/register",
        data=json.dumps({"username": "authtest", "password": "securepass123"}),
        content_type="application/json",
    )
    response = client.post(
        "/flask/v1/auth/token",
        data=json.dumps({"username": "authtest", "password": "wrongpassword"}),
        content_type="application/json",
    )
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"


def test_auth_token_missing_credentials(client):
    response = client.post(
        "/flask/v1/auth/token",
        data=json.dumps({"username": ""}),
        content_type="application/json",
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_protected_endpoint_without_token(client):
    response = client.get("/flask/v1/protected")
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data["error"]["code"] == "UNAUTHORIZED"


def test_protected_endpoint_with_valid_token(client):
    client.post(
        "/flask/v1/auth/register",
        data=json.dumps({"username": "prottest", "password": "securepass123"}),
        content_type="application/json",
    )
    token_response = client.post(
        "/flask/v1/auth/token",
        data=json.dumps({"username": "prottest", "password": "securepass123"}),
        content_type="application/json",
    )
    token = json.loads(token_response.data)["access_token"]

    response = client.get(
        "/flask/v1/protected", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["message"] == "You have access"
    assert data["user"] == "prottest"


def test_protected_endpoint_with_invalid_token(client):
    response = client.get(
        "/flask/v1/protected", headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data["error"]["code"] == "UNAUTHORIZED"


def test_request_id_in_response_headers(client):
    response = client.get("/health")
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0
