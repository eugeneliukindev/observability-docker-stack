from __future__ import annotations

import pyroscope


def init_pyroscope(
    application_name: str,
    host: str,
    port: int,
    secure: bool = False,
) -> None:
    # Per-endpoint CPU profiling via pyroscope.tag_wrapper is not supported in async Python:
    # tag_wrapper uses thread-local storage, so tags leak across concurrent coroutines on the
    # same OS thread. Per-trace profiles are linked via PyroscopeSpanProcessor instead.
    # https://github.com/grafana/pyroscope-rs/issues/132
    scheme = "https" if secure else "http"
    pyroscope.configure(
        application_name=application_name,
        server_address=f"{scheme}://{host}:{port}",
        sample_rate=100,
        oncpu=True,
        gil_only=True,
    )
