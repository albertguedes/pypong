import os
import jwt
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import request, g, jsonify

JWT_SECRET = os.getenv("JWT_SECRET", os.getenv("POSTGRES_PASSWORD", "dev-secret-change-me"))
JWT_ALG = "HS256"
ACCESS_TOKEN_TTL_MINUTES = 15
REFRESH_TOKEN_TTL_DAYS = 7


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return secrets.compare_digest(hash_password(password), hashed)


USERS_DB = {}


def create_user(username: str, password: str) -> dict:
    if username in USERS_DB:
        raise ValueError("USER_ALREADY_EXISTS")
    USERS_DB[username] = {
        "username": username,
        "password_hash": hash_password(password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return {"username": username}


def authenticate(username: str, password: str) -> dict | None:
    user = USERS_DB.get(username)
    if not user or not verify_password(password, user["password_hash"]):
        return None
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
    return {
        "access_token": jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALG),
        "refresh_token": jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALG),
        "token_type": "Bearer",
        "expires_in": ACCESS_TOKEN_TTL_MINUTES * 60,
    }


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": {"code": "UNAUTHORIZED", "message": "Missing or invalid Authorization header", "details": {}}}), 401
        token = auth_header[7:]
        payload = decode_token(token)
        if payload is None:
            return jsonify({"error": {"code": "UNAUTHORIZED", "message": "Token is invalid or expired", "details": {}}}), 401
        if payload.get("type") != "access":
            return jsonify({"error": {"code": "UNAUTHORIZED", "message": "Invalid token type", "details": {}}}), 401
        g.current_user = payload["sub"]
        return f(*args, **kwargs)
    return decorated
