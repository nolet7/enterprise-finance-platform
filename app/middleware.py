"""Low-cardinality structured access logs and response security headers.

No user claims, authorization headers, bodies, query strings, or raw URL IDs
are logged. The route template is obtained from the matched FastAPI route.
"""
import json
import logging
import sys
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("lsk.access")
logger.setLevel(logging.INFO)
if not logger.handlers:
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(stream)
logger.propagate = False


class EnterpriseRequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid4())  # Never trust an attacker-controlled trace ID
        started = time.perf_counter()
        status_code = 500
        route = "unmatched"
        try:
            response = await call_next(request)
            status_code = response.status_code
            route_obj = request.scope.get("route")
            route = str(getattr(route_obj, "path", "unmatched"))
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Cache-Control"] = "no-store"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
            return response
        finally:
            logger.info(json.dumps({
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "route": route[:120],
                "status_code": status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            }, separators=(",", ":")))
