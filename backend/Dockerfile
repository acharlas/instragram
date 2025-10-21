FROM ghcr.io/astral-sh/uv:python3.12-bookworm

ENV UV_PROJECT_ENVIRONMENT=/opt/uv
ENV PATH="/opt/uv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
