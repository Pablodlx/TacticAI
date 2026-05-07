# Docker layout

- `Dockerfile.web`: FastAPI API image for local + Cloud Run.
- `Dockerfile.worker`: worker image for local + GCE GPU.
- `docker-compose.local.yml`: local reproducible stack.
- `docker-compose.cloud.yml`: worker-only GPU-oriented compose.

