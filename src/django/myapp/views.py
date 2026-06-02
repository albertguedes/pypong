import os
import sys
import json
import uuid
import logging
from datetime import datetime, timezone, timedelta

import django
import jwt
import hashlib
import secrets
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import psycopg2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
JWT_SECRET = os.getenv("JWT_SECRET", os.getenv("POSTGRES_PASSWORD", "dev-secret-change-me"))
JWT_ALG = "HS256"
ACCESS_TOKEN_TTL_MINUTES = 15
REFRESH_TOKEN_TTL_DAYS = 7


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return secrets.compare_digest(hash_password(password), hashed)


USERS_DB = {}


def get_request_id(request):
    return request.META.get("HTTP_X_REQUEST_ID", str(uuid.uuid4()))


def error_response(code, message, details=None, status=400):
    payload = {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        }
    }
    return JsonResponse(payload, status=status)


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def jwt_required(view_func):
    def wrapper(request, *args, **kwargs):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return error_response(
                "UNAUTHORIZED",
                "Missing or invalid Authorization header",
                {},
                401,
            )
        token = auth_header[7:]
        payload = decode_token(token)
        if payload is None:
            return error_response(
                "UNAUTHORIZED",
                "Token is invalid or expired",
                {},
                401,
            )
        if payload.get("type") != "access":
            return error_response(
                "UNAUTHORIZED",
                "Invalid token type",
                {},
                401,
            )
        request.current_user = payload["sub"]
        return view_func(request, *args, **kwargs)
    return wrapper


@csrf_exempt
@require_http_methods(["POST"])
def auth_token(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        body = {}
    username = body.get("username", "").strip()
    password = body.get("password", "")

    if not username or not password:
        return error_response(
            "VALIDATION_ERROR",
            "username and password are required",
            {"fields": ["username", "password"]},
            400,
        )

    user = USERS_DB.get(username)
    if not user or not verify_password(password, user["password_hash"]):
        return error_response(
            "AUTHENTICATION_FAILED",
            "Invalid username or password",
            {},
            401,
        )

    now = datetime.now(timezone.utc)
    access_payload = {
        "sub": username,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES),
        "jti": str(secrets.token_hex(16)),
    }
    refresh_payload = {
        "sub": username,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
        "jti": str(secrets.token_hex(16)),
    }
    return JsonResponse({
        "access_token": jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALG),
        "refresh_token": jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALG),
        "token_type": "Bearer",
        "expires_in": ACCESS_TOKEN_TTL_MINUTES * 60,
    })


@csrf_exempt
@require_http_methods(["POST"])
def auth_register(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        body = {}
    username = body.get("username", "").strip()
    password = body.get("password", "")

    if not username or not password:
        return error_response(
            "VALIDATION_ERROR",
            "username and password are required",
            {"fields": ["username", "password"]},
            400,
        )
    if len(password) < 8:
        return error_response(
            "VALIDATION_ERROR",
            "password must be at least 8 characters",
            {"min_length": 8},
            400,
        )

    if username in USERS_DB:
        return error_response(
            "USER_ALREADY_EXISTS",
            "User already exists",
            {},
            409,
        )

    USERS_DB[username] = {
        "username": username,
        "password_hash": hash_password(password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    return JsonResponse({"message": "User created", "username": username}, status=201)


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "dockerdb"),
        user=os.getenv("POSTGRES_USER", "docker"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
    )


def index(request):
    status = {
        "framework": "django",
        "status": "ok",
        "version": django.get_version(),
        "python_version": sys.version.split()[0],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    html = f"""<!DOCTYPE html>
<html>
<head><title>Django Status</title></head>
<body>
<h1>Django Status</h1>
<ul>
"""
    for key, value in status.items():
        html += f"<li><strong>{key}:</strong> {value}</li>\n"
    html += "</ul>\n</body>\n</html>\n"
    return HttpResponse(html, content_type="text/html")


@require_http_methods(["GET"])
def health(request):
    try:
        conn = get_db_connection()
        conn.info.status
        conn.close()
        return JsonResponse({
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "connected",
        })
    except Exception:
        return error_response(
            "SERVICE_UNAVAILABLE",
            "Database connectivity check failed",
            {},
            503,
        )


@require_http_methods(["GET"])
def database(request):
    try:
        conn = get_db_connection()
        status = conn.info.status
        conn.close()
        return HttpResponse(
            f"Connected to '{os.getenv('POSTGRES_DB')}' on '{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}'.",
            content_type="text/plain",
        )
    except Exception as e:
        return HttpResponse(
            f"Error: Unable to connect to '{os.getenv('POSTGRES_DB')}' on '{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}'.",
            content_type="text/plain",
            status=500,
        )


@require_http_methods(["GET"])
def metrics(request):
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
    registry.append(f'pypong_info{{framework="django",version="{django.get_version()}"}} 1')

    return HttpResponse("\n".join(registry), content_type="text/plain")


def v1_info(request):
    import django as _django
    import sys as _sys
    return JsonResponse({
        "framework": "django",
        "status": "working",
        "version": _django.get_version(),
        "python_version": _sys.version.split()[0],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@require_http_methods(["GET"])
def django_info(request):
    return v1_info(request)


@csrf_exempt
@require_http_methods(["GET"])
@jwt_required
def protected(request):
    return JsonResponse({
        "message": "You have access",
        "user": getattr(request, 'current_user', 'unknown'),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })