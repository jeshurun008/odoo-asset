import traceback
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.exceptions.base import AppException
from app.exceptions.exceptions import InternalException
from app.logging.logger import correlation_id_ctx, get_logger
from app.schemas.envelope import ErrorPayload, ErrorResponse

logger = get_logger("exception_handlers")


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers globally on the FastAPI application."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        correlation_id = correlation_id_ctx.get()
        
        # Log custom exceptions at warning/info level as they represent known domain scenarios
        logger.warning(
            f"Application Exception: {exc.code} - {exc.message}",
            extra={"extra_data": {
                "code": exc.code,
                "correlation_id": correlation_id,
                "details": exc.details
            }}
        )

        payload = ErrorPayload(
            code=exc.code,
            message=exc.message,
            correlation_id=correlation_id,
            details=exc.details
        )
        response_content = ErrorResponse(error=payload).model_dump()
        return JSONResponse(
            status_code=exc.status_code,
            content=response_content
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        correlation_id = correlation_id_ctx.get()
        
        # Format the Pydantic error list to a cleaner layout for clients
        errors = exc.errors()
        formatted_details = {}
        for err in errors:
            # Join the location tuples (e.g. body, username) to a dot path or field name
            loc_path = ".".join(str(loc) for loc in err["loc"][1:]) if len(err["loc"]) > 1 else str(err["loc"][0])
            formatted_details[loc_path] = err["msg"]

        logger.info(
            f"Validation Exception: {formatted_details}",
            extra={"extra_data": {
                "correlation_id": correlation_id,
                "errors": formatted_details
            }}
        )

        payload = ErrorPayload(
            code="VALIDATION_ERROR",
            message="Input validation failed.",
            correlation_id=correlation_id,
            details=formatted_details
        )
        response_content = ErrorResponse(error=payload).model_dump()
        return JSONResponse(
            status_code=422,
            content=response_content
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        correlation_id = correlation_id_ctx.get()
        status_code = exc.status_code
        message = exc.detail

        code_map = {
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            429: "TOO_MANY_REQUESTS"
        }
        code = code_map.get(status_code, "HTTP_ERROR")

        payload = ErrorPayload(
            code=code,
            message=message,
            correlation_id=correlation_id
        )
        response_content = ErrorResponse(error=payload).model_dump()
        return JSONResponse(
            status_code=status_code,
            content=response_content
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = correlation_id_ctx.get()
        
        # Log the full stack trace server-side for debugging with correlation ID
        stack_trace = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        logger.error(
            f"Unhandled Exception occurred: {str(exc)}\n{stack_trace}",
            extra={"extra_data": {
                "correlation_id": correlation_id
            }}
        )

        # Do NOT leak the internal stack trace or raw exception to the client
        payload = ErrorPayload(
            code="INTERNAL_ERROR",
            message="An unexpected server error occurred. Please contact support.",
            correlation_id=correlation_id
        )
        response_content = ErrorResponse(error=payload).model_dump()
        return JSONResponse(
            status_code=500,
            content=response_content
        )
