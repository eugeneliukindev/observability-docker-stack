from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pyroscope.otel import PyroscopeSpanProcessor


def create_tracer_provider(
    service_name: str,
    service_version: str,
    endpoint: str,
    insecure: bool = True,
) -> TracerProvider:
    resource = Resource.create(
        attributes={
            "service.name": service_name,
            "service.version": service_version,
        }
    )
    tracer_provider = TracerProvider(resource=resource)
    otlp_span_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=insecure)
    batch_span_processor = BatchSpanProcessor(otlp_span_exporter)

    tracer_provider.add_span_processor(batch_span_processor)
    tracer_provider.add_span_processor(
        PyroscopeSpanProcessor()
    )  # Links trace spans with Pyroscope profiles — enables "Profiles" button in Tempo
    return tracer_provider
