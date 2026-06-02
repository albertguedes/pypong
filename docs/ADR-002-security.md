# ADR-002: Infrastructure Security Defaults

**Date:** 2026-06-02
**Status:** Decided

## Context

Services bind to `127.0.0.1` only, preventing external exposure. nginx is the only internet-facing component. All credentials pass via environment variables rather than baked into images.

## Decision

### Network Security
- nginx binds to `127.0.0.1:8080` — not exposed externally by default
- Database port randomized on host (bridge network, no host binding)
- All inter-service traffic uses Docker bridge DNS (`pypong-*container*`)

### Secrets Management
- `.env` file is gitignored and never committed
- `.env.example` is the template (safe to commit)
- `JWT_SECRET` and `POSTGRES_PASSWORD` are the critical secrets
- No secrets baked into Docker images (only via env_file at runtime)

### Container Security
- Python containers run as non-root user `appuser` (uid 1000)
- nginx mounts application code read-only
- All images based on Alpine Linux (minimal attack surface)

### Production Hardening (Not Included in MVP)
- TLS termination at nginx (letsencrypt or cloud provider cert)
- Docker Secrets for sensitive env vars in swarm mode
- Network policies restricting inter-service communication
- Automated vulnerability scanning (Trivy in CI)

## Consequences

- Development convenience preserved; production requires explicit hardening
- Users can expose ports for local testing but must opt-in to external exposure
- Backup encryption optional via GPG (`GPG_RECIPIENT` in `config.local.sh`)

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
