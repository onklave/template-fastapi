"""FastAPI application entrypoint."""

import os

from fastapi import FastAPI

APP_NAME = os.environ.get("APP_NAME", "onklave-fastapi-service")

app = FastAPI(title=APP_NAME)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness/readiness probe — the Onklave deploy health route."""
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    """Small greeting at the service root."""
    return {"service": APP_NAME, "message": "Hello from Onklave"}
