import os
import sys
import json
import uuid
import logging
from datetime import datetime, timezone
from functools import wraps

import importlib.metadata
_flask_version = importlib.metadata.version("flask")
from flask import Flask, Response, request, g, jsonify
import psycopg2
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    integrations=[FlaskIntegration()],
    dsn=os.getenv("SENTRY_DSN", ""),
    environment=os.getenv("ENVIRONMENT", "development"),
    traces_sample_rate=float(os.getenv("OTEL_SAMPLE_RATE", "0.0")),
    send_default_pii=False,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shared.auth import (
    authenticate,
    jwt_required,
    create_user,
    USERS_DB,
    JWT_SECRET,
    ACCESS_TOKEN_TTL_MINUTES,
)
from shared.errors import error_response, get_request_id
from shared.tracing import setup_logging, get_log_extra

logger = setup_logging("pypong.flask", logging.INFO)

app = Flask(__name__)


@app.before_request
def before_request():
    g.request_id = get_request_id()
    logger.info(
        f"Request started",
        extra=get_log_extra(g.request_id, method=request.method, path=request.path)
    )


@app.after_request
def after_request(response):
    response.headers["X-Request-ID"] = g.get("request_id", "")
    logger.info(
        f"Request completed",
        extra=get_log_extra(
            g.request_id,
            method=request.method,
            path=request.path,
            status=response.status_code,
        )
    )
    return response


@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(
        f"Unhandled exception: {str(e)}",
        extra=get_log_extra(g.request_id),
        exc_info=True,
    )
    sentry_sdk.capture_exception(e)
    return error_response(
        code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        details={},
        status=500,
    )


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "dockerdb"),
        user=os.getenv("POSTGRES_USER", "docker"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
    )


@app.route("/health", methods=["GET"])
def health():
    try:
        conn = get_db_connection()
        conn.info.status
        conn.close()
        return Response(
            json.dumps(
                {
                    "status": "ok",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "database": "connected",
                }
            ),
            status=200,
            mimetype="application/json",
        )
    except Exception:
        return error_response(
            code="SERVICE_UNAVAILABLE",
            message="Database connectivity check failed",
            details={},
            status=503,
        )


@app.route("/flask/v1/auth/token", methods=["POST"])
def auth_token():
    body = request.get_json(silent=True) or {}
    username = body.get("username", "").strip()
    password = body.get("password", "")

    if not username or not password:
        return error_response(
            code="VALIDATION_ERROR",
            message="username and password are required",
            details={"fields": ["username", "password"]},
            status=400,
        )

    result = authenticate(username, password)
    if result is None:
        logger.warning(
            f"Failed login attempt for user: {username}",
            extra=get_log_extra(g.request_id),
        )
        return error_response(
            code="AUTHENTICATION_FAILED",
            message="Invalid username or password",
            details={},
            status=401,
        )

    logger.info(
        f"User authenticated: {username}",
        extra=get_log_extra(g.request_id, user=username),
    )
    return jsonify(result)


@app.route("/flask/v1/auth/register", methods=["POST"])
def auth_register():
    body = request.get_json(silent=True) or {}
    username = body.get("username", "").strip()
    password = body.get("password", "")

    if not username or not password:
        return error_response(
            code="VALIDATION_ERROR",
            message="username and password are required",
            details={"fields": ["username", "password"]},
            status=400,
        )
    if len(password) < 8:
        return error_response(
            code="VALIDATION_ERROR",
            message="password must be at least 8 characters",
            details={"min_length": 8},
            status=400,
        )

    try:
        user = create_user(username, password)
    except ValueError as e:
        return error_response(
            code="USER_ALREADY_EXISTS",
            message=str(e),
            details={},
            status=409,
        )

    logger.info(
        f"New user registered: {username}",
        extra=get_log_extra(g.request_id, user=username),
    )
    return jsonify({"message": "User created", "username": user["username"]}), 201


@app.route("/flask/v1/protected", methods=["GET"])
@jwt_required
def protected():
    return jsonify(
        {
            "message": "You have access",
            "user": g.current_user,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@app.route("/", methods=["GET"])
def index():
    status = {
        "framework": "flask",
        "status": "ok",
        "version": _flask_version,
        "python_version": os.popen("python --version").read().strip(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoints": {
            "info": "/flask",
            "health": "/health",
            "database": "/database",
            "metrics": "/metrics",
            "api_auth": "/flask/v1/auth/token",
            "api_protected": "/flask/v1/protected",
        },
    }
    html = """<!DOCTYPE html>
<html>
<head><title>Flask Status</title></head>
<body>
<h1>Flask Status</h1>
<ul>
"""
    for key, value in status.items():
        html += f"<li><strong>{key}:</strong> {value}</li>\n"
    html += "</ul>\n</body>\n</html>\n"
    return Response(html, mimetype="text/html")


@app.route("/database", methods=["GET"])
def database():
    if request.headers.get("Authorization", "").startswith("Bearer "):
        return error_response(
            code="FORBIDDEN",
            message="Unauthenticated access not allowed",
            details={},
            status=403,
        )
    try:
        conn = get_db_connection()
        status = conn.info.status
        conn.close()
        return Response(
            f"Connected to '{os.getenv('POSTGRES_DB')}' on '{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}'.",
            mimetype="text/plain",
        )
    except Exception:
        return Response(
            f"Error: Unable to connect to '{os.getenv('POSTGRES_DB')}' on '{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}'.",
            status=500,
        )


@app.route("/metrics", methods=["GET"])
def metrics():
    registry = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT pg_database_size(%s) as size, (SELECT COUNT(*) FROM pg_stat_activity WHERE datname = %s) as connections",
            (os.getenv("POSTGRES_DB"), os.getenv("POSTGRES_DB")),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        db_connected = True
        db_size = row[0] if row else 0
        db_connections = row[1] if row else 0
    except Exception:
        db_connected = False
        db_size = 0
        db_connections = 0

    registry.append(f"# HELP pypong_database_connected Database connection status")
    registry.append(f"# TYPE pypong_database_connected gauge")
    registry.append(f"pypong_database_connected {1 if db_connected else 0}")
    registry.append(f"# HELP pypong_database_size_bytes Database size in bytes")
    registry.append(f"# TYPE pypong_database_size_bytes gauge")
    registry.append(f"pypong_database_size_bytes {db_size}")
    registry.append(f"# HELP pypong_database_connections Active database connections")
    registry.append(f"# TYPE pypong_database_connections gauge")
    registry.append(f"pypong_database_connections {db_connections}")
    registry.append(f"# HELP pypong_info Python runtime info")
    registry.append(f"# TYPE pypong_info gauge")
    registry.append(f'pypong_info{{framework="flask",version="{_flask_version}"}} 1')

    return Response("\n".join(registry), mimetype="text/plain")


@app.route("/v1", methods=["GET"])
def flask_info():
    return jsonify(
        {
            "framework": "flask",
            "status": "working",
            "version": _flask_version,
            "python_version": os.popen("python --version").read().strip(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
