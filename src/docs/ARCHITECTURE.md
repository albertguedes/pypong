# Architecture

Technical documentation for the Minimal Viable Docker Development Environment (Python stack).

---

## Overview

Three services run on a bridge network: **nginx** (HTTP), **Python/Flask** (application runtime via Gunicorn), and **PostgreSQL** (data). Nginx serves static files and proxies dynamic requests to Python on `127.0.0.1:8000`. Python connects to PostgreSQL on `127.0.0.1:5432` through the bridge network.

Only **Docker** and **Make** are required on the host; Python and pytest run inside the Python image.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         HOST MACHINE                            │
│                                                                 │
│   localhost:8080  ── nginx (pypong-nginx-container)            │
│                         │ proxy_pass 127.0.0.1:8000             │
│                         ▼                                       │
│   container:8000    ── Python/Gunicorn (pypong-python-container)│
│                         │ psycopg2 172.x.x.x:5432                │
│                         ▼                                       │
│   localhost:5432    ── PostgreSQL (pypong-postgresql-container)  │
│                        (exposed via bridge)                     │
│                                                                 │
│   ./src ──────────────────────▶ /var/www/html (ro)              │
└─────────────────────────────────────────────────────────────────┘
```

All services use **`bridge` network** with explicit port publishing. Services bind on `127.0.0.1` to avoid external exposure.

---

## Services

### 1. Web Server (nginx)

| Property | Value |
|----------|-------|
| Image | nginx:1.27-alpine |
| Container | pypong-nginx-container |
| Listen | `127.0.0.1:8080` (configured in `webserver/nginx/default.conf`) |
| Config | `webserver/nginx/default.conf`, `webserver/nginx/nginx.conf` |
| Dockerfile | `webserver/Dockerfile` |

**Responsibilities:**

- Serve static files from `/var/www/html` (volume: `./src`, read-only)
- Proxy `/health`, `/database`, `/metrics`, `/flask` to Python container
- Inline `/` static index page (no Python needed)

**Request flow:**

```
Client → :8080 → nginx
                 ├── / → /var/www/html/index.html (static)
                 └── /health|/database|/metrics|/flask → :8000 → Python/Gunicorn
```

### 2. Python Application (Flask/Gunicorn)

| Property | Value |
|----------|-------|
| Image | python:3.13-alpine |
| Container | pypong-python-container |
| Listen | `0.0.0.0:8000` (Gunicorn, bound to container) |
| Dockerfile | `python/Dockerfile` (build context: `./src/`) |
| User | appuser (uid 1000) |
| Dependencies | flask>=3.0.0, gunicorn>=23.0.0, psycopg2-binary>=2.9.0 |

**Volumes:**

- `./src` → `/var/www` (app code + tests)

**Environment (compose + `.env`):**

| Variable | Default in compose | Description |
|----------|-------------------|-------------|
| POSTGRES_HOST | `pypong-postgresql-container` | Database host (bridge DNS) |
| POSTGRES_PORT | `5432` | Database port |
| POSTGRES_DB | from `.env` | Database name |
| POSTGRES_USER | from `.env` | Database user |
| POSTGRES_PASSWORD | from `.env` | Database password |

### 3. Database (PostgreSQL)

| Property | Value |
|----------|-------|
| Image | postgres:17-alpine |
| Container | pypong-postgresql-container |
| Listen | `5432` (container), mapped to random host port |
| Dockerfile | `database/Dockerfile` |
| Data | Docker volume `pypong-data` → `/var/lib/postgresql/data` |

**Defaults:** database `dockerdb`, user `docker`, password from `.env`.

---

## Network Architecture

### Bridge networking

```yaml
networks:
  - pypong-network:  # bridge driver
```

Inter-service traffic uses **bridge network DNS**:

| From | To | Address |
|------|-----|---------|
| Browser | nginx | `http://127.0.0.1:8080` |
| nginx | Python | `http://pypong-python-container:8000` |
| Python | PostgreSQL | `pypong-postgresql-container:5432` |
| Host tools | PostgreSQL | Use `docker compose port db 5432` to get mapped port |

**Note:** `depends_on` orders container start but does **not** wait for PostgreSQL readiness; use `make test` or `pg_isready` manually.

---

## Data Flow

### Static content

```
Browser → http://127.0.0.1:8080/index.html
       → nginx → /var/www/html/index.html
```

### Dynamic endpoints (Python)

```
Browser → http://127.0.0.1:8080/health
       → nginx → proxy_pass pypong-python-container:8000
       → Flask/Gunicorn handles request
```

### Database (via Python/psycopg2)

```
Browser → http://127.0.0.1:8080/database
       → Python → psycopg2.connect(host=pypong-postgresql-container, ...)
       → PostgreSQL
```

---

## Operational Checks

| Check | Command |
|-------|---------|
| HTTP | `curl -sf http://127.0.0.1:8080/health` |
| DB ready | `docker exec pypong-postgresql-container pg_isready -U docker -d dockerdb` |
| Python ready | `curl -sf http://127.0.0.1:8080/flask` |
| Full suite | `make test` |

---

## Security Architecture

- Credentials in `.env` (gitignored), passed via `env_file`
- Services listen on `127.0.0.1` (not exposed on all interfaces)
- Python image runs as non-root user `appuser`
- nginx mounts `src` read-only
- No external ports exposed (port publishing is random for DB)

**Production hardening (not included):** TLS termination, Docker Secrets, compose healthchecks.

---

## Build Context

| Service | Context | Dockerfile |
|---------|---------|------------|
| database | `./database/` | `Dockerfile` |
| python | `./src/` | `../python/Dockerfile` |
| webserver | `./webserver/` | `Dockerfile` |

---

## CI/CD

| Workflow | Trigger | Notes |
|----------|---------|-------|
| `ci.yml` | push/PR to `master` | Docker build, pytest inside container |

---

## Future Considerations

- Compose healthchecks with `depends_on: condition: service_healthy`
- TLS reverse proxy, Redis sessions, read replicas
- S3/B2 backup integration