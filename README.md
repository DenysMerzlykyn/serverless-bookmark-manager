# serverless-bookmark-manager

A production-grade bookmark manager built entirely on **permanently-free-tier**
infrastructure — no EKS, no custom domain, no paid AWS services. The point of
this project is the infrastructure and engineering practice around it
(IAM least-privilege, IaC, CI/CD, testing, rollback strategy, documented
trade-offs), not the CRUD app itself, which is intentionally small.

> **Status:** scaffolding stage. Backend, frontend, and infra are being built
> incrementally, each stage reviewed before moving to the next. This README
> will be updated with live links once there's something deployed.

## Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI on AWS Lambda (via Mangum), exposed through a Lambda Function URL |
| Database | Neon Postgres (serverless, branch-per-environment) + SQLAlchemy + Alembic |
| Auth | JWT (argon2id password hashing), short-lived access tokens + rotating refresh tokens with reuse detection |
| Frontend | React + Vite + TypeScript, deployed to Cloudflare Pages |
| IaC | Terraform (Lambda, IAM, Function URL), state in Terraform Cloud |
| CI/CD | GitHub Actions, AWS auth via OIDC (no static access keys) |
| K8s demo | `kind` cluster spun up inside a GitHub Actions runner, kustomize-applied, smoke-tested, torn down |

Full reasoning behind every choice above — including where a free-tier option
was picked over the "ideal" production alternative and why — is in
[ARCHITECTURE.md](./ARCHITECTURE.md).

## Repository layout

```
backend/          FastAPI app, SQLAlchemy models, Alembic migrations, tests
frontend/         React + Vite + TypeScript SPA
infra/terraform/  Lambda, IAM, Function URL — modules + per-env (dev/prod) config
k8s-demo/         kustomize manifests for the CI-only kind cluster demo
.github/workflows/ CI (lint/test/scan on every PR) and deploy pipelines
```

## Local development

_To be filled in once the backend skeleton exists._

## License

MIT — see [LICENSE](./LICENSE).
