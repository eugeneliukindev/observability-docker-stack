from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pyroscope.otel import PyroscopeSpanProcessor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from src.__version__ import VERSION
from src.config import EXCLUDED_PATHS_GRAFANA
from src.env import APP_NAME, OTLP_ENDPOINT


def init_otlp(app: FastAPI) -> None:
    resource = Resource.create(attributes={"service.name": APP_NAME, "service.version": VERSION})
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True))
    )
    # Links trace spans with Pyroscope profiles — enables "Profiles" button in Tempo
    tracer_provider.add_span_processor(PyroscopeSpanProcessor())
    trace.set_tracer_provider(tracer_provider)
    # You can add custom log correlation in Logging Filter instead instrumentation like:
    # def filter(self, record: logging.LogRecord) -> bool:
    #    span = trace.get_current_span()
    #    ctx = span.get_span_context()
    #    record.otelTraceID = trace.format_trace_id(ctx.trace_id)
    #    record.otelSpanID = trace.format_span_id(ctx.span_id)
    #    return True
    # https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/logging/logging.html
    LoggingInstrumentor().instrument(set_logging_format=True)
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=tracer_provider,
        excluded_urls=",".join(EXCLUDED_PATHS_GRAFANA),
    )
