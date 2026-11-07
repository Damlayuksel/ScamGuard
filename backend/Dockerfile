FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

# The virtualenv lives outside /app so the dev bind mount does not hide it.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Set to "false" for production images.
ARG INSTALL_DEV=true

RUN useradd --system --uid 1000 --create-home app \
    && mkdir /opt/venv /app \
    && chown app:app /opt/venv /app

# Runs as the app user so `uv add` / `uv sync` also work inside dev containers.
USER app
WORKDIR /app

COPY --chown=app:app pyproject.toml uv.lock ./
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        uv sync --frozen; \
    else \
        uv sync --frozen --no-dev; \
    fi

COPY --chown=app:app . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
