.PHONY: help build up down logs shell clean test test-backup backup restore crontab test-unit test-integration release

DOCKER := docker
COMPOSE := $(DOCKER) compose

help:
	@echo "Minimal Viable Docker Development Environment"
	@echo ""
	@echo "3 containers: nginx + Python + postgresql"
	@echo ""
	@echo "Commands:"
	@echo "  make build          Build Docker images"
	@echo "  make up             Start all containers"
	@echo "  make down           Stop all containers"
	@echo "  make logs           View logs"
	@echo "  make shell          Shell into container (service=python|db|webserver)"
	@echo "  make clean          Remove containers and volumes"
	@echo "  make test           Run all tests (curl + pytest)"
	@echo "  make test-unit      Run unit tests only"
	@echo "  make test-integration  Run integration tests only"
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
		echo "Usage: make shell service=<db|python|webserver>"; \
		exit 1; \
	fi
	@case "$(service)" in \
		db) container="pypong-postgresql-container";; \
		python) container="pypong-python-container";; \
		webserver) container="pypong-nginx-container";; \
		*) echo "Invalid service: $(service)"; exit 1;; \
	esac
	$(DOCKER) exec -it $$container /bin/sh

clean:
	$(COMPOSE) down -v

status:
	$(COMPOSE) ps

test:
	@echo "Testing endpoints..."
	@curl -sf http://localhost:8080/ > /dev/null && echo "OK: /"
	@curl -sf http://localhost:8080/health > /dev/null && echo "OK: /health"
	@curl -sf http://localhost:8080/database > /dev/null && echo "OK: /database"
	@curl -sf http://localhost:8080/metrics > /dev/null && echo "OK: /metrics"
	@$(DOCKER) exec pypong-postgresql-container pg_isready -U docker -d dockerdb && echo "OK: db"
	@echo ""
	@echo "Running pytest..."
	@$(DOCKER) exec pypong-python-container pytest -v

test-unit:
	@$(DOCKER) exec pypong-python-container pytest -v tests/test_app.py

test-integration:
	@$(DOCKER) exec pypong-python-container pytest -v tests/

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