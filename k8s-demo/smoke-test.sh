#!/usr/bin/env bash
# Exercises the app deployed into the kind cluster through a port-forwarded
# Service. Goes beyond a bare liveness check - /health has no DB dependency
# (see backend/app/api/routes/health.py), so a real register+login round
# trip is what actually proves Postgres, the migration Job, and the app are
# all wired together correctly, not just that the process started.
set -euo pipefail

BASE_URL="${1:?usage: smoke-test.sh <base-url>}"
EMAIL="kind-smoke-test-$(date +%s)@example.com"
PASSWORD="KindSmokeTest123!"

echo "Checking ${BASE_URL}/health ..."
STATUS=$(curl -s -o /tmp/health.json -w "%{http_code}" "${BASE_URL}/health")
if [ "$STATUS" != "200" ]; then
  echo "health check failed: HTTP $STATUS" >&2
  cat /tmp/health.json >&2
  exit 1
fi
echo "health ok: $(cat /tmp/health.json)"

echo "Registering a test user ..."
STATUS=$(curl -s -o /tmp/register.json -w "%{http_code}" -X POST "${BASE_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"${EMAIL}\", \"password\": \"${PASSWORD}\"}")
if [ "$STATUS" != "201" ]; then
  echo "register failed: HTTP $STATUS" >&2
  cat /tmp/register.json >&2
  exit 1
fi
echo "register ok: $(cat /tmp/register.json)"

echo "Logging in as the test user ..."
STATUS=$(curl -s -o /tmp/login.json -w "%{http_code}" -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"${EMAIL}\", \"password\": \"${PASSWORD}\"}")
if [ "$STATUS" != "200" ]; then
  echo "login failed: HTTP $STATUS" >&2
  cat /tmp/login.json >&2
  exit 1
fi
if ! grep -q "access_token" /tmp/login.json; then
  echo "login response missing access_token" >&2
  cat /tmp/login.json >&2
  exit 1
fi
echo "login ok: real access_token issued"

echo "Smoke test passed."
