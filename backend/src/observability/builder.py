from __future__ import annotations

from collections.abc import Collection
from typing import Self

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from .opentelemetry.builder import OtlpBuilder
from .opentelemetry.tracer import create_tracer_provider
from .prometheus.init import init_prometheus
from .pyroscope.init import init_pyroscope


class ObservabilityBuilder:
    """Configures observability backends for a FastAPI application."""

    def __init__(
        self,
        app: FastAPI,
        service_name: str,
        service_version: str,
        *,
        excluded_urls: Collection[str] = frozenset(),
    ) -> None:
        self._app = app
        self._service_name = service_name
        self._service_version = service_version
        self._excluded_urls = excluded_urls

    def with_otlp(
        self,
        endpoint: str,
        *,
        service_name: str | None = None,
        service_version: str | None = None,
        insecure: bool = True,
    ) -> OtlpBuilder:
        tracer_provider = create_tracer_provider(
            endpoint=endpoint,
            service_name=service_name or self._service_name,
            service_version=service_version or self._service_version,
            insecure=insecure,
        )
        trace.set_tracer_provider(tracer_provider)
        return OtlpBuilder(parent=self, tracer_provider=tracer_provider)

    def with_prometheus(self) -> Self:
        init_prometheus(self._app)
        return self

    def with_pyroscope(
        self,
        host: str,
        port: int = 4040,
        *,
        secure: bool = False,
        service_name: str | None = None,
    ) -> Self:
        init_pyroscope(
            application_name=service_name or self._service_name,
            host=host,
            port=port,
            secure=secure,
        )
        return self

    @property
    def excluded_urls(self) -> Collection[str]:
        return self._excluded_urls

    @property
    def app(self) -> FastAPI:
        return self._app
