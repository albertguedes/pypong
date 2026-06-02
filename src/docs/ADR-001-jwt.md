# ADR-001: JWT Authentication Strategy

**Date:** 2026-06-02
**Status:** Decided

## Context

The API needs stateless authentication to identify and authorize requests from registered users. The system targets startup teams consuming the API from web and mobile clients.

## Decision

We chose **JWT (JSON Web Tokens)** with the following characteristics:

- **Algorithm:** HS256 (HMAC using SHA-256) — symmetric, well-supported, fast
- **Secret:** Stored in `JWT_SECRET` env var, derived from `POSTGRES_PASSWORD` in dev
- **Token types:**
  - Access token: 15 minute TTL, used for API calls
  - Refresh token: 7 day TTL, used to obtain new access tokens
- **Library:** PyJWT — pure Python, works across Flask/Django/FastAPI
- **Storage:** `USERS_DB` dict in-memory for MVP (no persistent user store yet)

## Rationale

- HS256 is industry standard, simpler than RSA for single-service deployments
- Separate access/refresh tokens allow short-lived access without re-login
- PyJWT is lightweight and has no native async concerns (works in sync and async contexts)
- In-memory user store is appropriate for MVP; database-backed store follows in production iteration

## Consequences

- No token revocation before expiry (refresh tokens can't be invalidated individually in MVP)
- User store resets on container restart (acceptable for dev; production needs persistent storage)
- Future migration path: Redis-backed session store for token blacklist/revocations

## Deferred

- Redis-backed token storage and revocation list (v1.1)
- RSA key pair for asymmetric signatures (v2.0, if multi-service auth needed)
