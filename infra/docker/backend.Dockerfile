FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Copy configuration and source files required by hatchling build backend
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY apps/ ./apps/
COPY configs/ ./configs/

# Install Python dependencies and package in editable mode
RUN pip install --no-cache-dir -e ".[dev]"

# Create data directories
RUN mkdir -p /app/data/raw /app/data/processed /app/data/features

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
