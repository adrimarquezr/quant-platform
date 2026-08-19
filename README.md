# Quant Platform — Quantitative Research & Systematic Trading

A professional-grade quantitative trading research and systematic investment platform built with Python 3.12+, designed for reproducible research, vectorized feature computation, multi-strategy backtesting, automated portfolio optimization, and institutional risk management.

---

## 🏛️ Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                   APACHE SUPERSET / BI DASHBOARDS                       │
│    Equity Curves  •  Risk Metrics & VaR  •  Asset Weights  •  Violations │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │ (SQL Analytics)
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          FASTAPI REST API                                │
│   /portfolios   /risk   /data-quality   /strategies   /backtests         │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │ (Service Layer Calls)
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                   APACHE AIRFLOW ORCHESTRATION                           │
│   • market_data_pipeline: Ingest -> Data Quality -> Feature Store        │
│   • daily_quant_pipeline: End-to-End Daily Pipeline & Rebalance          │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
    ┌────────────────────────────────┼────────────────────────────────┐
    ▼                                ▼                                ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│  DATA QUALITY LAYER  │  │   FEATURE ENGINE     │  │  STRATEGY SIGNALS    │
│  10 Automated Checks │  │ Vectorized Returns,  │  │ Momentum, Mean Rev., │
│  Prices, Gaps, OHLC  │  │ Vol, Z-Score, Trends │  │ Parameter Validation │
└──────────┬───────────┘  └──────────┬───────────┘  └──────────┬───────────┘
           │                         │                         │
           └─────────────────────────┼─────────────────────────┘
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                   PORTFOLIO & RISK ENGINES                               │
│  • Equal Weight, Inverse Volatility & Volatility Targeting Sizing        │
│  • Constraints: Max Position Weight, Gross Exposure, Turnover Limits    │
│  • Historical VaR (95%), CVaR (ES), Continuous Drawdowns, HHI, Beta     │
│  • Hard/Soft Governance Limits & Verdict (APPROVED / REJECTED)           │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                      ┌──────────────┴──────────────┐
                      ▼                             ▼
         ┌──────────────────────────┐  ┌──────────────────────────┐
         │     POSTGRESQL 16        │  │     PARQUET DATA LAKE     │
         │  Portfolios, Snapshots,  │  │  Daily OHLCV & Features   │
         │  Risk Metrics, DQ Runs   │  │  Partitioned Storage      │
         └──────────────────────────┘  └──────────────────────────┘
