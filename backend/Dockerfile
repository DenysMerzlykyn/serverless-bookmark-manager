# Used only by the kind-based k8s skills demo (see ARCHITECTURE.md
# "Kubernetes demo") - the real app runs on Lambda via Mangum, not in this
# container. app.main:app is the same FastAPI instance either way; this
# image just serves it with uvicorn instead of wrapping it in the Lambda
# handler.
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Only the runtime dependency tree, same as the Lambda deployment package -
# pytest/ruff/etc. never need to be in this image either. uvicorn is pinned
# to match the version already used as backend-ci's dev-extra, without
# adding a new pyproject.toml dependency group just for this one image.
RUN pip install --no-cache-dir . "uvicorn[standard]>=0.32,<0.33"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
