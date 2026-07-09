from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from app.api.routes import health
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title="Serverless Bookmark Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)

# Entry point AWS Lambda invokes. Mangum translates the Lambda Function URL's
# event/response shape to/from ASGI so `app` runs unmodified in both Lambda
# and local uvicorn.
handler = Mangum(app)
