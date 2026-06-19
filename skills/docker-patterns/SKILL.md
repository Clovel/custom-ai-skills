---
name: docker-patterns
description: Dockerfile and docker-compose best practices. Use when creating, editing, or reviewing Dockerfiles or compose files.
---
# Docker Patterns

## Dockerfile
- Multi-stage builds: separate build and runtime stages
- Use specific base image tags, never `latest`
- Order layers for cache efficiency: deps → build → copy
- Non-root user in runtime stage
- Use .dockerignore to exclude node_modules, .git, dist

## Node.js Specific
- Use `node:22-slim` for runtime, `node:22` for build
- Copy package.json + lockfile first, install, then copy source
- Use `--production` or `--omit=dev` for runtime deps only

## Compose
- Use profiles for optional services
- Named volumes for persistent data
- Health checks on all services
- Environment variables via `.env` file, avoid hardcoded unless pre-existing or really constant config.
