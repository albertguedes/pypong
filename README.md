# PYPONG — Multi-Framework Production-Ready Docker Stack

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![GitHub last commit](https://img.shields.io/github/last-commit/albertguedes/pypong)](https://github.com/albertguedes/pypong)
[![CI/CD](https://github.com/albertguedes/pypong/actions/workflows/ci.yml/badge.svg)](https://github.com/albertguedes/pypong/actions/workflows/ci.yml)

**PYPONG** is a production-oriented Docker development environment for Python teams. Three web frameworks — Flask, Django, and FastAPI — run simultaneously behind nginx, sharing a PostgreSQL database. Includes JWT authentication, Prometheus metrics, structured JSON logging, CORS, rate limiting, Sentry error tracking, and automated backups.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       HOST MACHINE  (127.0.0.1:8080)                    │
│                     nginx reverse proxy / load balancer                   │
└──────────────────────────────────┬────────────────────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
         ▼                         ▼                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Flask (8000)   │     │  Django (8001)  │     │  FastAPI (8002) │
│  JWT API /v1/*  │     │  dashboard only │     │  dashboard only │
│  Gunicorn ts4   │     │  Gunicorn ts4   │     │  Uvicorn        │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │     PostgreSQL 17       │
                    │    (bridge network)     │
                    │    pypong-data (vol)    │
                    └─────────────────────────┘
```

**5 services | 3 frameworks | 1 PostgreSQL | JWT auth | Prometheus metrics | Sentry | CORS | Rate limiting**

---

## Features

| Category | Implementation |
|----------|---------------|
| **Authentication** | JWT Bearer tokens (PyJWT, HS256, 15min access / 7d refresh) |
| **Password hashing** | SHA-256 with constant-time comparison |
| **Error format** | Identical `{"error": {code, message, details}}` across all frameworks |
| **Rate limiting** | nginx `limit_req`: 10r/s burst 20 for auth, 100r/s burst 200 for API |
| **Observability** | Structured JSON logs, Prometheus `/metrics`, `X-Request-ID` propagation |
| **Error tracking** | Sentry SDK with Flask/FastAPI/Django integrations |
| **Health checks** | `/health` verifies PostgreSQL connectivity, returns 503 if DB is down |
| **API versioning** | `/v1/` prefix for all API routes. Dashboard routes unchanged. |
| **CORS** | Configurable allowed origins via nginx `$cors_origin` map |
| **Tracing** | Request ID injection nginx → framework → PostgreSQL |
| **Backup** | `pg_dump` + gzip, optional GPG encryption, local/S3/B2/rsync providers |
| **Security** | Non-root user (`appuser`), read-only volume mounts, gitignored `.env` |

---

## Quick Start

```bash
# 1. Clone and enter
git clone https://github.com/albertguedes/pypong.git
cd pypong

# 2. Configure environment
cp .env.example .env

# 3. Build and start
make build && make up

# 4. Verify
make test
```

---

## API Reference

All frameworks expose the same API at their `/v1/` endpoint.

### Flask (Base: `http://localhost:8080/flask/v1`)

### Django (Base: `http://localhost:8080/django/v1`)

### FastAPI (Base: `http://localhost:8080/fastapi/v1`)

### Authentication

All three frameworks share identical auth endpoint behavior:

#### Register
```bash
# Flask
curl -X POST http://localhost:8080/flask/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"dev","password":"password123"}'

# Django
curl -X POST http://localhost:8080/django/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"dev","password":"password123"}'

# FastAPI
curl -X POST http://localhost:8080/fastapi/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"dev","password":"password123"}'
```

#### Login
```bash
# Flask
curl -X POST http://localhost:8080/flask/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"dev","password":"password123"}'
# Returns: {access_token, refresh_token, token_type, expires_in}
```

#### Protected Resource
```bash
curl -H "Authorization: Bearer <access_token>" \
  http://localhost:8080/flask/v1/protected
```

### Framework Dashboard Endpoints

| Framework | Base Path | Endpoints |
|-----------|-----------|-----------|
| Flask | `/flask` | `/flask/` `/flask/health` `/flask/database` `/flask/metrics` `/flask/v1` |
| Django | `/django` | `/django/` `/django/health` `/django/database` `/django/metrics` `/django/v1` |
| FastAPI | `/fastapi` | `/fastapi/` `/fastapi/health` `/fastapi/database` `/fastapi/metrics` `/fastapi/v1` |

### Metrics (Prometheus format)
```bash
curl http://localhost:8080/flask/metrics
# pypong_database_connected, pypong_database_size_bytes, pypong_info{framework="flask"}
```

---

## Developer Commands

| Command | Description |
|---------|-------------|
| `make build` | Build all Docker images |
| `make up` | Start all containers |
| `make down` | Stop all containers |
| `make clean` | Remove containers and volumes |
| `make test` | Run all tests (curl + pytest, all frameworks) |
| `make test-flask` | Flask pytest only |
| `make test-django` | Django pytest only |
| `make test-fastapi` | FastAPI pytest only |
| `make backup` | Backup database |
| `make restore file=<name>` | Restore from backup |
| `make shell service=<name>` | Shell into container (flask\|django\|fastapi\|db\|webserver) |
| `make logs [service=<name>]` | View container logs |

---

## Environment Variables

```env
# PostgreSQL
POSTGRES_DB=dockerdb
POSTGRES_USER=docker
POSTGRES_PASSWORD=docker
POSTGRES_PORT=5432

# JWT Authentication (required for production)
JWT_SECRET=<openssl-rand-hex-32>

# Optional / Recommended
SENTRY_DSN=https://<key>@o<org>.ingest.sentry.io/<project>
ENVIRONMENT=production
```

---

## Documentation

| Document | Contents |
|----------|----------|
| [ARCHITECTURE.md](./docs/ARCHITECTURE.md) | System architecture, networking, data flow |
| [openapi.yaml](./docs/openapi.yaml) | OpenAPI 3.0 specification for v1 API |
| [DEPLOY.md](./docs/DEPLOY.md) | Production deployment steps, TLS, Docker Swarm |
| [SECURITY.md](./docs/SECURITY.md) | Security policy, responsible disclosure, hardening checklist |
| [ADR-001-jwt.md](./docs/ADR-001-jwt.md) | Auth architecture decision record |
| [ADR-002-security.md](./docs/ADR-002-security.md) | Infrastructure security defaults |
| [ADR-003-multi-framework.md](./docs/ADR-003-multi-framework.md) | Multi-framework routing decisions |

---

## Backup System

```bash
# Configure backup provider
cp backup/config.sh backup/config.local.sh
# Edit: BACKUP_PROVIDER=(local|s3|b2|rsync)

# Backup now
make backup

# Restore
make restore file=backup/postgresql_20260602_120000.sql.gz
```

---

## CI/CD

Images published to **GitHub Container Registry (GHCR)**:

```bash
docker pull ghcr.io/albertguedes/pypong/flask:v0.10.1
docker pull ghcr.io/albertguedes/pypong/webserver:v0.10.1
docker pull ghcr.io/albertguedes/pypong/db:v0.10.1
```

Workflows:
- **CI** — on push/PR: lint, pytest inside containers, Trivy scan, Docker build
- **CD** — on annotated tag `v*`: build + push to GHCR

---

## Project Structure

```
pypong/
├── src/
│   ├── flask/
│   │   ├── app.py                # Flask + JWT API
│   │   ├── requirements.txt
│   │   ├── shared/                # auth.py, errors.py, tracing.py
│   │   └── tests/
│   ├── django/
│   │   ├── myapp/views.py        # Django endpoints
│   │   └── myproject/            # Django settings + urls
│   ├── fastapi/
│   │   └── main.py              # FastAPI endpoints
│   └── index.html               # Dashboard UI
├── webserver/nginx/            # nginx config (CORS, rate limit, proxy)
├── database/                   # PostgreSQL Dockerfile
├── python/                     # Shared Python Dockerfile (gunicorn)
├── backup/                     # pg_dump + encrypt + sync scripts
├── docs/                       # openapi.yaml, ADRs, DEPLOY, SECURITY
├── compose.yaml               # 5-service orchestration
├── Makefile                   # Developer commands
└── .env.example               # Environment template
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| WSGI Server | Gunicorn `--threads 4` (Flask/Django) |
| ASGI Server | Uvicorn (FastAPI) |
| Database | PostgreSQL 17 (Alpine) |
| Reverse Proxy | nginx 1.27 (Alpine) |
| Auth | PyJWT (HS256, SHA-256) |
| Metrics | Prometheus text format |
| Error tracking | Sentry SDK |
| Image base | Alpine Linux 3.19+ |
| Container user | `appuser` (uid 1000, non-root) |

---

## Contributing

See [CONTRIBUTING.md](./docs/CONTRIBUTING.md) for guidelines.

---

## License

MIT. See [LICENSE](./LICENSE).
