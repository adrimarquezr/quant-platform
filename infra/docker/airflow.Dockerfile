FROM apache/airflow:2.10.2-python3.12

USER root
# Install build tools if needed
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

USER airflow

# Install quant-platform project dependencies into Airflow environment
COPY pyproject.toml README.md /opt/airflow/
RUN pip install --no-cache-dir \
    "polars>=1.14.0" \
    "pyarrow>=18.0.0" \
    "duckdb>=1.1.0" \
    "numpy>=2.1.0" \
    "scipy>=1.14.0" \
    "yfinance>=0.2.48" \
    "structlog>=24.4.0" \
    "pydantic>=2.9.0" \
    "pydantic-settings>=2.6.0" \
    "httpx>=0.28.0" \
    "prometheus-client>=0.21.0"
