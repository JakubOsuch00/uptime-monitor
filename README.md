# uptime-monitor

Small app that checks if websites are up and how fast they respond. I made it to practice DevOps things: Docker, CI/CD, Kubernetes, Helm, Terraform and monitoring with Prometheus and Grafana. Everything runs locally, no cloud needed.

The app has two parts. The API (FastAPI) lets you add and remove websites and shows a status page with uptime from the last 24h. The worker checks every website every 30 seconds, saves the result in PostgreSQL and exposes Prometheus metrics. They use the same Docker image, only the start command is different.

## Docker Compose

```
cp .env.example .env
docker compose up -d --build
```

The status page is on http://localhost:8080 (Nginx in front of the API), Grafana on http://localhost:3000 (admin / password from .env) with a ready dashboard, Prometheus on http://localhost:9090.

Adding a website:

```
curl -X POST localhost:8080/api/targets -H "Content-Type: application/json" -d '{"name": "example", "url": "https://example.com"}'
```

The Dockerfile has two stages so the final image doesn't have build tools, runs as a non root user and has a healthcheck. Prometheus has three alert rules: website down for 2 minutes, slow response (p95 over 2s) and worker not running.

## Kubernetes

Terraform creates a local kind cluster (control plane and one worker node) and installs Traefik as the ingress controller. The app is installed with the Helm chart from helm/uptime-monitor. The k8s/ folder has the same thing as plain manifests (kubectl apply -k k8s/), I wrote them first and then made the chart from them.

```
make cluster    # terraform apply
make deploy     # build image, load it into kind, helm install
make k8s-status
```

After that the app is on http://uptime.localhost:8088. To remove everything run make destroy.

The API runs in 2 replicas with liveness, readiness and startup probes, resource limits and a read only filesystem. The worker has 1 replica and the Recreate strategy, because two workers would check every website twice. PostgreSQL is a StatefulSet with a persistent volume. The chart can also use an external database (postgres.enabled=false) and has an optional HorizontalPodAutoscaler.

## CI/CD

GitHub Actions runs ruff and pytest, then installs the Helm chart on a kind cluster inside the pipeline and does a smoke test with curl. After that the image is built, scanned with Trivy (the build fails on HIGH or CRITICAL vulnerabilities) and pushed to GitHub Container Registry with the commit sha and latest tags (and the version on git tags). There is also a simpler .gitlab-ci.yml for GitLab.

## Problems I ran into

Nginx returned 502 after the API container was recreated, because it resolves the hostname only once at startup and kept the old IP. Fixed by using the Docker DNS resolver with a variable in proxy_pass.

In Kubernetes the API and the worker crashed with "invalid literal for int(): tcp://10.96.139.160:9100". Kubernetes adds environment variables for every service in the namespace and the service called worker-metrics created WORKER_METRICS_PORT, which is also the name of my config variable. Fixed with enableServiceLinks: false.

The pods restarted 2 times on the first start, because they started before PostgreSQL was ready. Now the app retries the database connection on startup and the API has a startup probe, so there are no restarts.

Trivy found two HIGH vulnerabilities in zlib from the base image. The fix was already in Debian, so the Dockerfile runs apt-get upgrade.

Wikipedia was shown as down because it returns 403 for requests without a User-Agent, so the worker sends one.

## Tests

```
pip install -r requirements-dev.txt
pytest
```

The tests use SQLite and a mocked HTTP client, so they don't need a database or internet.

## What could be added

Secrets are in values.yaml and k8s/config.yaml only for the local demo, in a real setup they would come from something like sealed-secrets or Vault. Database migrations with Alembic instead of create_all. Alertmanager to send the alerts somewhere (Slack, email) and Prometheus inside the cluster.
