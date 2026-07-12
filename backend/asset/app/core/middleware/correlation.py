import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.logging.logger import correlation_id_ctx, request_id_ctx


class CorrelationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that captures or generates X-Correlation-Id and X-Request-Id.
    Propagates them into async-safe ContextVars for structured logging
    and returns them in response headers.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())

        # Bind variables for the duration of this request context
        token_corr = correlation_id_ctx.set(correlation_id)
        token_req = request_id_ctx.set(request_id)

        try:
            response = await call_next(request)
            response.headers["X-Correlation-Id"] = correlation_id
            response.headers["X-Request-Id"] = request_id
            return response
        finally:
            # Reset tokens to clean up context memory
            correlation_id_ctx.reset(token_corr)
            request_id_ctx.reset(token_req)