```

---

## 🚀 Key Modules & Capabilities in Phase 2

### 1. Data Quality Engine (`src/application/data_quality.py`)
- Automated validation before any data enters downstream pipelines:
  - **Schema & Types**: Required columns (`timestamp`, `open`, `high`, `low`, `close`, `volume`).
  - **Null & Missing Value Detection**: Fast column scans.
  - **Duplicate Timestamps**: Temporal uniqueness validation.
  - **Strict Price Positivity & Non-Zero**: $open, high, low, close > 0$.
  - **OHLC Logical Consistency**: $low \le open, close \le high$ and $low \le high$.
  - **Temporal Sorting & Irregular Trading Gaps**: Monotonic ordering and calendar discontinuity tracking.
  - **Abnormal Returns**: Outlier return spike detection ($|r| > 50\%$).
  - **Zero / Negative Volume**: Flagging non-liquid or corrupted trading sessions.
- Generates structured `DataQualityReport` and persists audit trails in `data_quality_runs` & `data_quality_checks`.

### 2. Feature Engineering Engine (`src/features/engine.py`)
- High-performance, vectorized computation powered by Polars:
  - **Returns**: 1-day, 5-day, 20-day, 60-day simple and log returns.
  - **Volatility**: 20-day, 60-day annualized rolling volatility ($\sigma \times \sqrt{252}$).
  - **Moving Averages & Ratios**: Simple (`SMA_10`, `SMA_20`, `SMA_50`, `SMA_200`), Exponential (`EMA_12`, `EMA_26`), and Price-to-SMA ratios.
  - **Momentum & Oscillators**: RSI (14), MACD line, MACD Signal line, MACD Histogram, Bollinger Bands (Upper, Lower, Width).
  - **Z-Scores & Distance**: Rolling 20-day z-scores with variance protection for mean reversion.
  - **Drawdowns**: Continuous percentage drawdown from rolling maximums.
- Strict backward-looking rolling windows with **zero look-ahead bias**.

### 3. Quantitative Strategies (`src/strategies/`)
- **Momentum (`MomentumStrategy`)**: Multi-asset time-series & cross-sectional trend following.
- **Mean Reversion (`MeanReversionStrategy`)**: Vectorized z-score deviation with zero-variance protection, overbought/oversold boundaries, and explicit parameter schemas.

### 4. Portfolio Engine (`src/application/portfolio/engine.py`)
- **Allocation Methods**:
  - `EQUAL_WEIGHT`: Equal distribution among active signals ($w_i = \text{sign}(s_i) / N$).
  - `INVERSE_VOLATILITY`: Risk parity weighting inversely proportional to asset volatility ($w_i \propto 1/\sigma_i$).
  - `VOLATILITY_TARGETING`: Scaling exposures dynamically to match a target portfolio annualized volatility.
- **Constraint Enforcement**:
  - `max_position_weight`: Clipping single-asset weights to institutional limits.
  - `max_gross_exposure`: Normalizing gross leverage ($\sum |w_i| \le \text{limit}$).
  - `max_turnover`: Turnover dampening between rebalancing cycles ($|w_t - w_{t-1}| \le \text{limit}$).

### 5. Risk Engine (`src/application/risk/engine.py`)
- **Point-in-Time Risk Metrics**:
  - **Historical VaR (95%)**: Non-parametric empirical percentile loss.
  - **CVaR / Expected Shortfall (95%)**: Conditional mean loss beyond VaR.
  - **Annualized Volatility**: Sample standard deviation scaled by $\sqrt{252}$.
  - **Drawdown Details**: Continuous tracking of peak equity, trough equity, current drawdown, max drawdown, and recovery factor.
  - **Concentration (HHI)**: Herfindahl-Hirschman Index across asset holdings.
  - **Market Beta & Correlation**: Systematic exposure against benchmark returns.
- **Governance Limits & Audits**:
  - Evaluates `RiskLimitConfig` and generates detailed `RiskViolation` items.
  - Produces deterministic `RiskVerdict.APPROVED` or `RiskVerdict.REJECTED`.

### 6. Apache Airflow Orchestration (`dags/`)
- **`market_data_pipeline`**: Ingests universe market data $\rightarrow$ validates Data Quality $\rightarrow$ computes feature lake $\rightarrow$ persists Parquet partitions.
- **`daily_quant_pipeline`**: Full daily lifecycle orchestrating data ingestion, data quality, feature generation, strategy signals, portfolio target weights, risk governance limits, and backtest benchmarks.
- **Design Philosophy**: Thin orchestration layers delegating all quant logic to reusable Python service domains.

### 7. Superset Dashboards & SQL Analytics (`infra/superset/`)
- Pre-built views for institutional reporting:
  - `v_portfolio_overview`: Current NAV, cash balance, invested capital, position count.
  - `v_portfolio_equity_curve`: Chronological NAV time series and daily return stream.
  - `v_portfolio_holdings`: Detailed weights, unrealized PnL, sectors, and asset classes.
  - `v_risk_metrics_summary`: Point-in-time VaR, CVaR, volatility, leverage, and HHI.
  - `v_risk_violations_audit`: Real-time audit log of all risk limit breaches.
  - `v_strategy_comparison`: Side-by-side performance benchmarks (Sharpe, CAGR, Sortino, Max DD).
  - `v_data_quality_audit`: Quality inspection logs and check statuses per symbol.

---

## 🛠️ Quick Start

### 1. Local Python Environment

```bash
# Clone and enter directory
cd quant-platform

# Install dependencies in editable mode with development tools
pip install -e ".[dev]"

