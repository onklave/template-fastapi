# syntax=docker/dockerfile:1

# --- build stage: install the package into a venv ---
FROM python:3.12-slim AS build
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# --- final stage: slim runtime, non-root ---
FROM python:3.12-slim
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PORT=8000

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# Honour $PORT (defaults to 8000) so the deploy contract's port can be injected.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
