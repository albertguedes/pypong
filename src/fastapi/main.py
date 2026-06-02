import os
import sys
import json
import uuid
from datetime import datetime, timezone, timedelta
from functools import wraps

import hashlib
import secrets
import jwt
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from fastapi import FastAPI, Request, Header, Depends
from fastapi.responses import PlainTextResponse, JSONResponse
import psycopg2
import psycopg2.extras

sentry_sdk.init(
    integrations=[FastApiIntegration()],
    dsn=os.getenv("SENTRY_DSN", ""),
    environment=os.getenv("ENVIRONMENT", "development"),
    traces_sample_rate=float(os.getenv("OTEL_SAMPLE_RATE", "0.0")),
    send_default_pii=False,
)

app = FastAPI(title="PYPONG FastAPI", version="1.0.0")

JWT_SECRET = os.getenv("JWT_SECRET", os.getenv("POSTGRES_PASSWORD", "dev-secret-change-me"))
JWT_ALG = "HS256"
ACCESS_TOKEN_TTL_MINUTES = 15
REFRESH_TOKEN_TTL_DAYS = 7


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return secrets.compare_digest(hash_password(password), hashed)


USERS_DB = {}


def get_request_id(request: Request) -> str:
    return request.headers.get("x-request-id", str(uuid.uuid4()))


def error_response(code: str, message: str, details: dict = None, status: int = 400):
    return JSONResponse(
        {
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            }
        },
        status_code=status,
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    body = None
    try:
        body = await request.body()
        if body:
            body = json.loads(body)
    except Exception:
        pass

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/", response_class=PlainTextResponse)
async def index():
    return "FastAPI is running"


@app.get("/health", response_class=JSONResponse)
async def health():
    try:
        conn = get_db_connection()
        conn.info.status
        conn.close()
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "connected",
        }
    except Exception:
        return error_response(
            "SERVICE_UNAVAILABLE",
            "Database connectivity check failed",
            {},
            503,
        )


@app.post("/v1/auth/token", response_class=JSONResponse)
async def auth_token(request: Request):
    body = await request.json() if request.body else {}
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
    return JSONResponse({
        "access_token": jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALG),
        "refresh_token": jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALG),
        "token_type": "Bearer",
        "expires_in": ACCESS_TOKEN_TTL_MINUTES * 60,
    })


@app.post("/v1/auth/register", response_class=JSONResponse)
async def auth_register(request: Request):
    try:
        body = await request.json()
    except Exception:
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

    return JSONResponse({"message": "User created", "username": username}, status_code=201)


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "dockerdb"),
        user=os.getenv("POSTGRES_USER", "docker"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
    )


@app.get("/database", response_class=PlainTextResponse)
async def database():
    try:
        conn = get_db_connection()
        status = conn.info.status
        conn.close()
        return f"Connected to '{os.getenv('POSTGRES_DB')}' on '{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}'."
    except Exception:
        return PlainTextResponse(
            f"Error: Unable to connect to '{os.getenv('POSTGRES_DB')}' on '{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}'.",
            status_code=500,
        )


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
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
    registry.append(f'pypong_info{{framework="fastapi",version="{__import__("fastapi").__version__}"}} 1')

    return PlainTextResponse("\n".join(registry), media_type="text/plain")


@app.get("/v1", response_class=JSONResponse)
async def fastapi_info():
    import sys
    return {
        "framework": "fastapi",
        "status": "working",
        "version": __import__("fastapi").__version__,
        "python_version": sys.version.split()[0],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_current_user(authorization: str = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise error_response(
            "UNAUTHORIZED",
            "Missing or invalid Authorization header",
            {},
            401,
        )
    token = authorization[7:]
    payload = decode_token(token)
    if payload is None:
        raise error_response(
            "UNAUTHORIZED",
            "Token is invalid or expired",
            {},
            401,
        )
    if payload.get("type") != "access":
        raise error_response(
            "UNAUTHORIZED",
            "Invalid token type",
            {},
            401,
        )
    return payload["sub"]


@app.get("/v1/protected", response_class=JSONResponse)
async def protected(current_user: str = Depends(get_current_user)):
    return {
        "message": "You have access",
        "user": current_user,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
