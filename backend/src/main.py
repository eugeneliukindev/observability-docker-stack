import asyncio
import random

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.__version__ import VERSION
from src.env import APP_NAME
from src.logger import configure_logging, log
from src.middleware import MetricsMiddleware, RequestAccessMiddleware
from src.observability import init_observability

configure_logging()

app = FastAPI(title=APP_NAME, version=VERSION)

app.add_middleware(MetricsMiddleware)
app.add_middleware(RequestAccessMiddleware)

init_observability(app=app)


class ItemBody(BaseModel):
    name: str
    price: float = 0.0


@app.get("/")
def read_root():
    return {"message": "API is running", "version": VERSION}


@app.get("/health", include_in_schema=False)
async def healthcheck() -> JSONResponse:
    return JSONResponse(status_code=200, content={"status": "healthy"})


# --- Items CRUD ---

@app.get("/api/items")
async def list_items():
    await asyncio.sleep(random.uniform(0.01, 0.1))
    log.app.info("Listing items")
    return {"items": [{"id": i, "name": f"Item {i}", "price": round(random.uniform(10, 999), 2)} for i in range(1, 6)]}


@app.get("/api/items/{item_id}")
async def get_item(item_id: int):
    await asyncio.sleep(random.uniform(0.005, 0.05))
    if item_id <= 0:
        raise HTTPException(status_code=400, detail="item_id must be positive")
    if item_id > 100:
        raise HTTPException(status_code=404, detail="Item not found")
    log.app.info("Getting item id=%d", item_id)
    return {"id": item_id, "name": f"Item {item_id}", "price": round(random.uniform(10, 999), 2)}


@app.post("/api/items", status_code=201)
async def create_item(body: ItemBody):
    await asyncio.sleep(random.uniform(0.02, 0.15))
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="name cannot be empty")
    new_id = random.randint(100, 9999)
    log.app.info("Created item id=%d name=%s", new_id, body.name)
    return {"id": new_id, "name": body.name, "price": body.price}


@app.put("/api/items/{item_id}")
async def update_item(item_id: int, body: ItemBody):
    await asyncio.sleep(random.uniform(0.01, 0.1))
    if item_id > 100:
        raise HTTPException(status_code=404, detail="Item not found")
    log.app.info("Updated item id=%d", item_id)
    return {"id": item_id, "name": body.name, "price": body.price}


@app.patch("/api/items/{item_id}")
async def patch_item(item_id: int, body: ItemBody):
    await asyncio.sleep(random.uniform(0.01, 0.08))
    if item_id > 100:
        raise HTTPException(status_code=404, detail="Item not found")
    log.app.info("Patched item id=%d", item_id)
    return {"id": item_id, "name": body.name, "price": body.price}


@app.delete("/api/items/{item_id}", status_code=204)
async def delete_item(item_id: int):
    await asyncio.sleep(random.uniform(0.005, 0.05))
    if item_id > 100:
        raise HTTPException(status_code=404, detail="Item not found")
    log.app.info("Deleted item id=%d", item_id)


# --- Orders ---

@app.post("/api/orders", status_code=201)
async def create_order(body: dict):
    await asyncio.sleep(random.uniform(0.05, 0.3))
    log.app.info("Created order")
    return {"order_id": random.randint(1000, 9999), "status": "pending"}


@app.get("/api/orders/{order_id}")
async def get_order(order_id: int):
    await asyncio.sleep(random.uniform(0.01, 0.07))
    if order_id > 9999:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"order_id": order_id, "status": random.choice(["pending", "processing", "done"])}


@app.delete("/api/orders/{order_id}", status_code=204)
async def cancel_order(order_id: int):
    await asyncio.sleep(random.uniform(0.02, 0.1))
    if order_id > 9999:
        raise HTTPException(status_code=404, detail="Order not found")
    log.app.info("Cancelled order id=%d", order_id)


# --- Slow / error / chaos ---

@app.get("/api/slow")
async def slow_endpoint():
    delay = random.uniform(0.5, 3.0)
    await asyncio.sleep(delay)
    log.app.info("Slow request delay=%.2fs", delay)
    return {"delay": delay}


@app.get("/api/very-slow")
async def very_slow_endpoint():
    delay = random.uniform(3.0, 8.0)
    await asyncio.sleep(delay)
    log.app.info("Very slow request delay=%.2fs", delay)
    return {"delay": delay}


@app.get("/api/cpu")
async def cpu_bound():
    """Fibonacci to generate CPU load — useful for profiling.
    Intentionally async so it runs on the event loop thread, which allows
    PyroscopeSpanProcessor to correctly tag CPU profiles with the span ID."""
    def fib(n: int) -> int:
        a, b = 0, 1
        for _ in range(n):
            a, b = b, a + b
        return a

    n = random.randint(300_000, 500_000)
    result = fib(n)
    return {"n": n, "last_digits": result % 10**6}


@app.get("/api/bad-request")
async def bad_request():
    raise HTTPException(status_code=400, detail="Invalid parameters")


@app.get("/api/server-error")
async def server_error():
    raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/exception")
async def raise_exception():
    log.app.error("Unhandled exception occurred")
    raise RuntimeError("Something went terribly wrong")


@app.get("/api/random")
async def random_response():
    await asyncio.sleep(random.uniform(0.01, 0.5))
    choice = random.choices(
        ["ok", "bad_request", "server_error", "slow"],
        weights=[60, 15, 15, 10],
    )[0]
    if choice == "bad_request":
        raise HTTPException(status_code=400, detail="Random bad request")
    if choice == "server_error":
        raise HTTPException(status_code=500, detail="Random server error")
    if choice == "slow":
        await asyncio.sleep(random.uniform(1.0, 4.0))
    return {"result": "ok", "choice": choice}

@app.get("/api/system-log")
def system_log():
    log.system.info("System log") # no log correlation opentelemetry
