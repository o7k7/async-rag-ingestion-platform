FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PYTHONPATH="/app"

WORKDIR /app

RUN useradd -m -u 1000 workeruser

COPY uv.lock pyproject.toml ./

RUN uv sync --frozen --no-install-project --no-dev

ENV PATH="/app/.venv/bin:$PATH"

COPY ./src ./src

RUN chown -R workeruser:workeruser /app

USER workeruser

CMD ["uv", "run", "src/main.py"]