# Architecture

This document explains what was built, why each piece was chosen over its more
"conventional" production alternative, and what the trade-offs of that choice are.
The constraint driving every decision here is **permanently-free-tier infrastructure
only** — no EKS, no custom domain, no paid AWS services, nothing that starts
billing after a 12-month introductory window. Where that constraint forced a
compromise against what a well-funded production system would do, it's called
out explicitly rather than hidden.

## Contents

- [System overview](#system-overview)
- [Component breakdown](#component-breakdown)
- [Free-tier vs. "ideal production" trade-offs](#free-tier-vs-ideal-production-trade-offs)
- [Security model](#security-model)
- [Environments](#environments)
- [Observability](#observability)
- [Rollback strategy](#rollback-strategy)
- [Testing strategy](#testing-strategy)
- [CI/CD pipeline](#cicd-pipeline)
- [Out of scope / explicitly not built](#out-of-scope--explicitly-not-built)

---

## System overview

```
                         ┌────────────────────────┐
                         │   Cloudflare Pages      │
                         │   React + Vite + TS SPA │
                         └───────────┬─────────────┘
                                     │ HTTPS (CORS-restricted)
                                     ▼
                         ┌────────────────────────┐
                         │  Lambda Function URL    │
                         │  auth = NONE (public)   │
                         └───────────┬─────────────┘
                                     │ invoke
                                     ▼
                         ┌────────────────────────┐
                         │  AWS Lambda             │
                         │  FastAPI + Mangum       │
                         │  one function per env,  │
                         │  "live" alias for       │
                         │  rollback               │
                         └───────────┬─────────────┘
                                     │ TLS, pooled via asyncpg
                                     ▼
                         ┌────────────────────────┐
                         │  Neon Postgres          │
                         │  branch: dev / prod     │
                         └────────────────────────┘

  Terraform state  →  Terraform Cloud (free tier)
  CI/CD             →  GitHub Actions, OIDC → AWS (no static keys)
  k8s skills demo    →  kind cluster spun up inside a GH Actions runner, torn down after smoke test
```

The backend is a single FastAPI application wrapped by [Mangum](https://mangum.io/)
so the exact same ASGI app runs locally (`uvicorn`) and in Lambda — no
Lambda-specific branching in application code.

## Component breakdown

### Backend — FastAPI on Lambda

- **Why Lambda + Function URL, not API Gateway:** API Gateway's free tier is
  12 months only; after that it bills per request. A Lambda Function URL is a
  first-class, permanently-free way to get an HTTPS endpoint in front of a
  Lambda function, with no additional service in the request path.
- **Why not a long-running container (ECS/Fargate/EC2):** all of those either
  fall outside the always-free tier or require a running instance (cost, and
  operational surface) that a Function URL avoids entirely. The trade-off is
  cold starts (see below).
- **Trade-off — cold starts:** Lambda cold starts (typically several hundred ms
  for a Python/FastAPI app) are a real UX cost a warm container wouldn't have.
  Mitigated partially by keeping the deployment package small (no heavy
  dependencies) and Python's comparatively fast cold-start profile vs. e.g. JVM
  runtimes. Not mitigated with provisioned concurrency, since that isn't free.

### Database — Neon Postgres

- Serverless Postgres with a genuinely permanent free tier, and — critically
  for this project — **branching**: dev and prod get separate database
  branches from the same project, which is what makes true environment
  isolation possible without paying for two separate managed databases.

### Frontend — React + Vite + TypeScript on Cloudflare Pages

- Static SPA, built by Vite, deployed to Cloudflare Pages (free tier: unlimited
  requests/bandwidth, global CDN, free `*.pages.dev` subdomain).
- **Why Cloudflare Pages over Vercel:** Vercel's free tier carries commercial-use
  restrictions and usage caps that are easy to trip accidentally; Cloudflare's
  free tier has no such restriction and no realistic path to surprise billing.

### Auth — JWT with argon2 + refresh rotation

- Passwords hashed with **argon2id** (via `argon2-cffi`), the current OWASP
  recommendation — resistant to GPU/ASIC cracking in a way bcrypt/PBKDF2 are not.
- **Access tokens:** short-lived (15 min), stateless JWT, validated on every
  request without a DB round-trip.
- **Refresh tokens:** opaque, stored **hashed** in a `refresh_tokens` table,
  rotated on every use (old token invalidated, new one issued). If a refresh
  token is presented that's already been used, the entire token family is
  revoked — this is reuse-detection, the standard signal that a token was
  stolen and replayed.
- **Why not pure stateless refresh (refresh-JWT-with-a-JWT):** it can't be
  revoked before expiry. A stolen refresh token would stay valid until it
  naturally expired. The DB-backed table costs one extra query per refresh but
  makes logout and theft-response actually work.

### IaC — Terraform

- Manages the Lambda function, its IAM execution role, and the Function URL
  configuration. No manual console changes for anything Terraform owns.
- **State backend: Terraform Cloud (free tier)**, not S3+DynamoDB. S3's free
  tier is 12-months-only for a new account; after that, storing state there
  would incur (trivial, but nonzero) cost, which breaks the "permanently free"
  constraint on principle even though the dollar amount is negligible. DynamoDB's
  free tier is permanent, but pairing it with a non-permanent S3 tier doesn't
  fully solve the problem. Terraform Cloud sidesteps this entirely — free forever,
  built-in state locking, no AWS resources consumed just to hold state.

### CI/CD — GitHub Actions + OIDC

- Actions is free for public repos. AWS auth uses **OIDC federation**
  (`aws-actions/configure-aws-credentials` with a GitHub OIDC provider trust
  relationship) — the workflow assumes a role scoped to exactly what it needs,
  and no long-lived AWS access keys are ever stored as GitHub secrets.

### Kubernetes demo — kind, inside CI only

- A dedicated workflow spins up a [kind](https://kind.sigs.k8s.io/) cluster
  inside the GitHub Actions runner itself, applies the `k8s-demo/` kustomize
  manifests, runs a smoke test against the deployed service, then tears the
  cluster down. This demonstrates kustomize/kubectl/manifest competency without
  needing a persistent (and non-free) managed cluster like EKS.
- This is explicitly a **skills demonstration**, not a claim that the actual
  application runs on Kubernetes in this project — the real app runs on Lambda.
  README/ARCHITECTURE will be explicit about that distinction so it doesn't
  read as misleading.

---

## Free-tier vs. "ideal production" trade-offs

| Area | Chosen (free-tier) | "Ideal" production alternative | Why the trade-off is acceptable here |
|---|---|---|---|
| Compute | Lambda Function URL | ECS/Fargate behind an ALB, or EKS | Cold starts vs. zero idle cost; acceptable for a portfolio-traffic workload |
| API layer | Direct Function URL | API Gateway (WAF, throttling, custom domain, request validation) | API Gateway's free tier expires after 12 months; documented mitigation below |
| Edge protection | None (no WAF/CloudFront) | CloudFront + AWS WAF in front of the API | Both are paid; mitigated with Lambda reserved concurrency cap + app-level rate limiting discussion below |
| Database | Neon serverless Postgres (free tier, branch-based envs) | RDS Multi-AZ with automated backups/PITR | Neon's free tier has no Multi-AZ/HA guarantee; acceptable for a non-critical-uptime portfolio app |
| State backend | Terraform Cloud free tier | S3 + DynamoDB with versioning/replication | Functionally similar; TFC avoids the 12-month S3 free-tier cliff |
| Domain | `*.pages.dev` / default Lambda URL | Custom domain + ACM cert + Route 53 | Route 53 hosted zones aren't free; a custom domain isn't required to demonstrate the underlying skills |
| Alerting | Documented plan only (see below) | CloudWatch Alarms + SNS + on-call paging | Alarms are cheap but not literally free at meaningful thresholds; kept as a documented "what I'd add" section |
| Networking | No VPC (public internet egress) | Lambda in a private VPC subnet | VPC egress needs a NAT Gateway (~$32/mo+); the function calls Neon over the public internet anyway, so VPC placement would add cost with no real isolation benefit here |
| Log/env-var encryption | AWS-managed key (default) | Customer-managed KMS key | A CMK costs ~$1/mo per key; AWS's default already encrypts at rest, just without customer-controlled rotation |
| Code integrity | GitHub Actions OIDC as the only deploy path | AWS Signer code-signing | OIDC already means only that one pipeline can update the function; signing profiles add setup complexity disproportionate to a single-maintainer project |
| Log retention | 14 days | 1+ year | Bounds CloudWatch Logs storage cost; a portfolio project has no compliance reason to keep logs longer |

### On the missing WAF/edge protection specifically

Because the Function URL's auth mode must be `NONE` for a browser SPA to call
it directly (see [Security model](#security-model)), the endpoint is publicly
invokable by anyone, not just this app's frontend. In a funded production
setting, the fix is CloudFront + AWS WAF (rate-based rules, managed rule
groups) in front of the origin. Neither is free. The mitigation actually
shipped here is:

1. **Lambda reserved concurrency cap** on the function — bounds the maximum
   simultaneous executions, which bounds both blast-radius cost from an abuse
   spike and protects the account's overall concurrency budget from being
   exhausted by this one function. **Currently unset in practice**: a
   brand-new AWS account starts with an account-wide concurrency limit of
   only 10, and AWS requires at least 10 to remain unreserved, so there's no
   room to reserve any amount on either function yet. AWS raises this
   automatically as an account ages (or it can be requested); the Terraform
   variable defaults to `null` (unmanaged) for exactly this reason and
   should be set once the account limit increases.
2. **Application-level rate limiting** (documented as a should-add; see below)
   on auth endpoints specifically, since credential-stuffing/brute-force is the
   most realistic abuse pattern for a public auth endpoint.

This is called out explicitly rather than silently omitted, because "no edge
protection" is a real security posture difference from a system fronted by
CloudFront+WAF, and pretending otherwise would undercut the point of this
document.

---

## Security model

- **Transport:** HTTPS everywhere (Lambda Function URLs and Cloudflare Pages
  both terminate TLS by default; no plaintext HTTP path exists).
- **AuthN:** JWT access tokens (15 min TTL) + rotating refresh tokens (see above).
- **AuthZ:** every bookmark/tag resource is scoped to `current_user.id` at the
  query level (never trust a client-supplied user ID); ownership checked before
  any read/write.
- **IAM:** the Lambda execution role is scoped to exactly the actions/resources
  it needs (e.g. `logs:CreateLogStream`/`logs:PutLogEvents` on its own log
  group only) — no wildcard `*` actions or resources anywhere in the Terraform.
  GitHub Actions' OIDC role is similarly scoped to only the actions needed to
  update this specific Lambda function/alias, not account-wide deploy rights.
- **Secrets:** DB connection string and JWT signing key are Lambda environment
  variables sourced from GitHub Actions secrets at deploy time, never committed.
  (Documented improvement: AWS Secrets Manager / SSM Parameter Store would be
  the production-grade choice for rotation, but both have per-secret costs
  beyond a small free allotment — noted as a "what I'd add" item, not shipped.)
- **Dependency hygiene:** Dependabot for both `pip` and `npm` ecosystems;
  `pip-audit` and `npm audit` run in CI on every PR; `trivy config` and
  `checkov` scan the Terraform on every PR. (Originally planned as `tfsec` +
  checkov, but tfsec's last release was over a year before this was written —
  its ruleset was absorbed into Trivy, which is what's actually maintained
  now.)
- **CloudWatch Logs encryption:** left on AWS's default (encrypted at rest
  with an AWS-owned key), not a customer-managed KMS key. A CMK is genuinely
  useful for controlling key rotation/access, but costs ~$1/month per key —
  a real dollar cost this project is specifically built to avoid, for
  non-sensitive application logs. Flagged by Trivy (AWS-0017, low severity),
  accepted deliberately rather than silently ignored.
- **Frontend token storage:** the access token lives only in memory (a module
  variable, never persisted); the refresh token is stored in `localStorage`.
  The backend issues tokens as a plain JSON response rather than an httpOnly
  cookie, so there's no storage option on the frontend that's fully invisible
  to JS — `localStorage` is the pragmatic choice given that, not a solved
  problem. What actually limits the blast radius of an XSS-stolen refresh
  token is the backend's rotation + reuse detection (a stolen token gets
  replayed at most once before the whole family is revoked), not where the
  frontend keeps it.

---

## Environments

`dev` and `prod` are genuinely separate, not a shared environment with a
naming convention pretending otherwise:

- **Database:** distinct Neon **branches** per environment, distinct connection
  strings.
- **Compute:** **separate Lambda functions per environment** (`bookmarks-api-dev`,
  `bookmarks-api-prod`), each with its own IAM role, log group, Function URL,
  and environment variables (DB branch connection string, JWT secret). Lambda
  environment variables belong to a function/version, not to an alias, so a
  single shared function couldn't actually give dev and prod independent
  config through aliases alone — that would need republishing the function's
  env vars between every dev and prod deploy, which is fragile and easy to
  get wrong. Separate functions is the standard pattern and mirrors the
  per-environment Neon branch split above.
- **Rollback within an environment:** each function still has a `live` alias
  the Function URL invokes through — publishing a new version and repointing
  `live` is the actual rollback mechanism (see
  [Rollback strategy](#rollback-strategy)). That part of the original design
  was right; what changed here is that dev/prod no longer share one function.
- **Frontend:** Cloudflare Pages' built-in preview-deployments-per-branch cover
  `dev`; `main` branch deploys to the production Pages URL.

---

## Observability

**Shipped:** structured JSON logging from the FastAPI app (one JSON object per
log line — `level`, `timestamp`, `request_id`, `message`, structured context
fields), written to stdout, which Lambda automatically ships to CloudWatch Logs.
This makes logs queryable via CloudWatch Logs Insights even without any
alarms configured. X-Ray tracing is also enabled on both functions
(`tracing_config { mode = "Active" }`) — genuinely free up to 100k
traces/month, well beyond what a portfolio project's traffic would ever hit.

**Documented, not implemented (would add if this were funded production):**

- **CloudWatch Alarms** on: Lambda error rate (`Errors`/`Invocations` ratio),
  p99 `Duration`, `Throttles` count, and Neon connection failures surfaced as
  a custom metric from the app.
- **SNS topic** fanning out alarm state changes to email/Slack/PagerDuty.
- **A dashboard** aggregating Lambda concurrency, error rate, and DB connection
  pool saturation on one screen.
- Reasoning for not shipping alarms: CloudWatch Alarms are technically
  low-cost (not literally free past a small allotment) and pull in SNS, which
  is a second service to wire up correctly — for a portfolio project with no
  real users to page for, the honest choice was to document the design rather
  than build alerting theater with nothing behind it to alert on.

---

## Rollback strategy

- **Backend (Lambda):** every deploy publishes a new **Lambda version** on
  that environment's function, and its **`live` alias** is what the Function
  URL actually invokes. Rolling back is repointing `live` to the previous
  version — no redeploy, no rebuild, near-instant. Terraform manages the
  alias resource, so a rollback is a one-line `alias.function_version` change
  applied via the same pipeline as a forward deploy (keeping rollback in the
  same reviewed, audited path as every other change).
- **Frontend (Cloudflare Pages):** every push creates an immutable deployment;
  rollback is re-promoting a previous deployment to production via the
  Cloudflare dashboard or `wrangler pages deployment` CLI — no rebuild needed
  since the previous build artifact still exists.

---

## Testing strategy

- **Unit tests** (`backend/tests/unit`): pure logic — password hashing, JWT
  encode/decode, service-layer functions — with the DB mocked/excluded.
- **Integration tests** (`backend/tests/integration`): run against a real
  Postgres instance (a `services: postgres` container in the GitHub Actions
  job, not a mock) — covers actual SQLAlchemy queries, migrations via Alembic,
  and full request/response cycles through FastAPI's `TestClient`.
- **Coverage** tracked via `pytest-cov`, enforced as a CI gate (threshold TBD
  once the initial test suite exists — will not invent a number before there's
  real code to measure).
- **Frontend:** component/unit tests via Vitest; `tsc --strict` and ESLint as
  additional correctness gates in CI.

---

## CI/CD pipeline

Five workflows, each scoped to one concern:

1. `backend-ci.yml` — ruff, black --check, mypy (strict), pytest+coverage,
   pip-audit. Runs on every PR touching `backend/`.
2. `frontend-ci.yml` — eslint, `tsc --noEmit --strict`, vitest, npm audit.
   Runs on every PR touching `frontend/`.
3. `terraform-ci.yml` — `terraform fmt -check`, `terraform validate` (each
   of `global`/`envs/dev`/`envs/prod`), `trivy config`, and `checkov`.
   **Never runs `plan` or `apply`** from this workflow. A `terraform plan`
   posted as a PR comment was the original goal, but plan needs real AWS
   credentials to refresh state against actual resources - the OIDC role
   this project uses only has narrow deploy permissions (update Lambda
   code/config, nothing else), and provisioning a second, broader
   read-only role just for CI plan visibility was judged not worth the
   added IAM surface for a portfolio project where every apply is already
   run locally and reviewed by hand before confirming. Documented as a
   "would add" item, not shipped.
4. `k8s-kind-demo.yml` — spins up kind, applies `k8s-demo/`, smoke-tests, tears
   down. Independent of the real app's deploy path.
5. Deploy workflows (`deploy-dev.yml` / `deploy-prod.yml`) — added later, once
   Terraform and the backend both exist to deploy. Will require explicit
   discussion before being wired to run `apply` automatically, and prod deploys
   will be gated behind a manual approval (GitHub Environments protection
   rule), not auto-deployed on merge.

---

## Out of scope / explicitly not built

Listed here so it's a documented decision, not an oversight:

- **Custom domain** — by design constraint (no Route 53 cost).
- **EKS / any managed Kubernetes control plane** — by design constraint; the
  `k8s-demo/` job demonstrates the skill without the cost.
- **Multi-region / DR** — no free-tier path to this that isn't essentially
  fake; not worth simulating.
- **Real alerting/on-call** — see [Observability](#observability); documented,
  not built.
- **Secrets Manager/rotation** — see [Security model](#security-model);
  documented as a production upgrade, not built.

---

*This document will be updated as each stage (backend skeleton, frontend
skeleton, Terraform, CI/CD, k8s demo) is actually built — sections above
describe the target design agreed before implementation, per the project's
build process.*
