# PYPONG - Python + PostgreSQL + Nginx Docker Development Environment

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![GitHub last commit](https://img.shields.io/github/last-commit/albertguedes/pypong)](https://github.com/albertguedes/pypong)
[![CI/CD](https://github.com/albertguedes/pypong/actions/workflows/ci.yml/badge.svg)](https://github.com/albertguedes/pypong/actions/workflows/ci.yml)

A production-ready, lightweight Docker development environment for teams requiring a consistent Python + PostgreSQL stack. Built on Alpine Linux images for minimal footprint and fast deployments.

**Key feature: Host-independent** - Only Docker is required on the host machine. All Python dependencies (Flask, Gunicorn, pytest) are installed inside the containers.

---

## Why This Project?

| Feature | Benefit |
|---------|---------|
| **Host-Independent** | Only Docker needed on host; no Python required |
| **Minimal Footprint** | Alpine-based images (~5MB base) for faster builds |
| **Production-Ready** | Health checks, restart policies, persistent volumes |
| **Environment Isolation** | All credentials via environment variables |
| **Self-Documenting** | Clear service boundaries and architecture docs |
| **Enterprise Secure** | Ports bound to localhost, host networking, no secrets |
| **CI/CD Ready** | GitHub Actions workflows for testing and release |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    HOST MACHINE                          │
│                  (127.0.0.1:8080)                        │
└─────────────────────────┬───────────────────────────────┘
                          │
         ┌────────────────┴────────────────┐
         │                                 │
         ▼                                 ▼
┌─────────────────────┐         ┌─────────────────────┐
│ pypong-nginx       │         │ pypong-python      │
│ (nginx:1.27-alpine) │         │ (python:3.13)       │
│                     │────────▶│                     │
│ :8080 (HTTP)        │         │ :8000 (gunicorn)    │
│ /var/www/html       │         │ /var/www            │
└─────────────────────┘         └─────────┬───────────┘
                                          │
                                          ▼
                              ┌─────────────────────┐
                              │ pypong-postgresql  │
                              │ (postgres:17)       │
                              │ :5432               │
                              │ pypong-data (vol)  │
                              └─────────────────────┘
```

All services use **host networking** for direct communication via `127.0.0.1`.

## Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| **webserver** | nginx:1.27-alpine | 8080 | HTTP server, Python proxy |
| **python** | python:3.13-alpine | 8000 | Flask/Gunicorn application |
| **db** | postgres:17-alpine | 5432 | PostgreSQL database |

---

## Quick Start

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- GNU Make 3.81+

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/albertguedes/pypong.git
cd pypong

# 2. Configure environment
cp .env.example .env

# 3. Build and start services
make build && make up

# 4. Verify services
make test
```

### Verify Your Setup

```bash
# Test HTTP server
curl http://localhost:8080/

# Test Python endpoints
curl http://localhost:8080/health
curl http://localhost:8080/database
curl http://localhost:8080/metrics

# Run all tests (curl + pytest)
make test

# Run unit tests only
make test:unit

# Run integration tests only
make test:integration

# View running containers
make logs

# Shell into Python container
make shell service=python
```

---

## Developer Commands

| Command | Description |
|---------|-------------|
| `make up` | Start all containers in detached mode |
| `make down` | Stop all containers |
| `make build` | Rebuild Docker images |
| `make logs [service=<name>]` | View logs (all or specific service) |
| `make shell service=<db\|python\|webserver>` | Exec into container shell |
| `make clean` | Remove containers and volumes |
| `make status` | Show running containers status |
| `make test` | Run all tests (curl + pytest) |
| `make test:unit` | pytest unit tests only |
| `make test:integration` | pytest integration tests only |
| `make backup` | Backup database |
| `make restore file=<backup>` | Restore database from backup |

---

## Testing

Tests run inside the Python container - no Python/pytest needed on host.

```bash
# Run all tests
make test

# Run unit tests only
make test:unit

# Run integration tests only
make test:integration
```

### Test Suites

| Suite | Purpose | Location |
|-------|---------|----------|
| **Unit** | Python logic tests | `src/tests/Unit/` |
| **Integration** | HTTP endpoints + DB tests | `src/tests/Integration/` |

---

## Environment Variables

Configure your environment by editing the `.env` file:

```env
# PostgreSQL Configuration
POSTGRES_DB=dockerdb
POSTGRES_USER=docker
POSTGRES_PASSWORD=your_secure_password
POSTGRES_PORT=5432
```

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | dockerdb | Name of the database |
| `POSTGRES_USER` | docker | Database user |
| `POSTGRES_PASSWORD` | - | Database password (required) |
| `POSTGRES_PORT` | 5432 | Database port |

---

## Project Structure

```
.
├── src/                    # Application source (volume-mounted)
│   ├── app.py             # Flask application
│   ├── requirements.txt   # Python dependencies
│   ├── index.html         # Static HTML page
│   └── tests/             # Test suite
│       └── test_app.py
├── python/                 # Python service
│   └── Dockerfile         # Python image definition
├── database/               # Database service
│   └── Dockerfile
├── webserver/              # Web server service
│   ├── Dockerfile
│   └── nginx/
│       ├── default.conf   # Nginx configuration
│       └── nginx.conf     # Main config
├── backup/                 # Backup scripts
│   ├── backup.sh           # Backup with encryption/sync
│   ├── restore.sh          # Restore script
│   ├── verify-restore.sh   # Backup verification
│   └── config.sh          # Backup configuration
├── compose.yaml           # Service definitions
├── Makefile               # Developer commands
└── docs/                  # Documentation
    ├── ARCHITECTURE.md
    ├── CHANGELOG.md
    ├── CONTRIBUTING.md
    └── USER_MANUAL.md
```

---

## CI/CD

### GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **CI** | push to master, PR | Test → Trivy scan → Build images |
| **CD** | annotated tag `v*` | Build + push images to GHCR |

### Docker Images

Images are published to **GitHub Container Registry (GHCR)**:

```bash
# Example: Pull tagged release
docker pull ghcr.io/albertguedes/pypong/python:v0.10.1
docker pull ghcr.io/albertguedes/pypong/webserver:v0.10.1
docker pull ghcr.io/albertguedes/pypong/db:v0.10.1
```

---

## Troubleshooting

### Services won't start

```bash
# Check Docker is running
docker info

# View container logs
make logs

# Verify .env file exists
cat .env
```

### Database connection fails

```bash
# Wait for DB to be ready
pg_isready -h 127.0.0.1 -p 5432 -U docker

# Shell into Python container
make shell service=python
```

### Port already in use

```bash
# Find what's using port 8080
lsof -i :8080
```

---

## Backup & Restore

### Configuration

Edit `backup/config.local.sh` to configure your backup destination:

```bash
# Choose provider: local, s3, b2, rsync
BACKUP_PROVIDER=local

# Optional GPG encryption
# GPG_RECIPIENT="your@email.com"

# S3 Configuration (if BACKUP_PROVIDER=s3)
# S3_BUCKET="your-bucket"
# S3_REGION="us-east-1"

# Backblaze B2 (if BACKUP_PROVIDER=b2)
# B2_ACCOUNT_ID=""
# B2_APPLICATION_KEY=""
# B2_BUCKET=""
```

### Commands

```bash
# Backup database (local)
make backup

# Verify backup integrity
bash backup/verify-restore.sh

# Restore from backup
make restore file=backup/postgresql_20260522_120000.sql.gz
```

---

## Security Notes

- Ports are bound to `127.0.0.1` (localhost only) by default
- All credentials managed via environment variables
- No secrets committed to version control
- Host networking mode for inter-container communication
- CI/CD includes Trivy vulnerability scanning
- Backups can be encrypted with GPG

**For production deployments**, consider:

- Implementing Docker Secrets
- Configuring SSL/TLS termination
- Adding a reverse proxy with automatic certificate management
- Enabling audit logging
- Setting resource limits and quotas

---

## Contributing

Contributions are welcome. Please see [CONTRIBUTING.md](./docs/CONTRIBUTING.md) for guidelines.

---

## License

This project is distributed under the [MIT License](./LICENSE). See [LICENSE](./LICENSE) for more information.