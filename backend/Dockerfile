FROM ghcr.io/astral-sh/uv:python3.12-bookworm

ENV UV_PROJECT_ENVIRONMENT=/opt/uv
ENV PATH="/opt/uv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
COPY . .

RUN useradd --create-home appuser \
    && chown -R appuser:appuser /app /opt/uv
USER appuser

CMD ["./scripts/start.sh"]
