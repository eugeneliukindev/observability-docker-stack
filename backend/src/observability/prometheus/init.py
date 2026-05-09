from __future__ import annotations

from typing import TYPE_CHECKING

from prometheus_client import CollectorRegistry, make_asgi_app, multiprocess
from starlette.types import ASGIApp

if TYPE_CHECKING:
    from fastapi import FastAPI


def init_prometheus(app: FastAPI) -> None:
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)  # type: ignore[no-untyped-call]
    metrics_app: ASGIApp = make_asgi_app(registry=registry)
    app.mount(path="/metrics", app=metrics_app, name="metrics")
