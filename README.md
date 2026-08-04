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

Onklave reads the root **`onklave.yaml`** — that manifest is the deploy
contract. It declares the build (root **`Dockerfile`**, multi-stage, runs as a
non-root user) and the runtime:

- Serves on port **8000** (honours `$PORT` if injected).
- Health route: **`GET /healthz`** → `200`.

Onklave builds, tests and deploys the repo itself; GitHub Actions is not part
of that chain. To add a second service, add another entry under `services`.

Keep that contract — Dockerfile at root, listen on the port, `/healthz` → 200 —
and you can extend the app however you like.
