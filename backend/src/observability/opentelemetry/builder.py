from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Self

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.trace import TracerProvider

if TYPE_CHECKING:
    from src.observability.builder import ObservabilityBuilder


class OtlpBuilder:
    def __init__(
        self,
        parent: ObservabilityBuilder,
        tracer_provider: TracerProvider,
    ) -> None:
        self._parent = parent
        self._tracer_provider = tracer_provider

    def with_logging(self, *, set_logging_format: bool = True) -> Self:
        LoggingInstrumentor().instrument(set_logging_format=set_logging_format)
        return self

    def with_fastapi(self, excluded_urls: Iterable[str] | None = None) -> Self:
        resolved_excluded_urls = excluded_urls or self._parent.excluded_urls
        FastAPIInstrumentor.instrument_app(
            self._parent.app,
            tracer_provider=self._tracer_provider,
            excluded_urls=",".join(resolved_excluded_urls) if resolved_excluded_urls else None,
        )
        return self

    def done(self) -> ObservabilityBuilder:
        return self._parent
