# template-fastapi

A Python **FastAPI** web service — an [Onklave](https://onklave.com) project
template. Generate a project from it and you get a tidy, runnable skeleton: a
single FastAPI app that listens on a port and answers a health route, ready to
deploy on Onklave.

## Run locally

Requires Python 3.12+.

```bash
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

The service starts on <http://127.0.0.1:8000>. Try:

- `GET /` — a small JSON greeting.
- `GET /healthz` — `{"status":"ok"}` (the health route).

Set `APP_NAME` in the environment to change the service name.

## Test

```bash
pytest
```

Success looks like all tests passing — they exercise the `/healthz` and root
routes via FastAPI's `TestClient`.

## How Onklave deploys it

Onklave builds this repo from the root **`Dockerfile`** (multi-stage, runs as a
non-root user) and runs it as a **service**:

- Serves on port **8000** (honours `$PORT` if injected).
- Health route: **`GET /healthz`** → `200`.

Keep that contract — Dockerfile at root, listen on the port, `/healthz` → 200 —
and you can extend the app however you like.
