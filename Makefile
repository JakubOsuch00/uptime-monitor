.PHONY: up down logs test lint scan cluster deploy k8s-status destroy

KUBECONFIG := terraform/uptime-config
export KUBECONFIG

# docker compose
up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api worker

# code
test:
	pytest -v

lint:
	ruff check .
	ruff format --check .

scan:
	docker build -t uptime-monitor:local .
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:0.67.2 \
		image --severity HIGH,CRITICAL --ignore-unfixed uptime-monitor:local

# kubernetes (local kind cluster)
cluster:
	terraform -chdir=terraform init
	terraform -chdir=terraform apply -auto-approve

deploy:
	docker build -t uptime-monitor:local .
	kind load docker-image uptime-monitor:local --name uptime
	helm upgrade --install uptime helm/uptime-monitor -n uptime --create-namespace \
		--set image.repository=uptime-monitor --set image.tag=local --wait

k8s-status:
	kubectl -n uptime get pods,svc,ingress

destroy:
	terraform -chdir=terraform destroy -auto-approve