# Run full test suite (Unit, Integration, E2E)
pytest

# Check linting and formatting
ruff check src apps tests dags
ruff format --check src apps tests dags
```

### 2. Launching with Docker Compose

```bash
# Set up environment variables
cp .env.example .env

# Build and start all platform services
docker compose up -d

# Verify running services
docker compose ps
```

### 3. Service Access Points

| Service | URL | Default Credentials | Description |
|---------|-----|---------------------|-------------|
| **FastAPI REST Docs** | `http://localhost:8000/docs` | None | Interactive Swagger API documentation |
| **Apache Airflow UI** | `http://localhost:8080` | `airflow` / `airflow` | DAG pipeline monitoring & scheduling |
| **Apache Superset BI** | `http://localhost:8088` | `admin` / `admin` | Portfolio & Risk analytical dashboards |
| **PostgreSQL Database** | `localhost:5432` | `quant_user` / `change_me_in_production` | Relational metadata store |

---

## 📡 REST API Reference

### Portfolios (`/portfolios`)
- `POST /portfolios`: Create a new investment portfolio (`name`, `description`, `initial_cash`).
- `GET /portfolios`: List all registered portfolios.
- `GET /portfolios/{id}`: Retrieve portfolio details and current NAV.
- `GET /portfolios/{id}/positions`: Retrieve asset holdings, entry prices, and market values.
- `GET /portfolios/{id}/performance`: Retrieve historical NAV snapshots and daily returns.

### Risk Management (`/risk`)
- `POST /risk/evaluate`: Evaluate point-in-time VaR, CVaR, Drawdown, HHI, and audit limits.
- `GET /risk`: List historical risk evaluations.
- `GET /risk/portfolio/{id}`: Query risk profile history for a given portfolio.
- `GET /risk/violations`: Audit trail of all limit breaches.

### Data Quality (`/data-quality`)
- `POST /data-quality/validate/{symbol}`: Trigger validation for an asset and persist report.
- `GET /data-quality`: List historical validation runs.
- `GET /data-quality/{run_id}`: Retrieve detailed check breakdown for a specific audit.

### Strategies (`/strategies`)
- `GET /strategies`: Discover registered strategies (`momentum`, `mean_reversion`).
- `GET /strategies/{name}/schema`: Inspect strategy parameter configurations and default values.

### Backtesting (`/backtests`)
- `POST /backtests`: Launch a deterministic backtest simulation.
- `GET /backtests`: List all completed backtests and summary Sharpe/Return metrics.
- `GET /backtests/{id}`: Retrieve equity curve, trade executions, and full performance tear sheet.

---

## 🧪 Testing & Quality Assurance

The platform enforces strict automated testing and static analysis:
- **Unit Tests**: Domain models, isolated math formulas (VaR, CVaR, Sharpe, Drawdown), feature calculations, strategy edge cases.
- **Integration Tests**: Database ORM persistence, Parquet data lake read/writes, REST API routers, Airflow DAG parsing.
- **End-to-End (E2E) Tests**: Complete pipeline simulation from raw market data ingestion through risk auditing, rebalancing, and API querying.
- **Coverage Goal**: `>= 85%` statement coverage required by CI pipeline.

```bash
# Run unit tests only
pytest -m unit

# Run integration tests only
pytest -m integration

# Run full end-to-end pipeline test
pytest -m e2e

# Generate detailed HTML coverage report
pytest --cov=src --cov=apps --cov-report=html
```

---

## 📜 CI/CD Pipeline

Automated GitHub Actions workflow (`.github/workflows/ci.yml`) executes on every push and pull request:
1. **Lint & Formatting**: `ruff check` & `ruff format --check`.
2. **Type Checking**: `mypy src apps`.
3. **Test Suite**: `pytest --cov=src --cov=apps --cov-report=term-missing` (enforcing `>= 85%` coverage).
4. **Container Validation**: Docker image build verification.

---

## ⚖️ License

MIT License — see [LICENSE](LICENSE) for details.
