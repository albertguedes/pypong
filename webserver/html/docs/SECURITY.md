# Security Policy

**PYPONG** is committed to security. Please follow this policy when reporting vulnerabilities.

---

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.10.x  | :white_check_mark: |

---

## Reporting a Vulnerability

If you discover a security vulnerability, please report it privately:

1. **Do not** open a public GitHub Issue for security vulnerabilities
2. Email: `albertguedes@pm.me` with subject `[SECURITY] PYPONG`
3. Include in your report:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes (optional)

**Expected response time:** 48 hours acknowledgement, 7 days for resolution.

---

## Security Domains

### Secrets Management
- Never commit `.env` or any file containing real credentials
- Use `JWT_SECRET` and database passwords via environment variables only
- CI/CD secrets are stored in GitHub Secrets, never in YAML files

### Authentication
- All `/v1/*` routes require valid JWT Bearer token
- `/v1/auth/token` is rate-limited at nginx level (10 req/s burst 20)
- Password hashes via SHA-256 (acceptable for MVP; bcrypt recommended for production)

### Network
- Services bind to `127.0.0.1` only
- Exposed ports: `8080` (nginx), `5432` (postgresql on bridge only)
- nginx is the only internet-facing component

### Dependencies
- All Python dependencies are pinned with minimum version constraints
- Trivy vulnerability scanning runs in CI before Docker image build
- Alpine Linux base images for minimal attack surface

---

## Known Security Considerations for Production

Before deploying to production, address the following:

- [ ] Set a strong `JWT_SECRET` (minimum 32 characters, use `openssl rand -hex 32`)
- [ ] Enable TLS termination at nginx (self-signed cert for internal, letsencrypt for public)
- [ ] Change default database credentials
- [ ] Review `docker-compose.yml` port bindings — remove `127.0.0.1` binding only after TLS is configured
- [ ] Enable database connection pooling and query logging
- [ ] Set `DEBUG=False` in Django settings (Django defaults to `DEBUG=True` in dev)

---

## Dependency Updates

Update dependencies regularly:

```bash
# Audit Python dependencies
pip install safety
safety check --file src/flask/requirements.txt

# Update all pinning
# Review changelogs before upgrading major versions
```

---

## Changelog

No security advisories issued yet.
