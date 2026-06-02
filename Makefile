.PHONY: help build up down logs shell clean test test-flask test-django test-fastapi test-backup backup restore crontab release prepare-release

DOCKER := docker
COMPOSE := $(DOCKER) compose

help:
	@echo "PYPONG - Python Multi-Framework Docker Development Environment"
	@echo ""
	@echo "5 containers: nginx + Flask + Django + FastAPI + postgresql"
	@echo ""
	@echo "Commands:"
	@echo "  make build          Build Docker images"
	@echo "  make up             Start all containers"
	@echo "  make down           Stop all containers"
	@echo "  make logs           View logs"
	@echo "  make shell          Shell into container (service=flask|django|fastapi|db|webserver)"
	@echo "  make clean          Remove containers and volumes"
	@echo "  make test           Run all tests (curl + pytest for all frameworks)"
	@echo "  make test-flask    Run Flask tests only"
	@echo "  make test-django   Run Django tests only"
	@echo "  make test-fastapi   Run FastAPI tests only"
	@echo "  make test-backup    Run backup script tests"
	@echo "  make backup         Backup database"
	@echo "  make restore        Restore database (file=<backup>)"
	@echo "  make crontab        Install crontab jobs"
	@echo "  make prepare-release VERSION=x.y.z  Prepare release (update VERSION + CHANGELOG)"
	@echo "  make release VERSION=x.y.z  Create release commit + tag + push"

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
ifdef service
	$(COMPOSE) logs $(service)
else
	$(COMPOSE) logs
endif

shell:
	@if [ -z "$(service)" ]; then \
		echo "Usage: make shell service=<flask|django|fastapi|db|webserver>"; \
		exit 1; \
	fi
	@case "$(service)" in \
		db) container="pypong-postgresql-container";; \
		flask) container="pypong-flask-container";; \
		django) container="pypong-django-container";; \
		fastapi) container="pypong-fastapi-container";; \
		webserver) container="pypong-nginx-container";; \
		*) echo "Invalid service: $(service)"; exit 1;; \
	esac
	$(DOCKER) exec -it $$container /bin/sh

clean:
	$(COMPOSE) down -v

status:
	$(COMPOSE) ps

test:
	@echo "Testing Flask endpoints..."
	@curl -sf http://localhost:8080/flask/ > /dev/null && echo "OK: Flask /flask/"
	@curl -sf http://localhost:8080/flask/health > /dev/null && echo "OK: Flask /flask/health"
	@curl -sf http://localhost:8080/flask/database > /dev/null && echo "OK: Flask /flask/database"
	@curl -sf http://localhost:8080/flask/metrics > /dev/null && echo "OK: Flask /flask/metrics"
	@curl -sf http://localhost:8080/flask/v1 > /dev/null && echo "OK: Flask /flask/v1"
	@echo "SKIP: Flask /flask/v1/auth/register (requires POST)" || true
	@echo "SKIP: Flask /flask/v1/auth/token (requires POST)" || true
	@echo "SKIP: Flask /flask/v1/protected (requires auth)" || true
	@echo ""
	@echo "Testing Django endpoints..."
	@curl -sf http://localhost:8080/django/ > /dev/null && echo "OK: Django /django/"
	@curl -sf http://localhost:8080/django/health > /dev/null && echo "OK: Django /django/health"
	@curl -sf http://localhost:8080/django/database > /dev/null && echo "OK: Django /django/database"
	@curl -sf http://localhost:8080/django/metrics > /dev/null && echo "OK: Django /django/metrics"
	@curl -sf http://localhost:8080/django/v1 > /dev/null && echo "OK: Django /django/v1"
	@echo "SKIP: Django /django/v1/auth/register (requires POST)" || true
	@echo "SKIP: Django /django/v1/auth/token (requires POST)" || true
	@echo ""
	@echo "Testing FastAPI endpoints..."
	@curl -sf http://localhost:8080/fastapi/ > /dev/null && echo "OK: FastAPI /fastapi/"
	@curl -sf http://localhost:8080/fastapi/health > /dev/null && echo "OK: FastAPI /fastapi/health"
	@curl -sf http://localhost:8080/fastapi/database > /dev/null && echo "OK: FastAPI /fastapi/database"
	@curl -sf http://localhost:8080/fastapi/metrics > /dev/null && echo "OK: FastAPI /fastapi/metrics"
	@curl -sf http://localhost:8080/fastapi/v1 > /dev/null && echo "OK: FastAPI /fastapi/v1"
	@echo "SKIP: FastAPI /fastapi/v1/auth/register (requires POST)" || true
	@echo "SKIP: FastAPI /fastapi/v1/auth/token (requires POST)" || true
	@echo ""
	@echo "Testing PostgreSQL..."
	@$(DOCKER) exec pypong-postgresql-container pg_isready -U docker -d dockerdb && echo "OK: db"
	@echo ""
	@echo "Running Flask pytest..."
	@$(DOCKER) exec pypong-flask-container pytest -v tests/

test-flask:
	@$(DOCKER) exec pypong-flask-container pytest -v

test-django:
	@$(DOCKER) exec pypong-django-container pytest -v

test-fastapi:
	@$(DOCKER) exec pypong-fastapi-container pytest -v

test-backup:
	@bash backup/test_backup.sh

backup:
	@bash backup/backup.sh

restore:
	@bash backup/restore.sh $(file)

crontab:
	@echo "Installing crontab..."
	@cat crontab.txt | crontab -
	@echo "Done. Crontab installed:"
	@crontab -l

release:
	@if [ -z "$(VERSION)" ]; then \
		echo "Usage: make release VERSION=x.y.z"; \
		exit 1; \
	fi
	@bash scripts/create-release.sh $(VERSION)

prepare-release:
	@if [ -z "$(VERSION)" ]; then \
		echo "Usage: make prepare-release VERSION=x.y.z"; \
		exit 1; \
	fi
	@bash scripts/prepare-release.sh $(VERSION)