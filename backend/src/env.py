import os

# Application
APP_NAME: str = os.environ.get("APP_NAME", "backend")
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

# Pyroscope
PYROSCOPE_HOST: str = os.environ.get("PYROSCOPE_HOST", "alloy")
PYROSCOPE_PORT: int = int(os.environ.get("PYROSCOPE_PORT", "4040"))

# OTLP (gRPC, host:port without scheme)
OTLP_HOST: str = os.environ.get("OTLP_HOST", "alloy")
OTLP_PORT: int = int(os.environ.get("OTLP_PORT", "4317"))
OTLP_ENDPOINT: str = f"{OTLP_HOST}:{OTLP_PORT}"

EXCLUDED_URLS = frozenset({"/metrics", "/metrics/", "/health"})

# Prometheus multiprocess dir — must match PROMETHEUS_MULTIPROC_DIR env var
PROMETHEUS_MULTIPROC_DIR: str = os.environ.get("PROMETHEUS_MULTIPROC_DIR", "/tmp/prometheus-metrics")
