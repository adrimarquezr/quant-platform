# Quant Platform — Quantitative Research & Systematic Trading

A professional-grade quantitative trading research platform built with Python, designed for systematic investing, reproducible backtesting, and rigorous portfolio & risk management.

## Architecture

```
┌─────────────────────────────┐     ┌──────────────────────┐
│   Apache Superset (BI)      │     │   Grafana (Ops)      │
│   Equity Curves, Drawdown,  │     │   CPU, RAM, Latency, │
│   Sharpe, Factor Analysis   │     │   DAG Status, Errors │
└────────────┬────────────────┘     └──────────┬───────────┘
             │                                  │
             ▼                                  ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI REST API                       │
│   /health  /market-data  /backtests  /portfolios  /risk │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│               Quantitative Engine (Python)               │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐│
│  │ Features │→ │ Strategy │→ │Portfolio │→ │  Risk   ││
│  │  Engine  │  │  Engine  │  │  Engine  │  │ Engine  ││
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘│
│                                                ↓        │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │
│  │Backtester│  │ Metrics  │  │ Execution Simulator  │ │
│  └──────────┘  └──────────┘  └──────────────────────┘ │
└────────────┬────────────────────────────────────────────┘
             │
      ┌──────┴──────┐
      ▼              ▼
┌──────────┐  ┌──────────────┐
│PostgreSQL│  │ Parquet/     │
│(metadata)│  │ DuckDB       │
│          │  │ (time series)│
└──────────┘  └──────────────┘
```

## Quick Start

### Local Development (without Docker)

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest -m unit

# Start the API
uvicorn apps.api.main:app --reload --port 8000

# Open API docs
# http://localhost:8000/docs
```

### Docker Compose

```bash
# Copy environment template
cp .env.example .env

# Start all services
docker compose up -d

# Access:
#   API:      http://localhost:8000/docs
#   Superset: http://localhost:8088
```

## Project Structure

```
quant-platform/
├── apps/api/           # FastAPI REST API (presentation layer)
├── src/
│   ├── domain/         # Pure business models & interfaces
│   ├── application/    # Use cases (backtesting, data quality)
│   ├── infrastructure/ # Database, providers, storage adapters
│   ├── features/       # Feature engineering (Polars)
│   ├── strategies/     # Strategy implementations
│   └── execution/      # Execution simulation
├── tests/              # pytest test suite
├── configs/            # YAML configurations
├── infra/              # Docker, Postgres, Superset, Grafana
├── data/               # Parquet data lake (gitignored)
└── dags/               # Airflow DAGs (Phase 2)
```

## Strategies

| Strategy | Description | Status |
|----------|-------------|--------|
| Momentum | Time-series & cross-sectional momentum | ✅ MVP |
| Mean Reversion | Z-score based mean reversion | ✅ MVP |
| Pairs Trading | Cointegration-based spread trading | 🔮 Phase 3 |
| Factor Investing | Multi-factor weighted scoring | 🔮 Phase 3 |

## Key Design Principles

- **No look-ahead bias**: Signals at bar t execute at bar t+1 open
- **Deterministic backtests**: Same inputs → identical outputs
- **Fail-fast data quality**: Corrupt data aborts the pipeline
- **Separation of concerns**: Signal ≠ Portfolio ≠ Execution
- **Reproducibility**: Every backtest stores its full configuration

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12+ |
| API | FastAPI + Pydantic v2 |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 |
| Data Processing | Polars + DuckDB + PyArrow |
| Visualization | Apache Superset |
| Orchestration | Apache Airflow (Phase 2) |
| Monitoring | Prometheus + Grafana (Phase 4) |
| Testing | pytest + pytest-cov |
| Linting | Ruff (replaces Black + isort + flake8) |
| Containers | Docker Compose |

## License

MIT
