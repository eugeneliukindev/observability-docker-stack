import time
from collections.abc import Collection

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match, Route
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlette.types import ASGIApp

from src.__version__ import VERSION
from src.observability.prometheus.constants import (
    EXCEPTIONS,
    INFO,
    REQUESTS,
    REQUESTS_IN_PROGRESS,
    REQUESTS_PROCESSING_TIME,
    RESPONSES,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, version: str = VERSION, excluded_urls: Collection[str] = frozenset()) -> None:
        super().__init__(app)
        INFO.labels(version=version).set(1)
        self._excluded_urls = excluded_urls

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self._excluded_urls:
            return await call_next(request)

        if (path := self._get_route_path(request)) is None:
            return await call_next(request)

        method = request.method
        REQUESTS.labels(method=method, path=path).inc()
        REQUESTS_IN_PROGRESS.labels(method=method, path=path).inc()
        before_time = time.perf_counter()
        status_code = HTTP_500_INTERNAL_SERVER_ERROR
        try:
            response = await call_next(request)
        except BaseException as e:
            status_code = HTTP_500_INTERNAL_SERVER_ERROR
            EXCEPTIONS.labels(method=method, path=path, exception_type=type(e).__name__).inc()
            raise
        else:
            status_code = response.status_code
            # Exemplars are not supported with prometheus_multiproc mode — observe() accepts
            # an exemplar kwarg but the multiprocess value collector silently drops them.
            REQUESTS_PROCESSING_TIME.labels(method=method, path=path).observe(time.perf_counter() - before_time)
        finally:
            RESPONSES.labels(method=method, path=path, status_code=status_code).inc()
            REQUESTS_IN_PROGRESS.labels(method=method, path=path).dec()

        return response

    @staticmethod
    def _get_route_path(request: Request) -> str | None:
        """Return the route template path (e.g. /api/items/{item_id}) for the request,
        or None if no route matches.

        Redis hashmap so all Gunicorn workers share a single warmed cache instead of each
        building their own:

            async def get_route_path_redis(self, request: Request) -> str | None:
                raw_path = request.url.path

                # Redis HGET/HSET stores all routes under one key — avoids per-key TTL
                # overhead and keeps the cache queryable as a single hash for inspection.
                cached = await redis.hget("route_cache", raw_path)
                if cached is not None:
                    return cached or None  # empty string is stored for unmatched paths

                for route in request._app.routes:
                    match, _ = route.matches(request.scope)
                    if match == Match.FULL:
                        await redis.hset("route_cache", raw_path, route.path)
                        return route.path

                await redis.hset("route_cache", raw_path, "")
                return None
        """
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL and isinstance(route, Route):
                return route.path
        return None
