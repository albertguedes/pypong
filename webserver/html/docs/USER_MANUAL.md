# User Manual

## Quick Start

```bash
# 1. Clone and enter directory
git clone https://github.com/albertguedes/pypong.git
cd pypong

# 2. Configure environment
cp .env.example .env
# Edit .env with your database credentials

# 3. Build and start
make build && make up

# 4. Verify
curl http://localhost:8080/
```

## Services

| Service | Port (host) | Container | Description |
|---------|-------------|-----------|-------------|
| nginx | 8080 (127.0.0.1) | pypong-nginx-container | HTTP server + static files |
| python | internal:8000 | pypong-python-container | Flask/Gunicorn application |
| postgresql | mapped (random) | pypong-postgresql-container | PostgreSQL 17 database |

## Common Commands

```bash
make up              # Start containers
make down            # Stop containers
make build           # Rebuild images
make logs            # View all logs
make logs service=python  # View Python logs
make shell service=python # Shell into Python container
make clean           # Remove containers and volumes
make test            # Run all tests (curl + pytest)
make test:unit       # pytest unit tests only
make test:integration # pytest integration tests only
make backup          # Backup database
make restore file=<name> # Restore from backup
```

## Endpoints

| URL | Method | Description | Response |
|-----|--------|-------------|----------|
| http://localhost:8080/ | GET | System Status Dashboard | HTML page |
| http://localhost:8080/health | GET | Health Check | `OK` |
| http://localhost:8080/database | GET | Database Connection Status | Text |
| http://localhost:8080/metrics | GET | System Metrics | JSON |
| http://localhost:8080/flask | GET | Flask Application Status | JSON |

### Example Responses

**GET /health**
```
OK
```

**GET /database**
```
Connected to 'dockerdb' on 'pypong-postgresql-container:5432'.
```

**GET /metrics**
```json
{
  "status": "ok",
  "timestamp": "2026-06-02T20:43:52.183545+00:00",
  "database": {
    "connected": true,
    "size_bytes": 7689907,
    "size_human": "7.33 MB",
    "connections": 1
  }
}
```

**GET /flask**
```json
{
  "flask": "working",
  "version": "3.1.3",
  "python_version": "Python 3.13.13",
  "timestamp": "2026-06-02T20:43:52.221493+00:00"
}
```

## Troubleshooting

**Services won't start:**
```bash
docker compose ps
make logs
cat .env
```

**Database connection fails:**
```bash
docker exec pypong-postgresql-container pg_isready -U docker -d dockerdb
make shell service=python
```

**Port already in use:**
```bash
ss -tlnp | grep 8080
```

**Rebuild from scratch:**
```bash
make clean && make build && make up
```