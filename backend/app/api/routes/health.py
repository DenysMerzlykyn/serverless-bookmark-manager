from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Liveness check only — no DB dependency, so it stays fast and reports
    correctly even if the database is unreachable (that's a separate concern
    from "is the Lambda function itself alive and serving").
    """
    return {"status": "ok"}
