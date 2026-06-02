# Deployment Guide

This guide covers deploying **PYPONG** to production or production-like environments.

---

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+ (or Docker Swarm)
- Minimum 1GB RAM, 2 vCPUs
- Ubuntu 22.04+ / Debian 12+ (or equivalent Linux)

---

## Environments

### Development
```bash
cp .env.example .env
# Edit .env with your values
make build && make up
```

### Staging / Production
All configuration via environment variables; no code changes required between environments.

---

## Production Deployment Steps

### 1. Server Setup

```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Add current user to docker group
usermod -aG docker $USER

# Install docker-compose
apt install docker-compose -y
```

### 2. Environment Configuration

```bash
# Generate strong JWT secret
openssl rand -hex 32
```

Create `.env.production`:
```env
# PostgreSQL
POSTGRES_DB=pypong
POSTGRES_USER=pypong_app
POSTGRES_PASSWORD=<use-openssl-rand-hex-32>
POSTGRES_PORT=5432

# JWT Authentication
JWT_SECRET=<use-openssl-rand-hex-32>

# Sentry Error Tracking (optional)
SENTRY_DSN=https://<key>@o<org>.ingest.sentry.io/<project>

# Environment flag
ENVIRONMENT=production
```

### 3. TLS / SSL Termination

For **self-signed internal certs**:
```bash
# Generate self-signed certificate
mkdir -p certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/key.pem -out certs/cert.pem \
  -subj "/CN=localhost"
```

For **letsencrypt** (public exposure):
```bash
apt install certbot
certbot certonly --standalone -d api.yourdomain.com
```

### 4. Start Services

```bash
# Load production environment
set -a && source .env.production && set +a

# Start in detached mode
docker compose up -d

# Verify all services healthy
docker compose ps
```

### 5. Health Verification

```bash
# Check all endpoints
curl -sf http://localhost:8080/flask/health
curl -sf http://localhost:8080/django/health
curl -sf http://localhost:8080/fastapi/health

# Check JWT API
curl -sf -X POST http://localhost:8080/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"adminpass123"}'
```

### 6. Backup Configuration

```bash
# Copy and configure backup
cp backup/config.sh backup/config.local.sh

# Edit backup/config.local.sh:
#   BACKUP_PROVIDER=local  # or s3, b2, rsync
#   KEEP_LOCAL_DAYS=7
#   GPG_RECIPIENT=your@email.com (optional)
```

### 7. Log Rotation

```bash
# Configure logrotate for nginx logs
cat >> /etc/logrotate.d/pypong <<EOF
/var/lib/docker/containers/*/pypong-*-container/*.log {
    rotate 14
    daily
    compress
    delaycompress
    copytruncate
}
EOF
```

---

## Docker Swarm (High Availability)

```bash
# Initialize swarm
docker swarm init --advertise-addr <your-ip>

# Deploy stack
docker stack deploy -c compose.yaml pypong

# Verify
docker stack services pypong
```

---

## Database Migration (Alembic)

```bash
# Install alembic in Flask container
docker exec pypong-flask-container pip install alembic>=1.13.0

# Initialize alembic (first time)
docker exec -it pypong-flask-container sh -c "cd /var/www && alembic init migrations"

# Create migration
docker exec pypong-flask-container sh -c "cd /var/www && alembic revision --autogenerate -m 'initial'"

# Apply migration
docker exec pypong-flask-container sh -c "cd /var/www && alembic upgrade head"
```

---

## Rollback Procedure

```bash
# Restart with previous image tag
docker compose pull
docker compose down
docker compose up -d

# Or: specific version
docker pull ghcr.io/albertguedes/pypong/flask:v0.10.0
docker compose rm -f flask && docker compose up -d flask
```

---

## Monitoring

### Prometheus Metrics

Prometheus format metrics available at:
```
http://localhost:8080/flask/metrics
http://localhost:8080/django/metrics
http://localhost:8080/fastapi/metrics
```

Add to `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'pypong'
    static_configs:
      - targets:
        - 'localhost:8080/flask'
```

### Sentry Error Tracking

Set `SENTRY_DSN` environment variable to your Sentry DSN. Errors are automatically captured with trace context.

### Health Monitoring

```bash
# Cron check script
*/5 * * * * curl -sf http://localhost:8080/flask/health || \
  echo "PYPONG HEALTH WARNING" | mail -s "Health Check Failed" admin@example.com
```

---

## Troubleshooting

### Services Won't Start

```bash
docker compose logs --tail=50
docker compose ps
cat .env  # verify env file exists and has values
```

### Database Connection Fails

```bash
docker exec pypong-postgresql-container pg_isready -U docker -d dockerdb
docker exec pypong-flask-container sh -c "curl -sf http://localhost:8000/health"
```

### Out of Memory

```bash
# Increase swap (Ubuntu/Debian)
dd if=/dev/zero of=/swapfile bs=1M count=1024
mkswap /swapfile
swapon /swapfile
```

---

## Security Hardening Checklist

- [ ] Strong JWT secret (`openssl rand -hex 32`)
- [ ] TLS enabled and working
- [ ] Database credentials changed from defaults
- [ ] No secrets in `.env` committed to version control
- [ ] nginx rate limiting verified
- [ ] Firewall configured (only ports 80/443 exposed)
- [ ] Docker daemon logs rotated
- [ ] Fail2ban configured for SSH brute-force protection
