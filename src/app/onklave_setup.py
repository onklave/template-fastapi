"""Onklave error tracking for the service.

Initialises the Onklave SDK and captures unhandled request exceptions before
FastAPI's default handler returns the 500. Without an
ONKLAVE_ERRORS_INGEST_KEY the SDK is a silent no-op, so this is safe to call
unconditionally in local dev.
"""

from typing import Awaitable, Callable

import onklave
from fastapi import FastAPI, Request, Response


def setup_onklave(app: FastAPI, service_name: str) -> None:
    """Initialise Onklave and register unhandled-exception capture."""
    onklave.init(service_name=service_name)

    @app.middleware("http")
    async def _capture_unhandled(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            onklave.capture_exception(
                exc,
                request={
                    "method": request.method,
                    "path": request.url.path,
                    "statusCode": 500,
                },
            )
            raise  # FastAPI's default handler still returns the 500.
