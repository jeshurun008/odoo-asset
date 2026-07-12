from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.core.config import settings
from app.core.middleware.correlation import CorrelationMiddleware
from app.core.middleware.headers import SecurityHeadersMiddleware
from app.exceptions.handlers import register_exception_handlers
from app.logging.logger import setup_logging

# Initialise structured JSON logging
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "AssetFlow Enterprise Asset & Resource Management API.\n\n"
        "### Auth Flow (Swagger UI Support)\n"
        "1. Click **Authorize**.\n"
        "2. Input registered user credentials in the OAuth2 form.\n"
        "3. Session tokens will be automatically propagated."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Register custom global exception handlers formatting Error Response Envelope
register_exception_handlers(app)

# Register middlewares in correct pipeline order (correlation first to track downstream operations)
app.add_middleware(CorrelationMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "X-Correlation-Id", "X-Request-Id"]
)

# Mount versioned routes under /api/v1
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
async def root():
    """Simple API Root/Health endpoint verifying container status."""
    return {
        "status": "success",
        "data": {
            "app": settings.PROJECT_NAME,
            "status": "operational",
            "phase": "Phase 1 - Foundation & Authentication"
        }
    }
