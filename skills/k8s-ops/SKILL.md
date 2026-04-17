---
name: k8s-ops
description: Kubernetes troubleshooting, deployment, and operations. Use when debugging pods, checking cluster health, or working with manifests.
---
# Kubernetes Operations

## Troubleshooting Flow
1. `kubectl get pods -n <ns>` — check status
2. For non-Running pods: `kubectl describe pod <name>` — check events
3. For CrashLoopBackOff: `kubectl logs <pod> --previous` — check last crash
4. For pending pods: check node resources and PVC bindings
5. For networking: `kubectl get svc,ingress -n <ns>`

## Safety
In general, never modify things. I'll do it manually. Letting an AI agent modify cloud ressources is way to dangerous. If you ever try to, warn me and ask me. Consider I'll say no 99.99% of the time.

- NEVER run `kubectl delete` without explicit user confirmation
- NEVER modify production resources without confirming namespace
- Always specify namespace explicitly, don't rely on current context
- Use `--dry-run=client -o yaml` to preview changes

## Manifests
- Use kustomize or helm, not raw YAML in production
- Resource limits on all containers
- Liveness + readiness probes on all services
- Pod disruption budgets for production workloads
