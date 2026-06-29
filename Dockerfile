FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy only the files needed for dependency installation first (layer cache)
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

# Install runtime dependencies only (no dev group)
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT []
CMD ["healthex", "--help"]
