# Architecture

Technical documentation for the Multi-Framework Python Docker Development Stack.

---

## Overview

**PYPONG** is a multi-framework Docker environment with three Python web frameworks (Flask, Django, FastAPI) running behind a single nginx reverse proxy. All frameworks share the same PostgreSQL database and expose identical `/v1/auth/*` JWT authentication endpoints.

**Architecture:** nginx (8080) → Flask (8000) / Django (8001) / FastAPI (8002) → PostgreSQL (5432)

Only **Docker** and **Make** are required on the host. Python and pytest run inside containers.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         HOST MACHINE  (127.0.0.1:8080)                  │
│                     nginx reverse proxy / load balancer                 │
└──────────────────────────────────┬────────────────────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
         ▼                         ▼                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Flask (8000)   │     │  Django (8001)  │     │  FastAPI (8002) │
│  /flask/*       │     │  /django/*      │     │  /fastapi/*     │
│  Gunicorn ts4   │     │  Gunicorn ts4   │     │  Uvicorn        │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │     PostgreSQL 17         │
                    │    (bridge network)      │
                    │    pypong-data (vol)     │
                    └─────────────────────────┘
```

---

## Services

### 1. Web Server (nginx)

| Property | Value |
|----------|-------|
| Image | nginx:1.27-alpine |
| Container | pypong-nginx-container |
| Listen | `127.0.0.1:8080` |
| Config | `webserver/nginx/default.conf`, `webserver/nginx/nginx.conf` |
| Static | `/usr/share/nginx/html/` (index.html + docs/) |

**nginx Responsibilities:**

- Entry point for all HTTP traffic
- Route `/flask/*` → Flask container (8000)
- Route `/django/*` → Django container (8001)
- Route `/fastapi/*` → FastAPI container (8002)
- Serve `/docs/` with autoindex (markdown files)
- Rate limiting (auth: 10r/s, API: 100r/s)
- CORS headers on `/v1/` routes
- Request ID propagation

**Request flow:**

```
Client → :8080 → nginx
         ├── / → /var/www/html/index.html (static homepage)
         ├── /docs/* → /var/www/html/docs/* (autoindex)
         ├── /flask/* → pypong-flask-container:8000
         ├── /django/* → pypong-django-container:8001
         └── /fastapi/* → pypong-fastapi-container:8002
```

### 2. Flask Application

| Property | Value |
|----------|-------|
| Image | flask-image (python:3.13-alpine) |
| Container | pypong-flask-container |
| Listen | `0.0.0.0:8000` (Gunicorn `--threads 4`) |
| Dockerfile | `python/flask.Dockerfile` |
| User | appuser (uid 1000) |
| Dependencies | flask>=3.0.0, gunicorn>=23.0.0, psycopg2-binary>=2.9.0, PyJWT, sentry-sdk |

**Flask Endpoints:**

| Path | Description |
|------|-------------|
| `/flask/` | Status page |
| `/flask/health` | DB connectivity check |
| `/flask/database` | DB connection test |
| `/flask/metrics` | Prometheus metrics |
| `/flask/v1` | API info |
| `/flask/v1/auth/register` | User registration (POST) |
| `/flask/v1/auth/token` | JWT token generation (POST) |
| `/flask/v1/protected` | JWT-protected endpoint (GET) |

### 3. Django Application

| Property | Value |
|----------|-------|
| Image | django-image (python:3.13-alpine) |
| Container | pypong-django-container |
| Listen | `0.0.0.0:8001` (Gunicorn `--threads 4`) |
| Dockerfile | `python/django.Dockerfile` |
| User | appuser (uid 1000) |
| Dependencies | django>=5.0.0, gunicorn>=23.0.0, psycopg2-binary>=2.9.0, PyJWT, sentry-sdk |

**Django Endpoints:** Same as Flask (with `/django/` prefix)

### 4. FastAPI Application

| Property | Value |
|----------|-------|
| Image | fastapi-image (python:3.13-alpine) |
| Container | pypong-fastapi-container |
| Listen | `0.0.0.0:8002` (Uvicorn) |
| Dockerfile | `python/fastapi.Dockerfile` |
| User | appuser (uid 1000) |
| Dependencies | fastapi>=0.100.0, uvicorn[standard], psycopg2-binary>=2.9.0, PyJWT, sentry-sdk |

**FastAPI Endpoints:** Same as Flask (with `/fastapi/` prefix)

### 5. Database (PostgreSQL)

| Property | Value |
|----------|-------|
| Image | postgres:17-alpine |
| Container | pypong-postgresql-container |
| Listen | `5432` (container) |
| Data | Docker volume `pypong-data` → `/var/lib/postgresql/data` |
| Defaults | db: `dockerdb`, user: `docker`, password: from `.env` |

---

## Network Architecture

### Bridge networking

All services use **`pypong-network`** bridge driver with DNS resolution:

| From | To | Address |
|------|-----|---------|
| Browser | nginx | `http://127.0.0.1:8080` |
| nginx | Flask | `http://pypong-flask-container:8000` |
| nginx | Django | `http://pypong-django-container:8001` |
| nginx | FastAPI | `http://pypong-fastapi-container:8002` |
| Flask/Django/FastAPI | PostgreSQL | `pypong-postgresql-container:5432` |

---

## Authentication

All three frameworks share identical JWT authentication:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/flask/v1/auth/register` | POST | Create user (username, password min 8 chars) |
| `/flask/v1/auth/token` | POST | Get access + refresh tokens |
| `/flask/v1/protected` | GET | Protected resource (requires Bearer token) |

JWT config: HS256, access token 15min TTL, refresh token 7 days.

---

## Rate Limiting (nginx)

| Zone | Limit | Burst |
|------|-------|-------|
| `auth_limit` | 10r/s | 20 |
| `api_limit` | 100r/s | 200 |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| POSTGRES_HOST | `pypong-postgresql-container` | Database host |
| POSTGRES_PORT | `5432` | Database port |
| POSTGRES_DB | `dockerdb` | Database name |
| POSTGRES_USER | `docker` | Database user |
| POSTGRES_PASSWORD | from `.env` | Database password |
| JWT_SECRET | from `.env` | JWT signing key |

---

## Operational Checks

| Check | Command |
|-------|---------|
| HTTP | `curl -sf http://127.0.0.1:8080/` |
| Flask | `curl -sf http://127.0.0.1:8080/flask/health` |
| Django | `curl -sf http://127.0.0.1:8080/django/health` |
| FastAPI | `curl -sf http://127.0.0.1:8080/fastapi/health` |
| DB ready | `docker exec pypong-postgresql-container pg_isready -U docker -d dockerdb` |
| Full suite | `make test` |

---

## Security

- Credentials in `.env` (gitignored), passed via `env_file`
- Services listen on `127.0.0.1` (not exposed externally)
- Python images run as non-root user `appuser`
- nginx mounts `webserver/html/` read-only
- Non-root containers throughout

---

## Build Context

| Service | Context | Dockerfile |
|---------|---------|------------|
| webserver | `./webserver/` | `Dockerfile` |
| flask | `./src/flask/` | `../python/flask.Dockerfile` |
| django | `./src/django/` | `../python/django.Dockerfile` |
| fastapi | `./src/fastapi/` | `../python/fastapi.Dockerfile` |
| database | `./database/` | `Dockerfile` |

---

## Future Considerations

- Compose healthchecks with `depends_on: condition: service_healthy`
- Redis for sessions/caching
- TLS termination at nginx
- Docker Secrets for production
- Read replicas for PostgreSQL