# Monitoring Middleware — Automatically tracks API request latency and errors
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to record API latency and error rates for every request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        # Normalize path: strip query params, collapse IDs to {id}
        path = request.url.path
        if path.startswith("/api/"):
            from app.services.monitoring_service import record_request
            record_request(request.method, path, response.status_code, duration_ms)

        return response
