from html import escape

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
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
    docs_url=None,
    redoc_url=None,
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


@app.get("/docs", include_in_schema=False, response_class=HTMLResponse)
async def custom_docs():
    """Self-contained API docs page that does not depend on external CDN assets."""
    schema = app.openapi()
    paths = schema.get("paths", {})
    method_order = ["get", "post", "put", "patch", "delete"]
    rows = []

    for path, operations in sorted(paths.items()):
        for method in method_order:
            operation = operations.get(method)
            if not operation:
                continue
            summary = operation.get("summary") or operation.get("operationId") or ""
            tags = ", ".join(operation.get("tags", []))
            rows.append(
                "<tr>"
                f"<td><span class='method {method}'>{method.upper()}</span></td>"
                f"<td><code>{escape(path)}</code></td>"
                f"<td>{escape(summary)}</td>"
                f"<td>{escape(tags)}</td>"
                "</tr>"
            )

    endpoints = "\n".join(rows) or (
        "<tr><td colspan='4'>No endpoints are currently registered.</td></tr>"
    )

    return HTMLResponse(
        f"""
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>{escape(settings.PROJECT_NAME)} API Docs</title>
            <style>
                :root {{
                    color-scheme: light;
                    --bg: #f7f8fb;
                    --panel: #ffffff;
                    --text: #172033;
                    --muted: #667085;
                    --line: #d9dee8;
                    --accent: #2563eb;
                }}
                * {{ box-sizing: border-box; }}
                body {{
                    margin: 0;
                    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                    background: var(--bg);
                    color: var(--text);
                }}
                main {{
                    width: min(1120px, calc(100% - 32px));
                    margin: 40px auto;
                }}
                header {{
                    display: flex;
                    align-items: flex-end;
                    justify-content: space-between;
                    gap: 24px;
                    margin-bottom: 24px;
                }}
                h1 {{
                    margin: 0 0 8px;
                    font-size: 34px;
                    line-height: 1.1;
                }}
                p {{
                    margin: 0;
                    color: var(--muted);
                }}
                a {{
                    color: var(--accent);
                    text-decoration: none;
                    font-weight: 650;
                }}
                .panel {{
                    background: var(--panel);
                    border: 1px solid var(--line);
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 10px 30px rgba(17, 24, 39, 0.06);
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                th, td {{
                    padding: 14px 16px;
                    border-bottom: 1px solid var(--line);
                    text-align: left;
                    vertical-align: top;
                }}
                th {{
                    font-size: 12px;
                    letter-spacing: 0;
                    text-transform: uppercase;
                    color: var(--muted);
                    background: #fbfcfe;
                }}
                tr:last-child td {{ border-bottom: 0; }}
                code {{
                    font-family: "Cascadia Code", Consolas, monospace;
                    font-size: 13px;
                }}
                .method {{
                    display: inline-block;
                    min-width: 62px;
                    padding: 5px 8px;
                    border-radius: 6px;
                    color: #fff;
                    font-size: 12px;
                    font-weight: 750;
                    text-align: center;
                }}
                .get {{ background: #16803c; }}
                .post {{ background: #2563eb; }}
                .put {{ background: #a855f7; }}
                .patch {{ background: #d97706; }}
                .delete {{ background: #dc2626; }}
                .links {{
                    display: flex;
                    gap: 14px;
                    flex-wrap: wrap;
                    margin-top: 12px;
                }}
                @media (max-width: 720px) {{
                    main {{ width: min(100% - 20px, 1120px); margin: 24px auto; }}
                    header {{ display: block; }}
                    th:nth-child(4), td:nth-child(4) {{ display: none; }}
                }}
            </style>
        </head>
        <body>
            <main>
                <header>
                    <div>
                        <h1>{escape(settings.PROJECT_NAME)} Backend</h1>
                        <p>API is running. Use the endpoints below or inspect the raw OpenAPI schema.</p>
                        <div class="links">
                            <a href="/">Health Check</a>
                            <a href="{escape(settings.API_V1_STR)}/openapi.json">OpenAPI JSON</a>
                        </div>
                    </div>
                    <p>Version {escape(schema.get("info", {}).get("version", "1.0.0"))}</p>
                </header>
                <section class="panel">
                    <table>
                        <thead>
                            <tr>
                                <th>Method</th>
                                <th>Path</th>
                                <th>Summary</th>
                                <th>Tags</th>
                            </tr>
                        </thead>
                        <tbody>
                            {endpoints}
                        </tbody>
                    </table>
                </section>
            </main>
        </body>
        </html>
        """
    )


@app.get("/redoc", include_in_schema=False)
async def redoc_redirect():
    return RedirectResponse(url="/docs")


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
