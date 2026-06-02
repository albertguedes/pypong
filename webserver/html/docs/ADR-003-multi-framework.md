# ADR-003: Multi-Framework Architecture

**Date:** 2026-06-02
**Status:** Decided

## Context

PYPONG serves teams evaluating different Python web frameworks. Three frameworks are available simultaneously via nginx reverse proxy, each exposing identical endpoints. The architecture must allow teams to switch between frameworks without changing client code.

## Decision

### Framework Ports
| Framework | Internal Port | nginx Route |
|-----------|--------------|-------------|
| Flask     | 8000         | `/flask/*`  |
| Django    | 8001         | `/django/*` |
| FastAPI   | 8002         | `/fastapi/*`|

### API Routes
All framework-specific endpoints for the dashboard are prefixed with the framework name.
The **JWT API** (v1) is served exclusively through Flask at `/v1/*` — the authoritative API entry point.

### Endpoint Parity
Each framework provides: `/`, `/health`, `/database`, `/metrics`, `/{framework_name}`

### Shared Conventions
- Identical error response format: `{"error": {"code", "message", "details"}}`
- Prometheus text format for `/metrics`
- Request ID propagation via `X-Request-ID` header
- Health check verifies PostgreSQL connectivity

## Rationale

- Separating Dashboard routes from API routes prevents routing ambiguity
- Flask is the API workhorse (gunicorn+threaded workers for sync DB calls)
- Django and FastAPI are available for team evaluation without affecting the API
- Identical error format ensures consistent client experience regardless of which framework handles a request

## Consequences

- Django/FastAPI do not implement the `/v1/*` JWT API (Flask is the sole v1 API provider)
- Adding API features to Django/FastAPI requires explicit decision; each framework maintains its own routing
- Clients consuming `/v1/*` are tightly coupled to Flask implementation

## Deferred
- API gateway/load balancer layer abstracting framework choice
- Shared user/auth store across all frameworks (currently only Flask-backed)
