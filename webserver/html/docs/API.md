# Python API Documentation

API documentation for the Flask application in `src/app.py`.

---

## Module: app

Flask application providing HTTP endpoints for system status, health checks, database connectivity, and metrics.

**Author:** albert r. carnier guedes (albert@teko.net.br)
**License:** MIT

---

## Functions

### get_db_connection()

**Description:**
Creates and returns a new PostgreSQL database connection using environment variables.

**Returns:**
`psycopg2.connection` - A PostgreSQL connection object.

**Raises:**
`psycopg2.Error` - If connection fails.

**Environment Variables:**
| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `127.0.0.1` | Database host |
| `POSTGRES_PORT` | `5432` | Database port |
| `POSTGRES_DB` | `dockerdb` | Database name |
| `POSTGRES_USER` | `docker` | Database user |
| `POSTGRES_PASSWORD` | `''` | Database password |

---

## Endpoints

### GET /

**Description:**
Returns an HTML status page with system information.

**Returns:**
`Response` (mimetype: `text/html`)

**Content:**
- `status`: Always `"ok"`
- `python_version`: Output of `python --version` command
- `timestamp`: Current UTC timestamp in ISO 8601 format

---

### GET /health

**Description:**
Health check endpoint for monitoring and load balancer probes.

**Returns:**
`Response` (mimetype: `text/plain`) - Content: `"OK"`

**Status Codes:**
- `200` - Service is healthy

---

### GET /database

**Description:**
Tests database connectivity and returns connection status.

**Returns:**
`Response` (mimetype: `text/plain`)

**Success Response:**
```
Connected to '{POSTGRES_DB}' on '{POSTGRES_HOST}:{POSTGRES_PORT}'.
```

**Error Response:**
```
Error: Unable to connect to '{POSTGRES_DB}' on '{POSTGRES_HOST}:{POSTGRES_PORT}'.
```

**Status Codes:**
- `200` - Connection successful
- `500` - Connection failed

---

### GET /metrics

**Description:**
Returns JSON-formatted system and database metrics.

**Returns:**
`Response` (mimetype: `application/json`)

**Response Schema:**
```json
{
  "status": "ok",
  "timestamp": "ISO8601 timestamp",
  "database": {
    "connected": true,
    "size_bytes": 7689907,
    "size_human": "7.33 MB",
    "connections": 1
  }
}
```

**Database Fields:**
- `connected` (`bool`): True if connection successful
- `size_bytes` (`int`): Database size in bytes (via `pg_database_size()`)
- `size_human` (`str`): Human-readable size (e.g., "7.33 MB")
- `connections` (`int`): Current connection count (via `pg_stat_activity`)

**Status Codes:**
- `200` - Always (errors are reported in `database.connected` field)

---

### GET /flask

**Description:**
Returns JSON confirmation that Flask is working, including version information.

**Returns:**
`Response` (mimetype: `application/json`)

**Response Schema:**
```json
{
  "flask": "working",
  "version": "3.1.3",
  "python_version": "Python 3.13.13",
  "timestamp": "ISO8601 timestamp"
}
```

**Status Codes:**
- `200` - Always

---

## Usage

### Running the Application Locally (Development)

```bash
cd src
python app.py
# Flask runs on http://127.0.0.1:8000
```

### Running with Gunicorn (Production)

```bash
gunicorn --bind 0.0.0.0:8000 --workers 2 app:app
```

---

## Testing

Tests are located in `src/tests/test_app.py` and run inside the Docker container:

```bash
# Via Makefile
make test

# Via Docker exec
docker exec pypong-python-container pytest -v
```

**Test Coverage:**
- `test_health_endpoint` - Verifies `/health` returns 200 with "OK"
- `test_database_endpoint_success` - Verifies `/database` when DB is reachable
- `test_database_endpoint_failure` - Verifies `/database` returns 500 on failure
- `test_metrics_endpoint_success` - Verifies `/metrics` returns valid JSON
- `test_index_endpoint` - Verifies `/` returns 200

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| flask | >=3.0.0 | Web framework |
| gunicorn | >=23.0.0 | WSGI server |
| psycopg2-binary | >=2.9.0 | PostgreSQL adapter |
| pytest | >=8.0.0 | Testing framework |