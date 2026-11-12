.PHONY: up down logs test lint scan

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api worker

test:
	pytest -v

lint:
	ruff check .
	ruff format --check .

scan:
	docker build -t uptime-monitor:local .
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:0.67.2 \
		image --severity HIGH,CRITICAL --ignore-unfixed uptime-monitor:local
