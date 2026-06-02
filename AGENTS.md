# AGENTS.md — Minimal Viable Docker Development Environment (Python)

## Architecture

- **3 services on bridge network**: nginx (8080), Python (8000 via gunicorn), PostgreSQL (5432)
- nginx → Python via proxy on `127.0.0.1:8000`
- Python → PostgreSQL on `127.0.0.1:5432`

## Developer Commands

```bash
make build              # Build Docker images
make up                 # Start services
make down               # Stop services
make logs [service=python]  # View logs
make shell service=python  # Shell into container (python|db|webserver)
make clean              # Remove containers + volumes
make test               # Run all tests (curl + pytest)
make test:unit          # pytest unit tests only
make test:integration    # pytest integration tests only
make backup             # Backup DB (writes to backup/)
make restore file=<name> # Restore from backup
```

## Testing

- **No Python/pytest on host** — all tools run inside the Python container
- pytest runs via: `docker exec pypong-python-container pytest -v`
- Test files are volume-mounted from `./src/tests` → `/var/www/tests`

## Backup System

- Main script: `backup/backup.sh`
- Configuration: `backup/config.local.sh` (local overrides, **not gitignored**)
- Supports: local, S3, B2, rsync providers
- Optional GPG encryption via `GPG_RECIPIENT` env var
- Local backups auto-pruned after `KEEP_LOCAL_DAYS` (default 7)

## Environment

- `.env` contains `GITHUB_REPOSITORY` and `GITHUB_TOKEN` — credentials, do not commit
- `.env.example` is the template (password: `docker`)
- PostgreSQL defaults: db=`dockerdb`, user=`docker`, password from `.env`, port=`5432`

## Application Stack

- **Flask** web framework (src/app.py)
- **Gunicorn** WSGI server on port 8000
- **psycopg2-binary** for PostgreSQL connectivity
- Endpoints: `/` (status), `/health`, `/database`, `/metrics`, `/flask`