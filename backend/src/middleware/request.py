import logging
import time
import uuid
from collections.abc import Collection
from typing import Final

from fastapi import status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from src.logger import request_id_ctx_var

_REQUEST_ID_HEADER: Final[str] = "X-Request-Id"
_SECONDS_TO_MS: Final[int] = 1000

# fmt: off
_BASE_FMT: Final[str] = (
    "method=%s | "
    "url=%s | "
    "status=%d | "
    "dur=%dms | "
    "ua=%s | "
    "size=%d bytes"
)
# fmt: on

_ACCESS_INFO_FMT: Final[str] = "HTTP | SUCCESS | " + _BASE_FMT
_ACCESS_WARNING_FMT: Final[str] = "HTTP | CLIENT ERROR | " + _BASE_FMT
_ACCESS_ERROR_FMT: Final[str] = "HTTP | SERVER ERROR | " + _BASE_FMT

log = logging.getLogger("app.access")


class RequestAccessMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, excluded_urls: Collection[str] = frozenset()):
        super().__init__(app)
        self._excluded_urls = excluded_urls

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self._excluded_urls:
            return await call_next(request)

        request_id = request.headers.get(_REQUEST_ID_HEADER) or uuid.uuid4().hex
        request_id_ctx_var.set(request_id)

        method = request.method
        path = request.url.path
        query = request.url.query
        full_url = f"{path}?{query}" if query else path
        user_agent = request.headers.get("user-agent", "-")
        start_time = time.perf_counter()

        response = await call_next(request)

        status_code = response.status_code
        duration_ms = int((time.perf_counter() - start_time) * _SECONDS_TO_MS)
        size = int(response.headers.get("content-length", 0))

        response.headers[_REQUEST_ID_HEADER] = request_id

        if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:  # Server error
            log.error(
                _ACCESS_ERROR_FMT,
                method,
                full_url,
                status_code,
                duration_ms,
                user_agent,
                size,
            )
        elif status_code >= status.HTTP_400_BAD_REQUEST:  # Client error
            log.warning(
                _ACCESS_WARNING_FMT,
                method,
                full_url,
                status_code,
                duration_ms,
                user_agent,
                size,
            )
        else:  # Success
            log.info(
                _ACCESS_INFO_FMT,
                method,
                full_url,
                status_code,
                duration_ms,
                user_agent,
                size,
            )

        return response
